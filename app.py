# app.py
import os
from dotenv import load_dotenv

# Load environment variables from .env before importing modules that read them
load_dotenv()

import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, Request, Query, BackgroundTasks
from pydantic import BaseModel
from task_memory import TaskMemory
from planner import Planner
from calendar_mock import CalendarMock
from self_reflection import reflect as reflect_fn
from observability import emit_event
import agent
import tools
import llm_nlu

# ---------------- Setup ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_planner")

app = FastAPI(title="AI Personal Productivity Assistant")

memory = TaskMemory()
calendar_client = CalendarMock()
planner = Planner(calendar_client, memory)

app.state.awaiting_time_for = None
app.state.last_agent_result = None

# ---------------- Schemas ----------------
class ActRequest(BaseModel):
    user_id: str
    goal: str

# ---------------- Background Scheduler ----------------
def _bg_schedule_and_update(user_id: str, parsed: dict, created_task_id: str):
    try:
        result = planner.schedule_task_from_parsed(user_id, parsed)
        if isinstance(result, dict) and result.get("scheduled"):
            start, end = result.get("start"), result.get("end")
            if created_task_id:
                memory.schedule_task(created_task_id, start, end)
                emit_event("task_scheduled", {"user": user_id, "task_id": created_task_id, "start": start, "end": end})
        else:
            emit_event("scheduling_no_slot_found", {"user": user_id, "task_id": created_task_id, "planner_result": result})
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Background scheduling failed: %s", e)
        try:
            emit_event("scheduling_error", {"user": user, "error": str(e), "trace": tb})
        except Exception:
            pass

# ---------------- Main Endpoint ----------------
@app.api_route("/mcp/act", methods=["GET", "POST"])
async def act(request: Request, background_tasks: BackgroundTasks, user_id: str = Query(None), goal: str = Query(None)):
    try:
        # Normalize input
        if request.method == "POST":
            body = await request.json()
            user_id = body.get("user_id") or user_id
            user_input = body.get("goal", "").strip() or (goal or "")
        else:
            user_input = (goal or "").strip()

        if not user_id or not user_input:
            return {"status": "error", "message": "Missing user_id or goal."}

        emit_event("user_input", {"user": user_id, "text": user_input})

        # ---------------- Provide time for pending task ----------------
        if app.state.awaiting_time_for:
            task_id = app.state.awaiting_time_for
            parsed = tools.parse_time(user_input)
            if not parsed:
                return {"status": "ok", "result": {"message": "I didn’t catch the time. Try 'tomorrow 11am'."}}
            start, end = parsed["start"], parsed["end"]
            memory.schedule_task(task_id, start, end)
            app.state.awaiting_time_for = None
            task = memory.get_task(task_id)
            emit_event("task_scheduled", {"user": user_id, "task_id": task_id, "start": start, "end": end})
            return {"status": "ok", "result": {"message": f"✅ Scheduled '{task.title}' from {start} to {end}.", "task": task.to_dict(), "scheduled": True}}

        # Quick intent parsing for scheduling
        parsed_quick = llm_nlu.parse_goal(user_input)
        if parsed_quick.get("intent") == "schedule_task":
            title = parsed_quick.get("title") or parsed_quick.get("raw", "Focused work")
            estimated = parsed_quick.get("duration_minutes") or 60
            task = memory.add_task(title=title, estimated_minutes=int(estimated), priority=int(parsed_quick.get("priority", 3)), pending_time=True)
            emit_event("task_added_pending_time", {"user": user_id, "task": task.to_dict()})
            background_tasks.add_task(_bg_schedule_and_update, user_id, parsed_quick, task.id)
            return {"status": "ok", "result": {"message": f"Trying to schedule '{title}' now. Will update you shortly.", "needs_time": False, "task_id": task.id, "task": task.to_dict()}}

        # Normal agent execution
        tool_mapping = {
            "add_task": lambda uid, title, est, prio: tools.add_task(memory, title, est or 60, prio or 3),
            "complete_task": lambda uid, task_id: tools.complete_task(memory, task_id),
            "list_tasks": lambda uid, status=None: tools.list_tasks(memory, status),
            "self_reflection": lambda uid: tools.self_reflect(reflect_fn, uid, memory, calendar_client),
            "schedule_task": lambda uid, parsed: planner.schedule_task_from_parsed(uid, parsed),
        }

        result = agent.run_agent(user_id, user_input, tool_mapping)
        app.state.last_agent_result = result

        if isinstance(result, dict) and result.get("intent") == "add_task":
            title = result.get("title") or "Untitled task"
            task = memory.add_task(title=title, priority=3, estimated_minutes=result.get("parsed", {}).get("estimated_minutes", 60), pending_time=True)
            app.state.awaiting_time_for = task.id
            emit_event("task_added_pending_time", {"user": user_id, "task": task.to_dict()})
            return {"status": "ok", "result": {"needs_time": True, "title": task.title, "task_id": task.id, "message": f"When should I schedule '{task.title}'?"}}

        if isinstance(result, dict) and (result.get("message") or result.get("tasks") or result.get("task")):
            return {"status": "ok", "result": result}

        message = result.get("message") if isinstance(result, dict) else str(result)
        return {"status": "ok", "result": {"needs_time": False, "message": message, "task": result if isinstance(result, dict) else None}}

    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Unhandled exception in /mcp/act: %s", e)
        try:
            emit_event("error", {"error": str(e), "trace": tb})
        except Exception:
            pass
        return {"status": "error", "message": "Internal server error."}

# ---------------- Tasks Listing ----------------
@app.get("/tasks")
async def get_tasks():
    return {"status": "ok", "result": {"tasks": memory.list_all()}}