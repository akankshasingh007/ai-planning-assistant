# agent.py — lightweight dispatcher that uses llm_nlu.parse_goal + tool mapping
import llm_nlu
from typing import Callable, Dict, Any

def run_agent(user_id: str, user_input: str, tools: Dict[str, Callable[..., Any]]):
    """
    Run the agent: parse the goal with llm_nlu.parse_goal and dispatch to the matching tool.

    tools expected keys: "add_task", "schedule_task", "complete_task", "list_tasks", "self_reflection" ...
    """
    parsed = llm_nlu.parse_goal(user_input)
    intent = parsed.get("intent")

    # schedule_task -> planner (planner returns dict with scheduled True/False)
    if intent == "schedule_task":
        fn = tools.get("schedule_task")
        if not fn:
            return {"message": "Calendar scheduling not available."}
        # pass parsed dict to the planner tool
        return fn(user_id, parsed)

    # For add_task we prefer to return intent to app so app can prompt for time if needed.
    if intent == "add_task":
        title = parsed.get("title") or parsed.get("raw")
        return {"intent": "add_task", "title": title, "parsed": parsed}

    # self-reflection tool
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
           # Fall back message prompting UI usage
           return {
               "message": "Please click the ✅ button to complete a task."
           }
       # dispatch to the tool if available
       fn = tools.get("complete_task")
       if not fn:
           return {"message": "Complete-task tool not available."}
       try:
           return fn(user_id, task_id)
       except Exception as e:
           return {"message": f"Error completing task: {e}"}

    # fallback: return the parsed raw message
    return {"message": parsed.get("raw", "Okay, done."), "intent": intent, "parsed": parsed}