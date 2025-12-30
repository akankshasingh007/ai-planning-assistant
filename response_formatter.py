
def format_response(persona_cfg, base_message, details=None):
    tone = persona_cfg.get("tone", "friendly")
    if tone == "concise":
        if details and isinstance(details, dict) and details.get("task"):
            t = details["task"]
            return f"Scheduled: {t.get('title')} at {details.get('start') or t.get('start')}"
        return base_message.split("\n")[0]
    if tone == "formal":
        if details and isinstance(details, dict) and details.get("task"):
            t = details["task"]
            return f"Task '{t.get('title')}' has been scheduled from {details.get('start')} to {details.get('end')}."
        return "Hello. " + base_message
    if details and isinstance(details, dict) and details.get("task"):
        t = details["task"]
        return f"✅ I've scheduled '{t.get('title')}' for you from {details.get('start')} to {details.get('end')}. Anything else?"
    return base_message