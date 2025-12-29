
# tools.py — agent tools
from datetime import datetime, timedelta
from dateutil import parser as dateparser

def add_task(memory, title, est, priority):
    # if est or priority come in as None, set defaults
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
    """
    Small parser: prefer dateutil parser but still handle 'today' and 'tomorrow' phrases.
    Returns dict with ISO start/end strings, or None if not parseable.
    """
    now = datetime.now()
    txt = text.strip().lower()
    start = None

    # direct parse attempt (supports 'tomorrow 11am' etc)
    try:
        parsed = dateparser.parse(text, default=now)
        if parsed:
            start = parsed
    except Exception:
        start = None

    if not start:
        if "tomorrow" in txt:
            start = now + timedelta(days=1)
            start = start.replace(hour=11, minute=0, second=0, microsecond=0)
        elif "today" in txt:
            start = now.replace(hour=11, minute=0, second=0, microsecond=0)
        else:
            return None

    # default duration 1 hour
    end = start + timedelta(hours=1)
    return {"start": start.isoformat(), "end": end.isoformat()}

def self_reflect(reflect_fn, user_id, memory, calendar):
    return reflect_fn(user_id, memory, calendar)