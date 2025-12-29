# task_memory.py — Persistent task store (with observability emits)
import json, os, uuid
from datetime import datetime
from typing import List, Optional, Dict
from observability import emit_event

DATA_FILE = "tasks.json"

class Task:
    def __init__(self, title: str, priority: int = 3, estimated_minutes: int = 60,
                 status: str = "pending", start: Optional[str] = None, end: Optional[str] = None,
                 pending_time: bool = False):
        self.id = str(uuid.uuid4())
        self.title = title
        self.priority = priority
        self.estimated_minutes = estimated_minutes
        self.status = status
        self.start = start
        self.end = end
        self.pending_time = pending_time
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return self.__dict__

class TaskMemory:
    def __init__(self, file_path: str = DATA_FILE):
        self.file_path = file_path
        self.tasks: List[Task] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            self._save()
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            try:
                raw = json.load(f)
                if not isinstance(raw, list):
                    raw = []
            except json.JSONDecodeError:
                raw = []
            self.tasks = [self._from_dict(t) for t in raw if isinstance(t, dict)]

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    def _from_dict(self, data: Dict) -> Task:
        task = Task(
            title=data["title"],
            priority=data.get("priority", 3),
            estimated_minutes=data.get("estimated_minutes", 60),
            status=data.get("status", "pending"),
            start=data.get("start"),
            end=data.get("end"),
            pending_time=data.get("pending_time", False),
        )
        task.id = data["id"]
        task.created_at = data.get("created_at")
        return task

    def add_task(self, title: str, priority: int = 3, estimated_minutes: int = 60,
                 pending_time: bool = False) -> Task:
        task = Task(title=title, priority=priority, estimated_minutes=estimated_minutes, pending_time=pending_time)
        self.tasks.append(task)
        self._save()
        # Observability emit
        try:
            emit_event("task_added", {"task": task.to_dict()})
        except Exception:
            pass
        return task

    def list_all(self) -> List[Dict]:
        return [t.to_dict() for t in self.tasks]

    def list_by_status(self, status: str) -> List[Dict]:
        return [t.to_dict() for t in self.tasks if t.status == status]

    def get_task(self, task_id: str) -> Optional[Task]:
        return next((t for t in self.tasks if t.id == task_id), None)

    def schedule_task(self, task_id, start, end):
        # Accept datetime objects or ISO strings
        if isinstance(start, datetime):
            start = start.isoformat()
        if isinstance(end, datetime):
            end = end.isoformat()

        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("Invalid datetime format")

        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        task.start = start
        task.end = end
        task.status = "scheduled"
        task.pending_time = False
        self._save()
        # Observability emit
        try:
            emit_event("task_scheduled", {"task_id": task_id, "start": start, "end": end, "task": task.to_dict()})
        except Exception:
            pass

    def complete_task(self, task_id: str):
        task = self.get_task(task_id)
        if not task: raise ValueError("Task not found")
        task.status = "done"
        self._save()
        # Observability emit
        try:
            emit_event("task_completed", {"task_id": task_id, "task": task.to_dict()})
        except Exception:
            pass

    def update_task(self, task_id: str, updates: Dict):
        task = self.get_task(task_id)
        if not task: raise ValueError("Task not found")
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self._save()
        # Observability emit
        try:
            emit_event("task_updated", {"task_id": task_id, "updates": updates, "task": task.to_dict()})
        except Exception:
            pass