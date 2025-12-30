
import json
import os
import threading
from datetime import datetime
import logging
import requests

logger = logging.getLogger("observability")

LOG_FILE = os.environ.get("OBS_LOG_FILE", "events.log")
LOCK = threading.Lock()

LANGFUSE_API_KEY = os.environ.get("LANGFUSE_API_KEY")
LANGFUSE_API_URL = os.environ.get("LANGFUSE_API_URL")  # e.g. https://api.langfuse.com

ARIZE_API_KEY = os.environ.get("ARIZE_API_KEY")
ARIZE_API_URL = os.environ.get("ARIZE_API_URL")

def _write_local(event: dict):
    serialized = json.dumps(event, ensure_ascii=False)
    with LOCK:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(serialized + "\n")
        except Exception as e:
            logger.debug("Failed to write local event: %s", e)

def emit_event(name: str, payload: dict):
    event = {
        "time": datetime.utcnow().isoformat(),
        "name": name,
        "payload": payload
    }
   
    _write_local(event)

    if LANGFUSE_API_KEY and LANGFUSE_API_URL:
        try:
            headers = {"x-api-key": LANGFUSE_API_KEY, "Content-Type": "application/json"}
            requests.post(f"{LANGFUSE_API_URL}/events", headers=headers, json=event, timeout=2)
        except Exception as e:
            logger.debug("Langfuse emit failed: %s", e)
            
    if ARIZE_API_KEY and ARIZE_API_URL:
        try:
            headers = {"Authorization": f"Bearer {ARIZE_API_KEY}", "Content-Type": "application/json"}
            requests.post(ARIZE_API_URL.rstrip("/") + "/events", headers=headers, json=event, timeout=2)
        except Exception as e:
            logger.debug("Arize emit failed: %s", e)