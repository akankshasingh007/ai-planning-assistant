
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("planner")
logger.setLevel(logging.INFO)

class Planner:
    def __init__(self, calendar_client, memory, default_work_hours: dict = None, scheduling_strategy: str = None, deep_work_minutes: int = None):
        self.calendar = calendar_client
        self.memory = memory
        self.default_work_hours = default_work_hours or {}
        self.scheduling_strategy = scheduling_strategy or "after_lunch"
        self.deep_work_minutes = deep_work_minutes or 60

    def _choose_slot_by_strategy(self, user_id: str, earliest: datetime, duration_minutes: int):
       
        if self.scheduling_strategy == "earliest":
            return earliest
        if self.scheduling_strategy == "after_lunch":
            candidate = earliest.replace(minute=0, second=0, microsecond=0)
            if candidate.hour < 14:
                candidate = candidate.replace(hour=14)
            return candidate
        if self.scheduling_strategy == "block_deep_work":
            candidate = earliest.replace(minute=0, second=0, microsecond=0)
            if candidate.hour < 9:
                candidate = candidate.replace(hour=9)
            return candidate
        return earliest

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
        if earliest < datetime.utcnow():
            earliest = datetime.utcnow()

        task = self.memory.add_task(title, priority=int(parsed.get("priority", 3)), estimated_minutes=duration_minutes)

        try:
            after = self._choose_slot_by_strategy(user_id, earliest, duration_minutes)
            slot_start = self.calendar.find_free_slot(user_id, after, duration_minutes)
        except Exception as e:
            logger.debug("Calendar find_free_slot failed: %s", e)
            slot_start = None

        if not slot_start:
            return {"task": task.to_dict(), "scheduled": False, "reason": "no_free_slot_found"}

        slot_end = slot_start + timedelta(minutes=duration_minutes)

        try:
            ev = self.calendar.add_event(user_id, task.title, slot_start, slot_end, metadata={"task_id": task.id})
        except TypeError:
            ev = self.calendar.add_event(task.title, slot_start, slot_end)

        self.memory.schedule_task(task.id, slot_start.isoformat(), slot_end.isoformat())
        logger.info(f"Scheduled {task.title} for {user_id} at {slot_start.isoformat()}")
        return {"task": task.to_dict(), "scheduled": True, "start": slot_start.isoformat(), "end": slot_end.isoformat()}