
from typing import Dict, Callable
from observability import emit_event
import personas
from connectors.calendar_connector import CalendarConnector
from connectors.github_connector import GitHubConnector
from connectors.messaging_connector import MessagingConnector
import tools
from response_formatter import format_response

def get_tool_mapping(persona_id: str, memory, calendar_client=None):

    persona_cfg = personas.PERSONAS.get(persona_id, personas.PERSONAS["default"])

    cal = CalendarConnector(client=calendar_client) if calendar_client else CalendarConnector()
    gh = GitHubConnector()
    msg = MessagingConnector()

    def add_task(uid, title, est, prio):
        try:
            task = memory.add_task(title=title,
                                   estimated_minutes=int(est or persona_cfg["default_duration_minutes"]),
                                   priority=int(prio or 3))
            emit_event("tool_call:add_task", {"user": uid, "task": task.to_dict(), "persona": persona_cfg["id"]})
            
            if persona_cfg.get("auto_create_issue") and "github" in persona_cfg.get("enabled_tools", []):
                try:
                    issue = gh.create_issue(uid, f"{uid}/auto", task.title, "")
                    gh.link_task_to_issue(memory, task.id, issue)
                    emit_event("auto_issue_created", {"user": uid, "issue": issue, "task_id": task.id})
                except Exception:
                    pass
            return task.to_dict()
        except Exception as e:
            emit_event("tool_call_error:add_task", {"user": uid, "error": str(e), "persona": persona_cfg["id"]})
            raise

    def complete_task(uid, task_id):
        try:
            memory.complete_task(task_id)
            emit_event("tool_call:complete_task", {"user": uid, "task_id": task_id, "persona": persona_cfg["id"]})
            return {"message": "✅ Task completed."}
        except Exception as e:
            emit_event("tool_call_error:complete_task", {"user": uid, "task_id": task_id, "error": str(e)})
            raise

    def list_tasks(uid, status=None):
        try:
            tasks = memory.list_all() if not status else memory.list_by_status(status)
            emit_event("tool_call:list_tasks", {"user": uid, "count": len(tasks)})
            return {"tasks": tasks}
        except Exception as e:
            emit_event("tool_call_error:list_tasks", {"user": uid, "error": str(e)})
            raise

    def self_reflection(uid):
        try:
            from self_reflection import reflect as reflect_fn
            res = reflect_fn(uid, memory, cal.client)
            emit_event("tool_call:self_reflection", {"user": uid})
            return res
        except Exception as e:
            emit_event("tool_call_error:self_reflection", {"user": uid, "error": str(e)})
            raise

    def schedule_task(uid, parsed):
        try:
            from planner import Planner
            planner = Planner(cal.client, memory, default_work_hours=persona_cfg.get("preferred_work_hours"),
                              scheduling_strategy=persona_cfg.get("scheduling_strategy"),
                              deep_work_minutes=persona_cfg.get("deep_work_minutes"))
            res = planner.schedule_task_from_parsed(uid, parsed)
            emit_event("tool_call:schedule_task", {"user": uid, "result": res})
            return res
        except Exception as e:
            emit_event("tool_call_error:schedule_task", {"user": uid, "error": str(e)})
            raise

    def create_issue_and_task(uid, repo, title, body=""):
        try:
            issue = gh.create_issue(uid, repo, title, body)
            task = memory.add_task(title=title,
                                   estimated_minutes=persona_cfg["default_duration_minutes"],
                                   priority=3)
           
            try:
                gh.link_task_to_issue(memory, task.id, issue)
            except Exception:
                pass
            emit_event("tool_call:create_issue_and_task", {"user": uid, "issue": issue, "task_id": task.id})
            return {"issue": issue, "task": task.to_dict()}
        except Exception as e:
            emit_event("tool_call_error:create_issue_and_task", {"user": uid, "error": str(e)})
            raise

    def send_message(uid, channel, text, metadata=None):
        try:
            res = msg.send_message(uid, channel, text, metadata=metadata)
            emit_event("tool_call:send_message", {"user": uid, "channel": channel, "text": text})
            return res
        except Exception as e:
            emit_event("tool_call_error:send_message", {"user": uid, "error": str(e)})
            raise

    def summarize_tasks_tool(uid, scope="all"):
        res = tools.summarize_tasks(memory, uid, scope=scope)
        emit_event("tool_call:summarize_tasks", {"user": uid, "scope": scope})
        msg = format_response(persona_cfg, res.get("message"), details={"counts": res.get("counts")})
        return {"message": msg, "summary": res}

    def estimate_effort_tool(uid, task_ids=None):
        res = tools.estimate_effort(memory, uid, task_ids or [])
        emit_event("tool_call:estimate_effort", {"user": uid, "task_ids": task_ids or []})
        msg = format_response(persona_cfg, f"Estimated effort: {res['total_minutes']} minutes.", details=res)
        return {"message": msg, "estimate": res}

    def prioritize_tasks_tool(uid, horizon_days=7):
        res = tools.prioritize_tasks(memory, uid, horizon_days=horizon_days, persona_cfg=persona_cfg)
        emit_event("tool_call:prioritize_tasks", {"user": uid, "horizon_days": horizon_days})
        msg = format_response(persona_cfg, "Here are the prioritized tasks.", details={"tasks": res.get("tasks", [])})
        return {"message": msg, "prioritization": res}

    def suggest_schedule_tool(uid, duration_minutes=60, preference=None):
        res = tools.suggest_schedule(memory, cal.client, uid, duration_minutes=duration_minutes, preference=preference or persona_cfg.get("scheduling_strategy"))
        emit_event("tool_call:suggest_schedule", {"user": uid, "duration_minutes": duration_minutes, "preference": preference})
        if res.get("error"):
            return {"message": f"Could not find a slot: {res.get('error')}", "error": res.get("error")}
        msg = format_response(persona_cfg, "Suggested time slot:", details={"start": res.get("start"), "end": res.get("end")})
        return {"message": msg, "slot": res}

    allowed = set(persona_cfg.get("enabled_tools", []))

    tool_mapping: Dict[str, Callable] = {}
    tool_mapping["add_task"] = add_task
    tool_mapping["complete_task"] = complete_task
    tool_mapping["list_tasks"] = list_tasks
    tool_mapping["self_reflection"] = self_reflection
    tool_mapping["schedule_task"] = schedule_task

    if "github" in allowed:
        tool_mapping["create_issue_and_task"] = create_issue_and_task
    if "messaging" in allowed:
        tool_mapping["send_message"] = send_message

    tool_mapping["summarize_tasks"] = summarize_tasks_tool
    tool_mapping["estimate_effort"] = estimate_effort_tool
    tool_mapping["prioritize_tasks"] = prioritize_tasks_tool
    tool_mapping["suggest_schedule"] = suggest_schedule_tool
    
    return tool_mapping