
from datetime import datetime, timedelta

class CalendarMock:
    """
    Small in-memory calendar shim that exposes:
      - find_free_slot(user_id, after, duration_minutes) -> datetime
      - add_event(user_id, title, start, end, metadata=None) -> dict

    Planner expects these signatures.
    """

    def add_event(self, user_id, title, start, end, metadata=None):
        # Normalize datetimes -> ISO strings for storage and consistency
        if isinstance(start, datetime):
            start_iso = start.isoformat()
        else:
            start_iso = start
        if isinstance(end, datetime):
            end_iso = end.isoformat()
        else:
            end_iso = end
        return {"title": title, "start": start_iso, "end": end_iso, "metadata": metadata or {}}

    def find_free_slot(self, user_id, after, duration_minutes):
        """
        Very small free-slot finder for demo purposes:
        - Accepts 'after' as datetime or ISO string.
        - Prefer scheduling at 14:00 of that day if possible (simulates "after lunch").
        - Otherwise schedule 1 hour after 'after'.
        """
        if not isinstance(after, datetime):
            try:
                after = datetime.fromisoformat(after)
            except Exception:
                after = datetime.utcnow()

        slot = after.replace(minute=0, second=0, microsecond=0)
        # Prefer "after lunch" slot at 14:00 if possible
        if slot.hour < 14:
            slot = slot.replace(hour=14)
        else:
            slot = slot + timedelta(hours=1)

        return slot