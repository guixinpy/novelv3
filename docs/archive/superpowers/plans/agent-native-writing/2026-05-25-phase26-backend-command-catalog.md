# Phase26 Backend Command Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend Agent command catalog the authoritative source for the Hermes slash-command UI.

**Architecture:** Backend owns command definitions and publishes a versioned catalog endpoint. Frontend keeps a static fallback but loads the backend catalog on Hermes initialization and passes it into slash parsing/filtering.

**Tech Stack:** FastAPI, pytest, Vue 3, Pinia, Vitest, TypeScript.

---

## Success Criteria

- Backend exposes `GET /api/v1/dialog/chat-commands`.
- The response lists public Agent controls and hidden legacy aliases with explicit metadata.
- Frontend `ChatInput` accepts a command catalog prop and uses it for menu filtering and parsing.
- `HermesView` loads the backend catalog during initialization and falls back to the static catalog if loading fails.
- Legacy module commands remain parseable only if present in the catalog and remain hidden from menu candidates.

## Files

- Modify: `backend/app/core/chat_commands.py`
  - Add catalog-facing metadata and command catalog builder.
- Modify: `backend/app/api/dialogs.py`
  - Add `GET /api/v1/dialog/chat-commands`.
- Modify: `backend/tests/test_dialogs.py`
  - Add endpoint contract coverage.
- Modify: `frontend/src/api/types.ts`
  - Add command catalog response types.
- Modify: `frontend/src/api/client.ts`
  - Add `getChatCommandCatalog`.
- Modify: `frontend/src/components/workspace/chatCommands.ts`
  - Accept externally supplied command definitions.
  - Normalize backend snake_case command records.
- Modify: `frontend/src/components/workspace/chatCommands.test.ts`
  - Cover backend catalog normalization and catalog-aware parsing/filtering.
- Modify: `frontend/src/components/chat/ChatInput.vue`
  - Accept `commands` prop and use it for menu/parser behavior.
- Modify: `frontend/src/views/HermesView.vue`
  - Load command catalog and pass it to `ChatInput`.
- Modify: `frontend/src/views/HermesView.test.ts`
  - Verify the view asks backend for the command catalog and passes it to the input.

## Task 1: Backend RED

- [ ] **Step 1: Add failing endpoint test**

In `backend/tests/test_dialogs.py`:

```python
def test_chat_command_catalog_endpoint_returns_agent_control_surface(client):
    response = client.get("/api/v1/dialog/chat-commands")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "phase26.agent_chat_command_catalog.v1"
    assert data["public_command_names"] == ["continue", "status", "clear", "compact"]
    assert data["legacy_alias_names"] == ["setup", "storyline", "outline", "chapter"]
    commands = {command["name"]: command for command in data["commands"]}
    assert commands["continue"]["public"] is True
    assert commands["continue"]["agent_intent_text"] == "继续"
    assert commands["setup"]["public"] is False
    assert commands["setup"]["legacy"] is True
    assert "action_type" not in commands["setup"]
```

- [ ] **Step 2: Run RED backend test**

```powershell
pytest backend/tests/test_dialogs.py -k "chat_command_catalog_endpoint" -q
```

Expected: fail with 404.

## Task 2: Frontend RED

- [ ] **Step 1: Add failing parser/catalog tests**

In `frontend/src/components/workspace/chatCommands.test.ts`:

```typescript
it('可从后端目录规范化命令定义并驱动解析与过滤', () => {
  const commands = normalizeChatCommandDefinitions([
    { name: 'continue', label: '/continue', description: '继续', example: '/continue', supports_args: false, public: true },
    { name: 'memory', label: '/memory', description: '记忆', example: '/memory', supports_args: false, public: true },
    { name: 'chapter', label: '/chapter', description: '旧命令', example: '/chapter 1', supports_args: true, public: false, legacy: true },
  ])

  expect(filterChatCommands('/m', commands).map((command) => command.name)).toEqual(['memory'])
  expect(parseSlashCommand('/memory', commands)).toMatchObject({ kind: 'command', name: 'memory' })
  expect(filterChatCommands('/ch', commands)).toEqual([])
  expect(parseSlashCommand('/chapter 1', commands)).toMatchObject({ kind: 'command', name: 'chapter' })
})
```

- [ ] **Step 2: Add failing HermesView loading test**

In `frontend/src/views/HermesView.test.ts`, update the `ChatInput` stub to accept `commands`, and add:

```typescript
it('loads backend command catalog and passes it to chat input', async () => {
  vi.mocked(api.getChatCommandCatalog).mockResolvedValueOnce({
    version: 'phase26.agent_chat_command_catalog.v1',
    public_command_names: ['continue', 'status', 'clear', 'compact'],
    legacy_alias_names: ['setup'],
    commands: [
      { name: 'continue', label: '/continue', description: '继续', example: '/continue', supports_args: false, public: true },
      { name: 'setup', label: '/setup', description: '旧命令', example: '/setup', supports_args: true, public: false, legacy: true },
    ],
  } as any)

  const wrapper = await mountHermesView()

  expect(api.getChatCommandCatalog).toHaveBeenCalled()
  expect(wrapper.get('[data-testid="chat-input"]').text()).toContain('continue')
})
```

- [ ] **Step 3: Run RED frontend tests**

```powershell
cd frontend
.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/views/HermesView.test.ts
```

Expected: fail because normalization and API loading are missing.

## Task 3: Backend Implementation

- [ ] **Step 1: Add catalog metadata**

In `backend/app/core/chat_commands.py`, extend `ChatCommandSpec` with `example` and `supports_args`.

- [ ] **Step 2: Add catalog builder**

Add:

```python
CHAT_COMMAND_CATALOG_VERSION = "phase26.agent_chat_command_catalog.v1"

def chat_command_catalog() -> dict:
    ...
```

The catalog must include all commands, but explicitly distinguish `public` and `legacy`.

- [ ] **Step 3: Add API route**

In `backend/app/api/dialogs.py`:

```python
@router.get("/api/v1/dialog/chat-commands")
def chat_commands():
    return chat_command_catalog()
```

## Task 4: Frontend Implementation

- [ ] **Step 1: Add API types and client method**

Add `ChatCommandCatalogResponse` and `ChatCommandCatalogItem` to `frontend/src/api/types.ts`.

Add `getChatCommandCatalog` to `frontend/src/api/client.ts`.

- [ ] **Step 2: Make command parser catalog-aware**

Update `parseSlashCommand(input, commands = chatCommandRegistry)` and `filterChatCommands(query, commands = chatCommandRegistry)`.

Add `normalizeChatCommandDefinitions`.

- [ ] **Step 3: Wire command catalog into HermesView**

In `HermesView.vue`:

- Add `chatCommands = ref(chatCommandRegistry)`.
- Load backend catalog during initialization.
- Pass `:commands="chatCommands"` to `ChatInput`.
- Parse outgoing slash input with `parseSlashCommand(text, chatCommands.value)`.

- [ ] **Step 4: Update ChatInput**

Add `commands?: ChatCommandDefinition[]` prop and use it for filter/parser.

## Task 5: Verification And Report

- [ ] **Step 1: Targeted verification**

```powershell
pytest backend/tests/test_dialogs.py -k "chat_command_catalog_endpoint or chat_command_registry_helpers or command_with_args_enters_preview_pending_action_and_message" -q
cd frontend
.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/views/HermesView.test.ts src/stores/chat.workspace.test.ts
.\node_modules\.bin\vue-tsc.cmd --noEmit
```

- [ ] **Step 2: Write report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase26-backend-command-catalog.md` with RED/GREEN evidence and remaining risks.
