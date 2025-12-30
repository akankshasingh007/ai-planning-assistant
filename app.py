
import os
from dotenv import load_dotenv
load_dotenv()

import logging
import traceback
import json
from datetime import datetime
from fastapi import FastAPI, Request, Query, BackgroundTasks, HTTPException
from pydantic import BaseModel
from task_memory import TaskMemory
from planner import Planner
from calendar_mock import CalendarMock
from self_reflection import reflect as reflect_fn
from observability import emit_event
import agent
import tools
import llm_nlu

from agent_dispatcher import get_tool_mapping
import personas
from mcp_functions import get_functions_for_persona

logger = logging.getLogger("ai_planner")
logging.basicConfig(level=logging.INFO)
USE_OPENAI = os.environ.get("USE_OPENAI", "false").lower() in ("1", "true", "yes")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_AVAILABLE = False
OPENAI_CLIENT = None
if USE_OPENAI:
    try:
        from openai import OpenAI as OpenAIClient
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            OPENAI_CLIENT = OpenAIClient(api_key=api_key)
        else:
            OPENAI_CLIENT = OpenAIClient()
        OPENAI_AVAILABLE = True
    except Exception as modern_exc:
        try:
            import openai as legacy_openai
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                legacy_openai.api_key = api_key
            OPENAI_CLIENT = legacy_openai
            OPENAI_AVAILABLE = True
        except Exception:
            OPENAI_AVAILABLE = False
            OPENAI_CLIENT = None
else:
    logger.info("OpenAI disabled (USE_OPENAI not set).")

app = FastAPI(title="AI Personal Productivity Assistant")

memory = TaskMemory()
calendar_client = CalendarMock()
planner = Planner(calendar_client, memory)

app.state.awaiting_time_for = {}
app.state.last_agent_result = None

class ActRequest(BaseModel):
    user_id: str
    goal: str
    persona: str = None
    task_id: str = None

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
            emit_event("scheduling_error", {"user": user_id, "error": str(e), "trace": tb})
        except Exception:
            pass

def run_openai_function_call(user_id: str, user_input: str, persona_id: str, tool_mapping: dict):
    if not OPENAI_AVAILABLE or OPENAI_CLIENT is None:
        return None
    functions = get_functions_for_persona(persona_id)
    messages = [
        {"role": "system", "content": "You are a productivity assistant. Use provided functions when appropriate."},
        {"role": "user", "content": user_input}
    ]
    try:
        if hasattr(OPENAI_CLIENT, "chat") and hasattr(OPENAI_CLIENT.chat, "completions"):
            resp = OPENAI_CLIENT.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=400,
                functions=functions,
                function_call="auto"
            )
            choice = resp.choices[0]
            message = getattr(choice, "message", None) or choice["message"]
        else:
            resp = OPENAI_CLIENT.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=400,
                functions=functions,
                function_call="auto"
            )
            message = resp["choices"][0]["message"]

        if message.get("function_call"):
            fc = message["function_call"]
            name = fc.get("name")
            args_text = fc.get("arguments") or "{}"
            try:
                args = json.loads(args_text)
            except Exception:
                args = {}
            if name not in tool_mapping:
                return {"message": f"I cannot call function '{name}' for persona '{persona_id}'."}
            fn = tool_mapping[name]
            try:
                try:
                    result = fn(user_id, **args)
                except TypeError:
                    try:
                        result = fn(memory, user_id, **args)
                    except TypeError:
                        result = fn(user_id, *(args.values()))
                return {"function": {"name": name, "args": args, "result": result}}
            except Exception as e:
                logger.exception("Function execution failed: %s", e)
                return {"message": f"Function '{name}' failed: {e}"}

        text = message.get("content") or message.get("text") or ""
        return {"message": text}

    except Exception as e:
        err = str(e)
        if "invalid_api_key" in err or "Incorrect API key" in err or "401" in err or "invalid request" in err.lower():
            logger.info("OpenAI invalid/unauthorized — falling back.")
            return None
        logger.exception("OpenAI function-calling failed: %s", e)
        return {"message": f"Model error: {e}"}

@app.get("/mcp/functions")
async def list_mcp_functions(persona: str = Query(None)):
    persona_id = persona or "default"
    if persona_id not in personas.PERSONAS:
        persona_id = "default"
    try:
        funcs = get_functions_for_persona(persona_id)
        return {"status": "ok", "result": {"persona": persona_id, "functions": funcs}}
    except Exception as e:
        logger.exception("Failed to list functions: %s", e)
        return {"status": "error", "message": str(e)}

@app.api_route("/mcp/act", methods=["GET", "POST"])
async def act(request: Request, background_tasks: BackgroundTasks, user_id: str = Query(None), goal: str = Query(None), persona: str = Query(None)):
    try:
        provided_task_id = None
        if request.method == "POST":
            body = await request.json()
            user_id = body.get("user_id") or user_id
            user_input = body.get("goal", "").strip() or (goal or "")
            persona = body.get("persona") or persona
            provided_task_id = body.get("task_id")
        else:
            user_input = (goal or "").strip()

        if not user_id or not user_input:
            return {"status": "error", "message": "Missing user_id or goal."}

        emit_event("user_input", {"user": user_id, "text": user_input, "persona": persona, "provided_task_id": bool(provided_task_id)})

        task_id_to_use = provided_task_id or app.state.awaiting_time_for.get(user_id)
        if task_id_to_use:
            parsed = tools.parse_time(user_input)
            if not parsed:
                return {"status": "ok", "result": {"message": "I didn’t catch the time. Try 'tomorrow 11am'."}}
            start, end = parsed["start"], parsed["end"]
            try:
                memory.schedule_task(task_id_to_use, start, end)
            except Exception as e:
                logger.exception("Scheduling failed for task_id %s: %s", task_id_to_use, e)
                if app.state.awaiting_time_for.get(user_id) == task_id_to_use:
                    app.state.awaiting_time_for.pop(user_id, None)
                return {"status": "ok", "result": {"message": f"Could not schedule task {task_id_to_use}: {e}"}}
            if app.state.awaiting_time_for.get(user_id) == task_id_to_use:
                app.state.awaiting_time_for.pop(user_id, None)
            task = memory.get_task(task_id_to_use)
            emit_event("task_scheduled", {"user": user_id, "task_id": task_id_to_use, "start": start, "end": end})
            return {"status": "ok", "result": {"message": f"✅ Scheduled '{task.title}' from {start} to {end}.", "task": task.to_dict(), "scheduled": True}}

        parsed_quick = llm_nlu.parse_goal(user_input)
        if parsed_quick.get("intent") == "schedule_task":
            title = parsed_quick.get("title") or parsed_quick.get("raw", "Focused work")
            estimated = parsed_quick.get("duration_minutes") or 60
            task = memory.add_task(title=title, estimated_minutes=int(estimated), priority=int(parsed_quick.get("priority", 3)), pending_time=True)

            if getattr(task, "deduped", False):
                return {"status": "ok", "result": {"message": f"I already added '{task.title}' recently. I'll use that one.", "task": task.to_dict(), "needs_time": True, "task_id": task.id}}
            app.state.awaiting_time_for[user_id] = task.id
            emit_event("task_added_pending_time", {"user": user_id, "task": task.to_dict()})
            background_tasks.add_task(_bg_schedule_and_update, user_id, parsed_quick, task.id)
            return {"status": "ok", "result": {"message": f"Trying to schedule '{title}' now. Will update you shortly.", "needs_time": False, "task_id": task.id, "task": task.to_dict()}}

        ui_lower = user_input.lower()
        if "summarize" in ui_lower or "summary" in ui_lower:
            try:
                summary = tools.summarize_tasks(memory, user_id, scope="all")
                if "message" not in summary:
                    summary["message"] = summary.get("message") or f"Summary: {summary.get('counts', {}).get('total', len(memory.list_all()))} tasks."
                return {"status": "ok", "result": summary}
            except Exception as e:
                logger.exception("Summarize failed: %s", e)
                return {"status": "ok", "result": {"message": f"Could not summarize tasks: {e}"}}

        if "estimate" in ui_lower or "effort" in ui_lower:
            try:
                estimate = tools.estimate_effort(memory, user_id, task_ids=[])
                msg = f"Estimated pending effort: {estimate.get('total_minutes',0)} minutes across {estimate.get('tasks_counted',0)} tasks. Recommended blocks: {estimate.get('recommended_blocks',0)}."
                estimate["message"] = msg
                return {"status": "ok", "result": estimate}
            except Exception as e:
                logger.exception("Estimate failed: %s", e)
                return {"status": "ok", "result": {"message": f"Could not estimate effort: {e}"}}

        persona_id = persona or "default"
        if persona_id not in personas.PERSONAS:
            persona_id = "default"

        tool_mapping = get_tool_mapping(persona_id, memory, calendar_client=calendar_client)

        if OPENAI_AVAILABLE:
            func_result = run_openai_function_call(user_id, user_input, persona_id, tool_mapping)
            if func_result is not None:
                return {"status": "ok", "result": func_result}

        result = agent.run_agent(user_id, user_input, tool_mapping)
        app.state.last_agent_result = result

        if isinstance(result, dict) and result.get("intent") == "add_task":
            title = result.get("title") or "Untitled task"
            parsed = result.get("parsed", {}) or {}
            estimated_minutes = parsed.get("estimated_minutes", 60)
            task = memory.add_task(title=title, priority=3, estimated_minutes=estimated_minutes, pending_time=True)
            if getattr(task, "deduped", False):
                return {"status": "ok", "result": {"needs_time": True, "title": task.title, "task_id": task.id, "message": f"I already added '{task.title}' recently. I'll use that one. When should I schedule it?"}}
            app.state.awaiting_time_for[user_id] = task.id
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

@app.get("/tasks")
async def get_tasks():
    return {"status": "ok", "result": {"tasks": memory.list_all()}}

@app.post("/tasks/{task_id}/complete")
async def complete_task_endpoint(task_id: str):
    try:
        memory.complete_task(task_id)
        try:
            emit_event("task_completed_api", {"task_id": task_id})
        except Exception:
            pass
        return {"status": "ok", "result": {"message": "✅ Task marked done", "task_id": task_id}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/mcp/reflect")
async def reflect_endpoint(user_id: str = Query(None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    try:
        tasks = memory.list_all()
        completed = [t for t in tasks if t.get("status") == "done"]
        pending = [t for t in tasks if t.get("status") != "done"]
        pending_ids = [t["id"] for t in pending]
        try:
            from tools import estimate_effort
            estimate = estimate_effort(memory, user_id, pending_ids)
        except Exception:
            estimate = {"total_minutes": sum(t.get("estimated_minutes", 60) for t in pending), "recommended_blocks": 0, "tasks_counted": len(pending)}
        message = f"Self-reflection: ✅ Completed: {len(completed)} • ⏳ Pending: {len(pending)}. Estimated pending effort: {estimate.get('total_minutes', 0)} min."
        return {
            "status": "ok",
            "result": {
                "message": message,
                "counts": {"completed": len(completed), "pending": len(pending)},
                "completed": completed,
                "pending": pending,
                "estimate": estimate
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))