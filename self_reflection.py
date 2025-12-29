# self_reflection.py — agent self-reflection module

def reflect(user_id, memory, calendar):
    tasks = memory.list_all()

    done = [t for t in tasks if t["status"] == "done"]
    pending = [t for t in tasks if t["status"] != "done"]

    if not tasks:
        return {
            "message": "You have no tasks yet. Let’s plan something."
        }

    return {
        "message": (
            f"🧠 Self-reflection complete.\n\n"
            f"✅ Completed: {len(done)}\n"
            f"⏳ Pending: {len(pending)}\n\n"
            f"Focus next on your highest-priority pending task."
        )
    }
