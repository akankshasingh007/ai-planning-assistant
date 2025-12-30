
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

    if any(kw in t for kw in ("done", "complete", "mark done", "finished")):
        out["intent"] = "mark_done"
        m = re.search(r"[0-9a-fA-F\-]{8,36}", text)
        if m:
            out["task_id"] = m.group(0)
        return out

    if any(kw in t for kw in ("list tasks", "show tasks", "what are my tasks", "my tasks")):
        out["intent"] = "list_tasks"
        return out

    if any(kw in t for kw in ("reflect", "self-reflection", "how did i do", "review")):
        out["intent"] = "self_reflection"
        return out

    if any(kw in t for kw in ("summarize", "summary", "summarise")):
        out["intent"] = "summarize_tasks"
        return out
    if any(kw in t for kw in ("estimate", "effort", "how long")):
        out["intent"] = "estimate_effort"
        ids = re.findall(r"[0-9a-fA-F\-]{8,36}", text)
        if ids:
            out["task_ids"] = ids
        return out
    if any(kw in t for kw in ("prioritize", "prioritise", "prioritiz")):
        out["intent"] = "prioritize_tasks"
        return out
    if "suggest" in t and "schedule" in t:
        out["intent"] = "suggest_schedule"
        m = re.search(r"(\d+)\s*(h|hr|hour|m|min)", text)
        if m:
            val = int(m.group(1))
            out["duration_minutes"] = val * 60 if m.group(2).startswith("h") else val
        return out

    if any(kw in t for kw in ("schedule", "schedule a", "meeting", "appointment", "tomorrow", "today", "at ", "pm", "am", "on ")):
        out["intent"] = "schedule_task"
        title = re.sub(r"\b(schedule|set|a|for|tomorrow|today|at|on|in|meeting|appointment)\b", "", t, flags=re.I).strip()
        out["title"] = title or None
        try:
            dt = dateparser.parse(text, default=ref)
            if dt:
                out["date"] = dt.isoformat()
        except Exception:
            pass
        m = re.search(r"(\d+)\s*(h|hr|hour|m|min)", text)
        if m:
            val = int(m.group(1))
            if m.group(2).startswith("h"):
                out["duration_minutes"] = val * 60
            else:
                out["duration_minutes"] = val
        else:
            out["duration_minutes"] = 60
        out["estimated_minutes"] = out.get("duration_minutes", 60)
        return out

    if any(kw in t for kw in ("add", "create", "todo", "remind", "schedule")) and not any(kw in t for kw in ("tomorrow","today","at","pm","am","on")):
        out["intent"] = "add_task"
        m = re.sub(r"^(add|create|todo|remind me to)\s*", "", text, flags=re.I).strip()
        out["title"] = m or text
        out["estimated_minutes"] = 60
        out["priority"] = 3
        return out

    out["intent"] = "add_task"
    out["title"] = text
    out["estimated_minutes"] = 60
    out["priority"] = 3
    return out