
"""
planner.py

Planner logic that coordinates TaskMemory and Calendar (real or mock) to schedule tasks.
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger("planner")
logger.setLevel(logging.INFO)

class Planner:
    def __init__(self, calendar_client, memory, default_work_hours: dict = None):
        self.calendar = calendar_client
        self.memory = memory
        self.default_work_hours = default_work_hours or {}

    def schedule_task_from_parsed(self, user_id: str, parsed: dict):
        title = parsed.get("title") or "Focused work"
        duration_minutes = int(parsed.get("duration_minutes", parsed.get("estimated_minutes", 60)))
        date_hint_iso = parsed.get("date")
        if date_hint_iso:
            try:
                earliest = datetime.fromisoformat(date_hint_iso)
            except Exception:
                earliest = datetime.utcnow()
        else:
            earliest = datetime.utcnow()
        # ensure in future
        if earliest < datetime.utcnow():
            earliest = datetime.utcnow()

        # create memory task (store as pending until scheduled)
        task = self.memory.add_task(title, priority=int(parsed.get("priority", 3)), estimated_minutes=duration_minutes)

        # find slot (calendar_client must implement find_free_slot)
        try:
            slot_start = self.calendar.find_free_slot(user_id, earliest, duration_minutes)
        except Exception as e:
            logger.debug("Calendar find_free_slot failed: %s", e)
            slot_start = None

        if not slot_start:
            return {"task": task.to_dict(), "scheduled": False, "reason": "no_free_slot_found"}

        slot_end = slot_start + timedelta(minutes=duration_minutes)

        # Add event (calendar client add_event signature: user_id, title, start, end, metadata)
        try:
            ev = self.calendar.add_event(user_id, task.title, slot_start, slot_end, metadata={"task_id": task.id})
        except TypeError:
            # some clients may accept (title, start, end)
            ev = self.calendar.add_event(task.title, slot_start, slot_end)

        # Save ISO strings into memory (TaskMemory.schedule_task expects strings)
        self.memory.schedule_task(task.id, slot_start.isoformat(), slot_end.isoformat())
        logger.info(f"Scheduled {task.title} for {user_id} at {slot_start.isoformat()}")
        return {"task": task.to_dict(), "scheduled": True, "start": slot_start.isoformat(), "end": slot_end.isoformat()}