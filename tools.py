
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import re

def add_task(memory, title, est=None, priority=None):
    estimated = int(est) if est else 60
    prio = int(priority) if priority else 3
    return memory.add_task(title=title, estimated_minutes=estimated, priority=prio)

def complete_task(memory, task_id):
    memory.complete_task(task_id)
    return {"message": "✅ Task completed."}

def list_tasks(memory, status=None):
    tasks = memory.list_all() if not status else memory.list_by_status(status)
    return {"tasks": tasks}

def parse_time(text):
   
    if not text or not text.strip():
        return None
    now = datetime.now()
    txt = text.strip().lower()
    txt = re.sub(r'\bon\b\s+on\b', ' on', txt)
    txt = re.sub(r'\s+', ' ', txt)
    txt = txt.replace(',', ' ')
    parsed = None
    try:
        parsed = dateparser.parse(txt, default=now, fuzzy=True)
    except Exception:
        parsed = None
    if not parsed:
        try:
            parsed = dateparser.parse(txt, default=now)
        except Exception:
            parsed = None
    if not parsed:
        if "tomorrow" in txt:
            parsed = now + timedelta(days=1)
            parsed = parsed.replace(hour=11, minute=0, second=0, microsecond=0)
        elif "today" in txt:
            parsed = now.replace(hour=11, minute=0, second=0, microsecond=0)
        else:
            return None

    if parsed.hour == 0 and parsed.minute == 0 and ":" not in txt and "am" not in txt and "pm" not in txt:
        parsed = parsed.replace(hour=11, minute=0, second=0, microsecond=0)
    start = parsed
    end = start + timedelta(hours=1)
    return {"start": start.isoformat(), "end": end.isoformat()}

def summarize_tasks(memory, user_id, scope="all"):

    tasks = memory.list_all()
    if scope != "all":
        tasks = [t for t in tasks if t.get("status") == scope]
    total = len(tasks)
    done = len([t for t in tasks if t.get("status") == "done"])
    scheduled = len([t for t in tasks if t.get("status") == "scheduled"])
    pending = len([t for t in tasks if t.get("status") not in ("done", "scheduled")])
    top_pending = sorted([t for t in tasks if t.get("status") != "done"], key=lambda x: x.get("priority", 3))[:5]
    message = f"Summary: {total} tasks — ✅ {done} done • ⏳ {pending} pending • 📅 {scheduled} scheduled."
    return {
        "message": message,
        "top_pending": top_pending,
        "counts": {"total": total, "done": done, "pending": pending, "scheduled": scheduled}
    }

def estimate_effort(memory, user_id, task_ids=None):

    if not task_ids:
        tasks = [t for t in memory.list_all() if t.get("status") != "done"]
    else:
        tasks = []
        for tid in task_ids:
            t = memory.get_task(tid)
            if t:
                tasks.append(t.to_dict())
    total = sum(int(t.get("estimated_minutes", 60)) for t in tasks)
    tasks_counted = len(tasks)
    recommended_blocks = max(1, round(total / 90)) if tasks_counted > 0 else 0
    message = f"Estimated pending effort: {total} minutes across {tasks_counted} tasks. Recommended {recommended_blocks} focused blocks (~90min each)."
    return {
        "total_minutes": total,
        "recommended_blocks": recommended_blocks,
        "tasks_counted": tasks_counted,
        "message": message
    }