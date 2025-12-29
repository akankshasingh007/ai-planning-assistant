# llm_nlu.py
# LLM-based NLU that turns natural-language goals into a structured JSON intent object.
# Tries to use OpenAI if available and OPENAI_API_KEY is set; otherwise falls back to a local heuristic.
import os
import json
import logging
from datetime import datetime
from dateutil import parser as dateparser

logger = logging.getLogger("llm_nlu")
logger.setLevel(logging.INFO)

# Try to import openai, but tolerate its absence so local runs work without it.
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

# Keep a minimal fallback heuristic if LLM fails or isn't available
def heuristic_parse_goal(text: str, ref: datetime = None):
    # Import the local heuristic nlu parser if present
    try:
        from nlu import parse_goal as hparse
        return hparse(text, ref)
    except Exception:
        # Minimal safe fallback in case nlu.py isn't present either
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
    """
    Parse the user's free-text goal into a dict.
    Uses OpenAI if available and API key present; otherwise falls back to heuristics.
    """
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
        # attempt to extract JSON from the model response
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