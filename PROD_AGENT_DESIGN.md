
## Goal
- Build an agentic AI assistant that helps users plan their day and manage tasks by integrating reasoning with multiple tools.
- Support multiple personas (Software Developer, Product Manager, Team Lead) via persona configs that tune defaults and tool use.
- Use at least two tools (Calendar + Task store) and optionally third-party connectors (GitHub, Messaging) to make the agent truly agentic: it reasons, chooses tools, and acts.

## High-level architecture (how it maps to this repo)
- NLU: `llm_nlu.py` (uses OpenAI or fallback `nlu.py`).
- Planner / Scheduling: `planner.py` (uses Calendar client; returns scheduled slots).
- Memory: `task_memory.py` (persistent store).
- Tools / Connectors: new connector wrappers provided (calendar, github, messaging).
- Dispatcher: `agent_dispatcher.py` (wires a persona-specific tool mapping into `agent.run_agent`).
- App: `app.py` is the HTTP entrypoint; it should import and use the dispatcher to get tools per persona.

## Core tools and interfaces

All connectors implement small, testable interfaces so Planner / Agent can call them safely.

Calendar client interface (planner expects):
- find_free_slot(user_id, after, duration_minutes) -> datetime
- add_event(user_id, title, start, end, metadata=None) -> dict
- The existing `calendar_mock.CalendarMock` already matches this interface.

TaskMemory interface (existing `TaskMemory` methods):
- add_task(title, priority, estimated_minutes, pending_time=False) -> Task
- list_all() -> list[dict]
- get_task(task_id) -> Task or None
- schedule_task(task_id, start, end) -> None
- complete_task(task_id) -> None

GitHubTool (stub interface):
- create_issue(user_id, repo, title, body) -> dict (issue metadata)
- link_task_to_issue(task_id, issue) -> None (store in TaskMemory metadata)

MessagingTool (stub interface):
- send_message(user_id, channel, text, metadata=None) -> dict

See connector stubs added to the repo for examples.

## Persona layer
A persona is a small config object:
- id: "developer" | "pm" | "team_lead"
- default_duration_minutes: int
- deep_work_minutes: int
- prioritize: function or priority rules
- preferred_work_hours: {start_hour, end_hour}
- enabled_tools: list of connector names

Personas allow the agent to:
- choose default durations
- choose whether to create GitHub issues automatically
- prefer blocking calendar slots (deep work) vs meeting invites

A `personas.py` file is included with example configurations.

## Agentic workflow (detailed)
1. Receive user input -> `llm_nlu.parse_goal()` -> structured intent (intent, title, date, duration_minutes, task_id).
2. Dispatcher chooses tools based on persona and maps capabilities into `agent.run_agent`.
3. If the intent is scheduling:
   - Planner.find_free_slot -> Planner adds event via calendar client -> TaskMemory.schedule_task & emit events.
4. If the intent is to create a work artifact (e.g., GitHub issue):
   - GitHubTool.create_issue -> link to TaskMemory (via metadata).
5. If the intent is to mark done:
   - call TaskMemory.complete_task(task_id) and emit event.
6. The agent returns a user-facing message and structured result.

## Failure and audit
- Every tool call must be wrapped in try/except and emit an observability event (the repo provides `observability.emit_event()`).
- Partial failures are tolerated and surfaced to user with actionable suggestions.
- Logs must never contain raw API keys.

## Integration steps (making this live)
1. Add the connector files (calendar, github, messaging) to the repo (stubs provided).
2. Add `agent_dispatcher.py` which returns `tool_mapping = get_tool_mapping(persona, memory, calendar, connectors...)`.
3. In `app.py` replace the inline `tool_mapping` with `from agent_dispatcher import get_tool_mapping` and call `get_tool_mapping(persona_config, memory, calendar_client, connectors...)`.
   - Persona selection: default to `demo_user` persona or allow `user_id` to map to a stored persona.
4. Ensure `llm_nlu` is present (OpenAI or fallback) and `task_memory.schedule_task` is robust (already fixed).
5. Restart the backend and test flows:
   - add task -> ask to schedule -> respond with time -> scheduled
   - create GitHub issue + schedule focused work block

## Example connectors and dispatcher (see sample files)
- `connectors/calendar_connector.py` (wraps `CalendarMock` or real Google Calendar client).
- `connectors/github_connector.py` (minimal create_issue stub).
- `connectors/messaging_connector.py` (minimal send_message stub).
- `personas.py` (persona configs).
- `agent_dispatcher.py` (wires persona to tools).

## Metrics & evaluation
- Task success rate, tool error rate, latency, user satisfaction (feedback after action).
- Add events for: task_added, task_scheduled, task_completed, external_tool_call, scheduling_error.

## Security
- Store API keys in environment variables (no commit of .env).
- Redact secrets in observability outputs.

## Next steps / optional enhancements
- Add automatic delegation rules for team lead persona (create task and send message).
- Add OAuth flow for Google Calendar / GitHub.
- Add unit tests (for NLU heuristics, planner behavior, connectors).
- Add stronger persona profile management (user-specific stored configs).
