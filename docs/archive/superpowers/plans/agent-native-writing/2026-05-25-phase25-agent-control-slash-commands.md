# Phase25 Agent Control Slash Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor slash commands from manual module shortcuts into an Agent control surface.

**Architecture:** The public slash menu exposes only session controls and Agent-level controls. Legacy module commands are accepted only as migration aliases that translate into natural-language Agent intents; they must not create old module-specific pending actions directly.

**Tech Stack:** FastAPI backend, SQLAlchemy tests with pytest, Vue/TypeScript command parser with Vitest.

---

## Assumptions And Success Criteria

- `/clear` and `/compact` remain because they control the chat session itself.
- Public Agent controls for this phase are `/continue` and `/status`; they route through existing dialog Agent logic rather than direct module actions.
- Legacy `/setup`, `/storyline`, `/outline`, and `/chapter` remain parseable for input tolerance, but they are hidden from the public menu and converted to Agent intent text.
- The backend route projection should no longer advertise legacy module commands as slash-command routes.
- Verification uses targeted T1/T2 checks, not full-suite validation.

## Files

- Modify: `backend/app/core/chat_commands.py`
  - Add command metadata for public visibility, legacy aliases, and Agent intent text.
  - Stop exposing legacy module commands through slash route projection.
- Modify: `backend/app/api/dialogs.py`
  - Route `/continue` and `/status` through existing text-intent/low-detail continue paths.
  - Convert legacy module commands into Agent intent text instead of direct pending actions.
  - Preserve request message metadata for traceability.
- Modify: `backend/app/services/writing_agent/slash_command_route.py`
  - Ensure route inspection reflects public Agent slash commands and reports hidden legacy aliases separately.
- Modify: `backend/tests/test_dialogs.py`
  - Add RED tests for Agent-first slash command behavior and legacy alias migration.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Adjust slash route inspection expectations away from legacy module command routes.
- Modify: `frontend/src/components/workspace/chatCommands.ts`
  - Public menu shows `/continue`, `/status`, `/clear`, `/compact`.
  - Parser accepts legacy aliases only for migration.
- Modify: `frontend/src/components/workspace/chatCommands.test.ts`
  - Add RED tests for hidden legacy commands and new Agent controls.

## Task 1: Backend Command Contract Tests

- [ ] **Step 1: Write failing backend tests**

Update `backend/tests/test_dialogs.py`:

```python
def test_chat_command_registry_exposes_agent_controls_and_hides_legacy_aliases():
    public_commands = public_chat_command_names()

    assert public_commands == ["continue", "status", "clear", "compact"]
    assert is_supported_chat_command("continue") is True
    assert is_supported_chat_command("status") is True
    assert is_supported_chat_command("setup") is True
    assert is_legacy_chat_command("setup") is True
    assert command_to_action_type("setup") is None
    assert command_to_action_type("chapter") is None
    assert command_agent_route("setup") is None
    assert command_agent_route("chapter") is None
```

Add a focused API behavior test:

```python
def test_continue_command_routes_through_low_detail_agent_continue(client, db_session):
    project_id = _create_project_with_ready_outline(client, db_session, chapter_count=2)
    _create_generated_chapter(db_session, project_id, chapter_index=1)

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project_id, "input_type": "command", "command_name": "continue"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pending_action"]["type"] == "preview_chapter"
    assert data["pending_action"]["params"]["chapter_index"] == 2
```

Add a legacy migration test:

```python
def test_legacy_chapter_command_routes_as_agent_intent_not_direct_slash_action(client, db_session):
    project_id = _create_project_with_ready_outline(client, db_session, chapter_count=2)

    response = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "chapter",
            "command_args": "2 强化悬疑",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pending_action"]["type"] == "preview_chapter"
    params = data["pending_action"]["params"]
    assert params["agent_route"]["source"] == "text_intent"
    assert params["legacy_command"]["command_name"] == "chapter"
```

- [ ] **Step 2: Run RED backend tests**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "chat_command_registry_exposes_agent_controls or continue_command_routes_through_low_detail_agent_continue or legacy_chapter_command_routes_as_agent_intent" -q
```

Expected: fail because public command helpers and Agent intent routing do not exist yet.

## Task 2: Frontend Command Contract Tests

- [ ] **Step 1: Write failing frontend tests**

Update `frontend/src/components/workspace/chatCommands.test.ts`:

```typescript
it('公开候选只展示 Agent 控制命令和会话命令', () => {
  expect(filterChatCommands('/').map((command) => command.name)).toEqual([
    'continue',
    'status',
    'clear',
    'compact',
  ])
})

it('旧模块命令可解析但不出现在候选中', () => {
  expect(filterChatCommands('/ch')).toEqual([])
  expect(parseSlashCommand('/chapter 2 强化悬疑')).toEqual({
    kind: 'command',
    name: 'chapter',
    args: '2 强化悬疑',
    rawInput: '/chapter 2 强化悬疑',
  })
})

it('/continue 和 /status 会被解析为 Agent 控制命令', () => {
  expect(parseSlashCommand('/continue')).toMatchObject({ kind: 'command', name: 'continue' })
  expect(parseSlashCommand('/status')).toMatchObject({ kind: 'command', name: 'status' })
})
```

- [ ] **Step 2: Run RED frontend tests**

Run:

```powershell
.\node_modules\.bin\vitest.cmd run frontend/src/components/workspace/chatCommands.test.ts
```

Expected: fail because new commands and hidden legacy behavior are not implemented.

## Task 3: Backend Implementation

- [ ] **Step 1: Extend command metadata**

In `backend/app/core/chat_commands.py`, add fields to `ChatCommandSpec`:

```python
public: bool = True
legacy: bool = False
agent_intent_text: str | None = None
```

Set registry semantics:

- `continue`: public, `agent_intent_text="继续"`
- `status`: public, `agent_intent_text="接下来做什么"`
- `clear`, `compact`: public session commands
- `setup`, `storyline`, `outline`, `chapter`: `public=False`, `legacy=True`, no direct `action_type`

- [ ] **Step 2: Add helper functions**

Add:

```python
def public_chat_command_names() -> list[str]: ...
def is_legacy_chat_command(command_name: str | None) -> bool: ...
def command_to_agent_intent_text(command_name: str | None, args: str | None = None) -> str | None: ...
def legacy_command_to_agent_intent_text(command_name: str, args: str | None = None) -> str: ...
```

- [ ] **Step 3: Refactor dialog command branch**

In `backend/app/api/dialogs.py`:

- Handle `/clear` and `/compact` as before.
- For `command_to_agent_intent_text(...)`, set `effective_text` and fall through to existing text routing.
- For legacy commands, set `effective_text` to a natural language Agent request and attach legacy metadata to the eventual pending action params.
- Ensure the user command message is not saved twice.

- [ ] **Step 4: Refactor slash route projection**

In `backend/app/services/writing_agent/slash_command_route.py`, keep route inspection focused on real slash-command routes and include a trace field such as `legacy_aliases` instead of advertising them as direct routes.

## Task 4: Frontend Implementation

- [ ] **Step 1: Extend frontend command definition**

In `frontend/src/components/workspace/chatCommands.ts`, add:

```typescript
public: boolean
legacy?: boolean
```

Set registry order:

```typescript
continue, status, clear, compact, setup, storyline, outline, chapter
```

- [ ] **Step 2: Filter only public commands**

Update `filterChatCommands` so old module commands are parseable but hidden from autocomplete.

## Task 5: Verification And Report

- [ ] **Step 1: Run targeted backend tests**

```powershell
pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers or continue_command_routes_through_low_detail_agent_continue or legacy_chapter_command_routes_as_agent_intent or command_with_args_enters_preview_pending_action_and_message or command_compact" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "slash_command_route" -q
```

- [ ] **Step 2: Run targeted frontend tests**

```powershell
.\node_modules\.bin\vitest.cmd run frontend/src/components/workspace/chatCommands.test.ts
.\node_modules\.bin\vue-tsc.cmd --noEmit
```

- [ ] **Step 3: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase25-agent-control-slash-commands.md` with:

- Changed behavior.
- RED/GREEN evidence.
- Remaining risk and next suggested phase.
