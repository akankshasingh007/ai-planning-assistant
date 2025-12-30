
import os
import json
import logging
from datetime import datetime
from dateutil import parser as dateparser

logger = logging.getLogger("llm_nlu")
logger.setLevel(logging.INFO)

OPENAI_AVAILABLE = True
try:
    import openai
except Exception:
    OPENAI_AVAILABLE = False
    openai = None
    logger.info("openai package not available; falling back to heuristic NLU.")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    if not OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not set; will use heuristic fallback.")
    OPENAI_AVAILABLE = False

def heuristic_parse_goal(text: str, ref: datetime = None):
    try:
        from nlu import parse_goal as hparse
        return hparse(text, ref)
    except Exception:
        ref = ref or datetime.utcnow()
        return {
            "intent": "add_task",
            "title": text,
            "estimated_minutes": 60,
            "priority": 3,
            "raw": text
        }

SYSTEM_PROMPT = "You are a JSON-outputting parser. Return a compact JSON object with keys intent, title (optional), duration_minutes (optional), date (optional iso), estimated_minutes (optional), priority (optional), raw."

def parse_goal(text: str, ref: datetime = None):
   
    ref = ref or datetime.utcnow()
    if not OPENAI_AVAILABLE:
        return heuristic_parse_goal(text, ref)

    try:
        completion = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.0,
            max_tokens=300
        )
        content = completion["choices"][0]["message"]["content"]
    
        start = content.find("{")
        if start == -1:
            return heuristic_parse_goal(text, ref)
        json_text = content[start:]
        parsed = json.loads(json_text)
        if parsed.get("date"):
            try:
                dt = dateparser.parse(parsed["date"], default=datetime.utcnow())
                parsed["date"] = dt.isoformat()
            except Exception:
                pass
        parsed["raw"] = parsed.get("raw", text)
        return parsed
    except Exception as e:
        logger.exception("LLM parse failed, falling back to heuristic: %s", e)
        return heuristic_parse_goal(text, ref)