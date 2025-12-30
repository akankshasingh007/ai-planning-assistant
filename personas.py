
from typing import Dict, Any

PERSONAS: Dict[str, Dict[str, Any]] = {
    "developer": {
        "id": "developer",
        "display_name": "Software Developer",
        "default_duration_minutes": 60,
        "deep_work_minutes": 90,
        "preferred_work_hours": {"start": 9, "end": 17},
        "enabled_tools": ["calendar", "github"],
        "auto_create_issue": True,
        "scheduling_strategy": "block_deep_work",  
        "priority_rules": {"overdue_boost": 2, "important_tags": ["bug", "critical"]},
        "tone": "concise"
    },
    "product_manager": {
        "id": "product_manager",
        "display_name": "Product Manager",
        "default_duration_minutes": 45,
        "deep_work_minutes": 60,
        "preferred_work_hours": {"start": 9, "end": 18},
        "enabled_tools": ["calendar", "messaging"],
        "auto_create_issue": False,
        "scheduling_strategy": "earliest",
        "priority_rules": {"overdue_boost": 1, "important_tags": ["roadmap", "customer"]},
        "tone": "friendly"
    },
    "team_lead": {
        "id": "team_lead",
        "display_name": "Team Lead",
        "default_duration_minutes": 30,
        "deep_work_minutes": 60,
        "preferred_work_hours": {"start": 8, "end": 16},
        "enabled_tools": ["calendar", "messaging", "github"],
        "auto_create_issue": False,
        "scheduling_strategy": "after_lunch",
        "priority_rules": {"overdue_boost": 1, "important_tags": ["sync", "blocker"]},
        "tone": "formal"
    },
    "default": {
        "id": "default",
        "display_name": "Default",
        "default_duration_minutes": 60,
        "deep_work_minutes": 60,
        "preferred_work_hours": {"start": 9, "end": 17},
        "enabled_tools": ["calendar"],
        "auto_create_issue": False,
        "scheduling_strategy": "after_lunch",
        "priority_rules": {},
        "tone": "friendly"
    }
}