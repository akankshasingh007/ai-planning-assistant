# agent.py — lightweight dispatcher that uses llm_nlu.parse_goal + tool mapping
import llm_nlu
from typing import Callable, Dict, Any

def run_agent(user_id: str, user_input: str, tools: Dict[str, Callable[..., Any]]):
    """
    Run the agent: parse the goal with llm_nlu.parse_goal and dispatch to the matching tool.
    tools expected keys: "add_task", "schedule_task", "complete_task", "list_tasks",
    "self_reflection", "summarize_tasks", "estimate_effort", "prioritize_tasks", "suggest_schedule" ...
    """
    parsed = llm_nlu.parse_goal(user_input)
    intent = parsed.get("intent")

    # schedule_task -> planner (planner returns dict with scheduled True/False)
    if intent == "schedule_task":
        fn = tools.get("schedule_task")
        if not fn:
            return {"message": "Calendar scheduling not available."}
        return fn(user_id, parsed)

    # add_task -> create pending task (UI will ask for time)
    if intent == "add_task":
        title = parsed.get("title") or parsed.get("raw")
        return {"intent": "add_task", "title": title, "parsed": parsed}

    # self-reflection
    if intent in ("self_reflection", "self-reflection", "self_reflect", "reflect"):
        fn = tools.get("self_reflection") or tools.get("self_reflect")
        if not fn:
            return {"message": "Reflection tool not available."}
        return fn(user_id)

    # list tasks
    if intent == "list_tasks":
        fn = tools.get("list_tasks")
        if not fn:
            return {"message": "List tool not available."}
        return fn(user_id, None)

    # complete / mark done
    if intent in ("mark_done", "mark_done_task", "complete_task", "done"):
        task_id = parsed.get("task_id")
        if not task_id:
            return {"message": "Please click the ✅ button to complete a task."}
        fn = tools.get("complete_task")
        if not fn:
            return {"message": "Complete-task tool not available."}
        try:
            return fn(user_id, task_id)
        except Exception as e:
            return {"message": f"Error completing task: {e}"}

    # new higher-level intents
    if intent == "summarize_tasks":
        fn = tools.get("summarize_tasks")
        if not fn:
            return {"message": "Summarize tool not available."}
        scope = parsed.get("scope", "all")
        return fn(user_id, scope)

    if intent == "estimate_effort":
        fn = tools.get("estimate_effort")
        if not fn:
            return {"message": "Estimate tool not available."}
        task_ids = parsed.get("task_ids", [])
        return fn(user_id, task_ids)

    if intent == "prioritize_tasks":
        fn = tools.get("prioritize_tasks")
        if not fn:
            return {"message": "Prioritization tool not available."}
        horizon = parsed.get("horizon_days", 7)
        return fn(user_id, horizon)

    if intent == "suggest_schedule":
        fn = tools.get("suggest_schedule")
        if not fn:
            return {"message": "Suggest-schedule tool not available."}
        duration = parsed.get("duration_minutes", 60)
        pref = parsed.get("preference")
        return fn(user_id, duration, pref)

    return {"message": parsed.get("raw", "Okay, done."), "intent": intent, "parsed": parsed}