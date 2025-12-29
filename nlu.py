# Minimal heuristic NLU used as a fallback when OPENAI_API_KEY is not set.
# Provides parse_goal(text, ref=None) -> dict with keys:
#   intent, title (optional), duration_minutes (optional), date (optional iso),
#   estimated_minutes (optional), priority (optional), raw
from datetime import datetime, timedelta
import re
from dateutil import parser as dateparser

def _as_iso(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            return dateparser.parse(dt).isoformat()
        except Exception:
            return dt
    return dt.isoformat()

def parse_goal(text: str, ref: datetime = None):
    ref = ref or datetime.utcnow()
    t = (text or "").strip().lower()
    out = {"intent": "unknown", "raw": text}

    # mark done / complete
    if any(kw in t for kw in ("done", "complete", "mark done", "finished")):
        out["intent"] = "mark_done"
        # try to extract a UUID-like id if provided (fallback otherwise)
        m = re.search(r"[0-9a-fA-F\-]{8,36}", text)
        if m:
            out["task_id"] = m.group(0)
        return out

    # list tasks
    if any(kw in t for kw in ("list tasks", "show tasks", "what are my tasks", "my tasks")):
        out["intent"] = "list_tasks"
        return out

    # self-reflection
    if any(kw in t for kw in ("reflect", "self-reflection", "how did i do", "review")):
        out["intent"] = "self_reflection"
        return out

    # schedule / add with time hint (schedule intent)
    if any(kw in t for kw in ("schedule", "schedule a", "meeting", "appointment", "tomorrow", "today", "at ", "pm", "am")):
        out["intent"] = "schedule_task"
        # title guess: remove scheduling words
        title = re.sub(r"\b(schedule|set|a|for|tomorrow|today|at|on|in|meeting|appointment)\b", "", t, flags=re.I).strip()
        out["title"] = title or None

        # try to parse a date/time phrase
        try:
            dt = dateparser.parse(text, default=ref)
            if dt:
                out["date"] = dt.isoformat()
        except Exception:
            pass

        # duration heuristics
        m = re.search(r"(\d+)\s*(h|hr|hour|m|min)", text)
        if m:
            val = int(m.group(1))
            if m.group(2).startswith("h"):
                out["duration_minutes"] = val * 60
            else:
                out["duration_minutes"] = val
        else:
            out["duration_minutes"] = 60  # default 1 hour

        out["estimated_minutes"] = out.get("duration_minutes", 60)
        return out

    # add task (no time yet) -> add_task intent
    if any(kw in t for kw in ("add", "create", "todo", "remind")):
        out["intent"] = "add_task"
        # guess title
        # e.g. "add museum visit" -> "museum visit"
        m = re.sub(r"^(add|create|todo|remind me to)\s*", "", text, flags=re.I).strip()
        out["title"] = m or text
        out["estimated_minutes"] = 60
        out["priority"] = 3
        return out

    # fallback: treat as add_task with raw title
    out["intent"] = "add_task"
    out["title"] = text
    out["estimated_minutes"] = 60
    out["priority"] = 3
    return out