
from typing import List, Dict
import personas

CORE_FUNCTIONS: List[Dict] = [
    {
        "name": "add_task",
        "description": "Create a task in the user's task memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "title": {"type": "string"},
                "estimated_minutes": {"type": "integer"},
                "priority": {"type": "integer"},
                "pending_time": {"type": "boolean"}
            },
            "required": ["user_id", "title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List tasks for the user (optionally filtered by status).",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "status": {"type": ["string","null"]},
                "limit": {"type": "integer"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "get_task",
        "description": "Get a single task by id.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_id": {"type": "string"}
            },
            "required": ["user_id", "task_id"]
        }
    },
    {
        "name": "update_task",
        "description": "Update fields on an existing task.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_id": {"type": "string"},
                "updates": {"type": "object"}
            },
            "required": ["user_id", "task_id", "updates"]
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_id": {"type": "string"}
            },
            "required": ["user_id", "task_id"]
        }
    },
    {
        "name": "self_reflection",
        "description": "Run the agent's self-reflection routine for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "summarize_tasks",
        "description": "Return a short summary of the user's tasks (counts by status and top pending items).",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "scope": {"type": "string", "enum": ["all", "pending", "scheduled", "done"]}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "estimate_effort",
        "description": "Estimate total effort for a set of tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "prioritize_tasks",
        "description": "Return prioritized list of task ids or suggestions for the next N days.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "horizon_days": {"type": "integer"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "suggest_schedule",
        "description": "Suggest a calendar slot for a given duration based on preference.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "preference": {"type": "string"}
            },
            "required": ["user_id", "duration_minutes"]
        }
    }
]

CALENDAR_FUNCTIONS: List[Dict] = [
    {
        "name": "schedule_task",
        "description": "Schedule a task in the user's calendar. If task_id is provided, link the scheduled slot to that task.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_id": {"type": ["string","null"]},
                "title": {"type": ["string","null"]},
                "duration_minutes": {"type": "integer"},
                "earliest_iso": {"type": ["string","null"]},
                "preferred_hours": {
                    "type": "object",
                    "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}}
                }
            },
            "required": ["user_id", "duration_minutes"]
        }
    },
    {
        "name": "find_free_slot",
        "description": "Find a free calendar slot after a given time for the given duration.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "after_iso": {"type": "string"},
                "duration_minutes": {"type": "integer"}
            },
            "required": ["user_id", "after_iso", "duration_minutes"]
        }
    },
    {
        "name": "add_event",
        "description": "Add a calendar event at the given start/end.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "title": {"type": "string"},
                "start_iso": {"type": "string"},
                "end_iso": {"type": "string"},
                "metadata": {"type": "object"}
            },
            "required": ["user_id", "title", "start_iso", "end_iso"]
        }
    }
]

GITHUB_FUNCTIONS: List[Dict] = [
    {
        "name": "create_issue",
        "description": "Create an issue in the given repo and return issue metadata.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "repo": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["user_id", "repo", "title"]
        }
    },
    {
        "name": "link_task_to_issue",
        "description": "Link an existing task to an external issue object.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "task_id": {"type": "string"},
                "issue": {"type": "object"}
            },
            "required": ["user_id", "task_id", "issue"]
        }
    }
]

MESSAGING_FUNCTIONS: List[Dict] = [
    {
        "name": "send_message",
        "description": "Send a short message to a channel on behalf of the user (stub).",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "channel": {"type": "string"},
                "text": {"type": "string"},
                "metadata": {"type": "object"}
            },
            "required": ["user_id", "channel", "text"]
        }
    }
]

ALL_FUNCTIONS = CORE_FUNCTIONS + CALENDAR_FUNCTIONS + GITHUB_FUNCTIONS + MESSAGING_FUNCTIONS

def get_functions_for_persona(persona_id: str) -> List[Dict]:
   
    persona_cfg = personas.PERSONAS.get(persona_id, personas.PERSONAS.get("default", {}))
    enabled = set(persona_cfg.get("enabled_tools", []))

    funcs = []
    funcs.extend(CORE_FUNCTIONS)
    if "calendar" in enabled:
        funcs.extend(CALENDAR_FUNCTIONS)
    if "github" in enabled:
        funcs.extend(GITHUB_FUNCTIONS)
    if "messaging" in enabled:
        funcs.extend(MESSAGING_FUNCTIONS)
    seen = set()
    out = []
    for f in funcs:
        if f["name"] in seen:
            continue
        seen.add(f["name"])
        out.append(f)
    return out