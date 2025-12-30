
from datetime import datetime, timedelta

class CalendarMock:

    def add_event(self, user_id, title, start, end, metadata=None):
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
      
        if not isinstance(after, datetime):
            try:
                after = datetime.fromisoformat(after)
            except Exception:
                after = datetime.utcnow()

        slot = after.replace(minute=0, second=0, microsecond=0)
        if slot.hour < 14:
            slot = slot.replace(hour=14)
        else:
            slot = slot + timedelta(hours=1)

        return slot