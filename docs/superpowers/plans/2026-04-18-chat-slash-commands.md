# Chat Slash Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace chat quick-action buttons with Claude Code style slash commands, and add persistent `/clear` and `/compact` context controls.

**Architecture:** FastAPI remains the source of truth for chat history, command dispatch, and compaction state. Vue only handles command discovery, parsing of registered commands, and rendering typed message variants such as summary cards; command side effects like clear/compact always round-trip through the backend so refreshes stay consistent.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, Vue 3, Pinia, TypeScript, Vite, Vitest, `@vue/test-utils`, jsdom, agent-browser

---

## File Structure

```
novelv3/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   │       └── d9f5e6a1c2b3_add_dialog_message_types_and_meta.py
│   ├── app/
│   │   ├── api/
│   │   │   ├── dialogs.py                    # command dispatch, clear/compact, pending-action phrasing
│   │   │   ├── setups.py                     # optional command_args appended to setup prompt
│   │   │   ├── storylines.py                 # optional command_args appended to storyline prompt
│   │   │   └── outlines.py                   # optional command_args appended to outline prompt
│   │   ├── core/
│   │   │   ├── chat_commands.py              # supported command registry + conflict checks
│   │   │   └── chat_compaction.py            # AI summary + deterministic fallback
│   │   ├── models/
│   │   │   └── dialog_message.py             # message_type/meta columns
│   │   └── schemas/
│   │       ├── dialog.py                     # ChatIn / ChatMessageOut typed command + summary fields
│   │       └── __init__.py
│   ├── prompts/
│   │   └── compact_dialog_context.txt        # summary prompt for /compact
│   └── tests/
│       ├── test_dialogs.py                   # clear/compact/command contracts
│       ├── test_setups.py                    # setup command args prompt injection
│       ├── test_storylines.py                # storyline command args prompt injection
│       └── test_outlines.py                  # outline command args prompt injection
├── frontend/
│   ├── package.json                          # add @vue/test-utils + jsdom
│   ├── package-lock.json
│   └── src/
│       ├── api/
│       │   ├── client.ts                     # same endpoint, widened request/response types
│       │   └── types.ts                      # command request + typed summary history fields
│       ├── components/
│       │   ├── ChatMessage.vue               # route summary messages to summary card
│       │   ├── ChatSummaryCard.vue           # foldable compact summary card
│       │   └── workspace/
│       │       ├── ChatCommandMenu.vue       # slash command palette above composer
│       │       ├── ChatWorkspace.vue         # slash input UX, remove quick buttons
│       │       ├── chatCommands.ts           # command registry + parser/filter helpers
│       │       └── chatCommands.test.ts      # parser/filter unit tests
│       ├── stores/
│       │   ├── chat.ts                       # sendCommand + history replacement for clear/compact
│       │   └── chat.workspace.test.ts        # command routing + history replacement tests
│       └── views/
│           └── ProjectDetail.vue             # route send events to sendText / sendCommand
├── scripts/
│   └── verify_full_app_ui.sh                 # smoke slash menu + compact summary + button removal
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-18-chat-slash-commands-design.md
```

## Task 1: Add Typed Chat Message Metadata and Persistence

**Files:**
- Create: `backend/alembic/versions/d9f5e6a1c2b3_add_dialog_message_types_and_meta.py`
- Modify: `backend/app/models/dialog_message.py`
- Modify: `backend/app/schemas/dialog.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/api/dialogs.py`
- Test: `backend/tests/test_dialogs.py`

- [ ] **Step 1: Write the failing backend metadata tests**

`backend/tests/test_dialogs.py`
```python
def test_get_messages_exposes_message_type_and_meta(client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })

    history = client.get(f"/api/v1/dialog/projects/{pid}/messages")
    body = history.json()

    assert history.status_code == 200
    assert body[-1]["message_type"] == "plain"
    assert body[-1]["meta"] is None


def test_command_input_round_trips_as_command_message(client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "setup",
        "command_args": "主角是植物学家",
        "text": "/setup 主角是植物学家",
    })

    history = client.get(f"/api/v1/dialog/projects/{pid}/messages").json()

    assert history[0]["role"] == "user"
    assert history[0]["message_type"] == "command"
    assert history[0]["content"] == "/setup 主角是植物学家"
```

- [ ] **Step 2: Run the targeted backend tests and verify they fail on missing fields**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_get_messages_exposes_message_type_and_meta \
  tests/test_dialogs.py::test_command_input_round_trips_as_command_message -q
```
Expected: FAIL with missing `message_type` / `meta` keys or because `input_type="command"` is not handled yet.

- [ ] **Step 3: Implement model, schema, and migration support for typed chat messages**

`backend/app/models/dialog_message.py`
```python
class DialogMessage(Base):
    __tablename__ = "dialog_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dialog_id = Column(String, ForeignKey("dialogs.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, default="")
    message_type = Column(String, nullable=False, default="plain")
    meta = Column(JSON, nullable=True)
    action_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

`backend/app/schemas/dialog.py`
```python
class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    message_type: str = "plain"
    meta: dict | None = None
    action_result: dict | None = None
    created_at: datetime


class ChatIn(BaseModel):
    project_id: str
    input_type: str = "text"
    text: str = ""
    action_type: str | None = None
    command_name: str | None = None
    command_args: str | None = None
    params: dict = Field(default_factory=dict)
```

`backend/alembic/versions/d9f5e6a1c2b3_add_dialog_message_types_and_meta.py`
```python
def upgrade() -> None:
    op.add_column(
        "dialog_messages",
        sa.Column("message_type", sa.String(), nullable=False, server_default="plain"),
    )
    op.add_column(
        "dialog_messages",
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.alter_column("dialog_messages", "message_type", server_default=None)


def downgrade() -> None:
    op.drop_column("dialog_messages", "meta")
    op.drop_column("dialog_messages", "message_type")
```

`backend/app/api/dialogs.py`
```python
def _save_message(
    db: Session,
    dialog_id: str,
    role: str,
    content: str,
    action_result: dict | None = None,
    message_type: str = "plain",
    meta: dict | None = None,
):
    msg = DialogMessage(
        dialog_id=dialog_id,
        role=role,
        content=content,
        message_type=message_type,
        meta=meta,
        action_result=action_result,
    )
    db.add(msg)
    db.commit()
```

- [ ] **Step 4: Re-run the targeted tests and verify they pass**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_get_messages_exposes_message_type_and_meta \
  tests/test_dialogs.py::test_command_input_round_trips_as_command_message -q
```
Expected: PASS.

- [ ] **Step 5: Commit the persistence groundwork**

```bash
cd /home/guixin/project_workspace/novelv3
git add backend/app/models/dialog_message.py backend/app/schemas/dialog.py backend/app/schemas/__init__.py \
  backend/app/api/dialogs.py backend/alembic/versions/d9f5e6a1c2b3_add_dialog_message_types_and_meta.py \
  backend/tests/test_dialogs.py
git commit -m "feat: add typed dialog message metadata"
```

## Task 2: Implement Backend Slash Command Dispatch, /clear, and /compact

**Files:**
- Create: `backend/app/core/chat_commands.py`
- Create: `backend/app/core/chat_compaction.py`
- Create: `backend/prompts/compact_dialog_context.txt`
- Modify: `backend/app/api/dialogs.py`
- Test: `backend/tests/test_dialogs.py`

- [ ] **Step 1: Write failing tests for clear, compact, and command conflict rules**

`backend/tests/test_dialogs.py`
```python
@patch("app.api.dialogs.load_api_key", return_value="sk-test")
@patch("app.api.dialogs.ai_service.complete", new_callable=AsyncMock)
def test_compact_replaces_previous_plain_messages_with_summary(mock_complete, mock_key, client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    mock_complete.return_value.content = "压缩摘要：用户想先完善世界观，再决定故事线。"

    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "先聊世界观"})
    client.post("/api/v1/dialog/chat", json={"project_id": pid, "input_type": "text", "text": "主角是植物学家"})

    res = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "compact",
        "text": "/compact",
    })

    history = client.get(f"/api/v1/dialog/projects/{pid}/messages").json()
    assert res.status_code == 200
    assert history[-1]["message_type"] == "summary"
    assert history[-1]["meta"]["compacted_count"] == 4
    assert history[-1]["meta"]["summary_text"].startswith("压缩摘要：")


def test_clear_removes_old_messages_and_pending_action(client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })

    res = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "clear",
        "text": "/clear",
    })

    history = client.get(f"/api/v1/dialog/projects/{pid}/messages").json()
    assert res.status_code == 200
    assert len(history) == 1
    assert history[0]["content"] == "上下文已清空，你可以开始新的对话。"
    assert history[0]["message_type"] == "command"


def test_compact_is_blocked_while_pending_action_exists(client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    })

    res = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "compact",
        "text": "/compact",
    })

    assert res.status_code == 200
    assert "当前有待确认操作" in res.json()["message"]
```

- [ ] **Step 2: Run the failing command tests**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_compact_replaces_previous_plain_messages_with_summary \
  tests/test_dialogs.py::test_clear_removes_old_messages_and_pending_action \
  tests/test_dialogs.py::test_compact_is_blocked_while_pending_action_exists -q
```
Expected: FAIL because slash commands, summary messages, and clear behavior do not exist.

- [ ] **Step 3: Implement command registry, compaction helper, and chat dispatch**

`backend/app/core/chat_commands.py`
```python
SUPPORTED_CHAT_COMMANDS = {
    "clear": {"supports_args": False, "history_mutation": True},
    "compact": {"supports_args": False, "history_mutation": True},
    "setup": {"supports_args": True, "action_type": "preview_setup"},
    "storyline": {"supports_args": True, "action_type": "preview_storyline"},
    "outline": {"supports_args": True, "action_type": "preview_outline"},
}


def is_supported_chat_command(name: str | None) -> bool:
    return bool(name and name in SUPPORTED_CHAT_COMMANDS)


def command_to_action_type(name: str) -> str | None:
    return SUPPORTED_CHAT_COMMANDS.get(name, {}).get("action_type")


def command_mutates_history(name: str) -> bool:
    return bool(SUPPORTED_CHAT_COMMANDS.get(name, {}).get("history_mutation"))
```

`backend/app/core/chat_compaction.py`
```python
async def build_compact_summary(
    ai_service: AIService,
    prompt_manager: PromptManager,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    source_messages: list[DialogMessage],
) -> dict:
    lines = [f"{item.role}: {item.content}" for item in source_messages if item.content]
    if not lines:
        raise ValueError("no messages to compact")

    prompt = prompt_manager.load(
        "compact_dialog_context",
        {
            "project_name": project.name or "未命名项目",
            "project_genre": project.genre or "未分类题材",
            "project_phase": project.current_phase or "setup",
            "diagnosis": "、".join(diagnosis.missing_items) if diagnosis.missing_items else "无",
            "dialog_history": "\n".join(lines[-20:]),
        },
    )
    try:
        result = await ai_service.complete([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.4)
        summary_text = (result.content or "").strip()
    except Exception:
        summary_text = ""

    if not summary_text:
        summary_text = (
            f"项目当前缺少：{ '、'.join(diagnosis.missing_items) if diagnosis.missing_items else '无' }。\n"
            f"最近消息数：{len(source_messages)}。\n"
            f"最近用户输入：{next((m.content for m in reversed(source_messages) if m.role == 'user'), '无')}。"
        )

    return {
        "title": "上下文摘要",
        "summary_text": summary_text,
        "compacted_count": len(source_messages),
        "command_name": "compact",
    }
```

`backend/app/api/dialogs.py`
```python
if payload.input_type == "command" and payload.command_name:
    _save_message(db, dialog.id, "user", payload.text or f"/{payload.command_name}", message_type="command")

    if payload.command_name == "clear":
        db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog.id).delete()
        dialog.pending_action_id = None
        dialog.state = "chatting"
        db.commit()
        reply = "上下文已清空，你可以开始新的对话。"
        _save_message(db, dialog.id, "system", reply, message_type="command")
        return ChatOut(message=reply, pending_action=None, ui_hint=build_ui_hint("CHATTING", "chat", "idle", "上下文已清空"), refresh_targets=[], project_diagnosis=diagnosis)

    if payload.command_name == "compact":
        if dialog.pending_action_id:
            reply = "当前有待确认操作，先处理完再压缩上下文。"
            _save_message(db, dialog.id, "system", reply, message_type="command")
            return ChatOut(message=reply, pending_action=None, ui_hint=build_ui_hint("PENDING_ACTION", "chat", "idle", "待确认动作阻止 compact"), refresh_targets=[], project_diagnosis=diagnosis)

        source_messages = (
            db.query(DialogMessage)
            .filter(DialogMessage.dialog_id == dialog.id, DialogMessage.message_type == "plain")
            .order_by(DialogMessage.created_at)
            .all()
        )
        meta = await build_compact_summary(ai_service, PromptManager(), project, diagnosis, source_messages)
        compacted_ids = [item.id for item in source_messages]
        if compacted_ids:
            db.query(DialogMessage).filter(DialogMessage.id.in_(compacted_ids)).delete(synchronize_session=False)
            db.commit()
        _save_message(db, dialog.id, "system", meta["summary_text"], message_type="summary", meta=meta)
        return ChatOut(message=meta["summary_text"], pending_action=None, ui_hint=build_ui_hint("CHATTING", "chat", "idle", "上下文已压缩"), refresh_targets=[], project_diagnosis=diagnosis)
```

`backend/prompts/compact_dialog_context.txt`
```text
请把下面的小说项目对话压缩成一段供后续继续工作的上下文摘要。

项目：$project_name
题材：$project_genre
当前阶段：$project_phase
当前缺口：$diagnosis

对话历史：
$dialog_history

输出要求：
1. 用中文。
2. 只保留后续继续创作真正需要的信息。
3. 优先保留用户目标、约束、附加要求、未完成事项。
4. 不要写寒暄。
```

- [ ] **Step 4: Run the command tests again and verify they pass**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_compact_replaces_previous_plain_messages_with_summary \
  tests/test_dialogs.py::test_clear_removes_old_messages_and_pending_action \
  tests/test_dialogs.py::test_compact_is_blocked_while_pending_action_exists -q
```
Expected: PASS.

- [ ] **Step 5: Commit command dispatch and compaction**

```bash
cd /home/guixin/project_workspace/novelv3
git add backend/app/core/chat_commands.py backend/app/core/chat_compaction.py backend/prompts/compact_dialog_context.txt \
  backend/app/api/dialogs.py backend/tests/test_dialogs.py
git commit -m "feat: add slash command clear and compact flows"
```

## Task 3: Pass Command Arguments Through Pending Actions and Generation Prompts

**Files:**
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/setups.py`
- Modify: `backend/app/api/storylines.py`
- Modify: `backend/app/api/outlines.py`
- Test: `backend/tests/test_dialogs.py`
- Test: `backend/tests/test_setups.py`
- Test: `backend/tests/test_storylines.py`
- Test: `backend/tests/test_outlines.py`

- [ ] **Step 1: Write failing tests for command argument plumbing**

`backend/tests/test_dialogs.py`
```python
def test_setup_command_stores_command_args_in_pending_action(client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    res = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "command",
        "command_name": "setup",
        "command_args": "主角是植物学家",
        "text": "/setup 主角是植物学家",
    })

    body = res.json()
    assert body["pending_action"]["type"] == "preview_setup"
    assert body["pending_action"]["params"]["command_args"] == "主角是植物学家"
    assert "附加要求：主角是植物学家" in body["message"]
```

`backend/tests/test_setups.py`
```python
@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_generate_setup_appends_command_args_to_prompt(mock_parse, mock_complete, mock_key, client):
    project = client.post("/api/v1/projects", json={"name": "Test"}).json()
    pid = project["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    client.post("/api/v1/projects/{}/setup/generate?command_args=主角是植物学家".format(pid))

    sent_messages = mock_complete.await_args.args[0]
    assert "附加要求：主角是植物学家" in sent_messages[0]["content"]
```

- [ ] **Step 2: Run the failing generation-arg tests**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_setup_command_stores_command_args_in_pending_action \
  tests/test_setups.py::test_generate_setup_appends_command_args_to_prompt -q
```
Expected: FAIL because `command_args` are neither stored nor appended.

- [ ] **Step 3: Implement command arg storage and prompt injection**

`backend/app/api/dialogs.py`
```python
def _pending_reply(action_type: str, command_args: str | None = None) -> str:
    base = _action_description(action_type)
    if command_args:
        return f"{base} 附加要求：{command_args}。确认执行吗？"
    return f"{base} 确认执行吗？"


pending = PendingAction(
    dialog_id=dialog.id,
    type=candidate.type,
    params={
        "project_id": payload.project_id,
        "command_args": payload.command_args or "",
    },
)
```

`backend/app/api/setups.py`
```python
@router.post("/generate", response_model=SetupOut)
async def generate_setup(project_id: str, db: Session = Depends(get_db), command_args: str | None = None):
    ...
    if command_args:
        prompt = f"{prompt}\n\n【附加要求】\n{command_args}"
```

`backend/app/api/storylines.py`
```python
@router.post("/generate", response_model=StorylineOut)
async def generate_storyline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None):
    ...
    if command_args:
        prompt = f"{prompt}\n\n【附加要求】\n{command_args}"
```

`backend/app/api/outlines.py`
```python
@router.post("/generate", response_model=OutlineOut)
async def generate_outline(project_id: str, db: Session = Depends(get_db), command_args: str | None = None):
    ...
    if command_args:
        prompt = f"{prompt}\n\n【附加要求】\n{command_args}"
```

`backend/app/api/dialogs.py`
```python
async def _execute_action(action_type: str, project_id: str, db: Session, command_args: str | None = None) -> dict:
    if action_type == "generate_setup":
        await generate_setup(project_id, db, command_args=command_args)
    elif action_type == "generate_storyline":
        await generate_storyline(project_id, db, command_args=command_args)
    elif action_type == "generate_outline":
        await generate_outline(project_id, db, command_args=command_args)
```

- [ ] **Step 4: Run all command-arg tests and verify they pass**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/backend && source .venv/bin/activate
pytest tests/test_dialogs.py::test_setup_command_stores_command_args_in_pending_action \
  tests/test_setups.py tests/test_storylines.py tests/test_outlines.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit prompt argument plumbing**

```bash
cd /home/guixin/project_workspace/novelv3
git add backend/app/api/dialogs.py backend/app/api/setups.py backend/app/api/storylines.py \
  backend/app/api/outlines.py backend/tests/test_dialogs.py backend/tests/test_setups.py \
  backend/tests/test_storylines.py backend/tests/test_outlines.py
git commit -m "feat: pass slash command args into generation prompts"
```

## Task 4: Add Frontend Command Registry, Parsing, and Store Support

**Files:**
- Create: `frontend/src/components/workspace/chatCommands.ts`
- Create: `frontend/src/components/workspace/chatCommands.test.ts`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/chat.workspace.test.ts`
- Modify: `frontend/src/views/ProjectDetail.vue`

- [ ] **Step 1: Write failing frontend parser and store tests**

`frontend/src/components/workspace/chatCommands.test.ts`
```ts
import { describe, expect, it } from 'vitest'
import { filterChatCommands, parseSlashCommand } from './chatCommands'

describe('chat slash commands', () => {
  it('只解析已注册命令，未知 slash 文本回落为普通文本', () => {
    expect(parseSlashCommand('/setup 主角是植物学家')).toEqual({
      kind: 'command',
      name: 'setup',
      args: '主角是植物学家',
      raw: '/setup 主角是植物学家',
    })
    expect(parseSlashCommand('/foo bar')).toEqual({
      kind: 'text',
      raw: '/foo bar',
    })
  })

  it('按前缀过滤 slash 菜单', () => {
    expect(filterChatCommands('/co').map((item) => item.name)).toEqual(['compact'])
  })
})
```

`frontend/src/stores/chat.workspace.test.ts`
```ts
it('sendCommand(compact) 会在返回后重拉历史而不是只追加一条消息', async () => {
  const store = useChatStore()
  store.projectId = 'project-1'

  vi.mocked(api.sendChat).mockResolvedValue({
    message: '压缩完成',
    pending_action: null,
    ui_hint: null,
    refresh_targets: [],
    project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
  })
  vi.mocked(api.getMessages).mockResolvedValue([
    {
      role: 'system',
      content: '压缩摘要正文',
      message_type: 'summary',
      meta: { title: '上下文摘要', summary_text: '压缩摘要正文', compacted_count: 6, command_name: 'compact' },
    },
  ] as any)

  await store.sendCommand('compact', '', '/compact')

  expect(api.getMessages).toHaveBeenCalledWith('project-1')
  expect(store.messages[0].message_type).toBe('summary')
})
```

- [ ] **Step 2: Run the failing frontend unit tests**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/frontend
npm run test:unit -- src/components/workspace/chatCommands.test.ts src/stores/chat.workspace.test.ts
```
Expected: FAIL because parser helpers and `sendCommand()` do not exist.

- [ ] **Step 3: Implement command registry, parser, and store support**

`frontend/src/components/workspace/chatCommands.ts`
```ts
export type ChatCommandName = 'clear' | 'compact' | 'setup' | 'storyline' | 'outline'

export const CHAT_COMMANDS = [
  { name: 'clear', label: '/clear', description: '清空当前项目对话上下文', example: '/clear', supportsArgs: false },
  { name: 'compact', label: '/compact', description: '压缩当前对话为摘要', example: '/compact', supportsArgs: false },
  { name: 'setup', label: '/setup', description: '发起设定生成，可附加要求', example: '/setup 主角是植物学家', supportsArgs: true },
  { name: 'storyline', label: '/storyline', description: '发起故事线生成，可附加要求', example: '/storyline 冲突更集中', supportsArgs: true },
  { name: 'outline', label: '/outline', description: '发起大纲生成，可附加要求', example: '/outline 12章，节奏快', supportsArgs: true },
] as const

export function parseSlashCommand(raw: string) {
  const trimmed = raw.trim()
  if (!trimmed.startsWith('/')) return { kind: 'text' as const, raw }
  const [token, ...rest] = trimmed.slice(1).split(/\s+/)
  const match = CHAT_COMMANDS.find((item) => item.name === token)
  if (!match) return { kind: 'text' as const, raw }
  return { kind: 'command' as const, name: match.name, args: rest.join(' ').trim(), raw: trimmed }
}

export function filterChatCommands(raw: string) {
  const query = raw.startsWith('/') ? raw.slice(1).trim() : ''
  const token = query.split(/\s+/)[0] || ''
  return CHAT_COMMANDS.filter((item) => item.name.startsWith(token))
}
```

`frontend/src/stores/chat.ts`
```ts
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type?: 'plain' | 'summary' | 'command'
  meta?: Record<string, unknown> | null
  pending_action?: PendingAction | null
  diagnosis?: Diagnosis | null
  action_result?: Record<string, unknown> | null
}

async function sendCommand(name: string, args = '', rawInput = `/${name}`): Promise<ChatResponse | null> {
  if (loading.value) return null
  const { pidSnapshot, versionSnapshot } = captureSnapshot()
  messages.value.push({ role: 'user', content: rawInput, message_type: 'command' })
  loading.value = true
  try {
    const res = await api.sendChat({
      project_id: pidSnapshot,
      input_type: 'command',
      text: rawInput,
      command_name: name,
      command_args: args,
    })
    if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
    if (name === 'clear' || name === 'compact') {
      await loadHistory(pidSnapshot, versionSnapshot)
    } else {
      messages.value.push({ role: 'assistant', content: res.message, message_type: 'plain', pending_action: res.pending_action || null, diagnosis: res.project_diagnosis || null })
    }
    if (res.pending_action) pendingAction.value = res.pending_action
    if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
    return res
  } finally {
    if (isActiveSnapshot(pidSnapshot, versionSnapshot)) loading.value = false
  }
}
```

`frontend/src/views/ProjectDetail.vue`
```ts
import { parseSlashCommand } from '../components/workspace/chatCommands'

async function send(text: string) {
  if (chat.pendingAction) return
  const parsed = parseSlashCommand(text)
  if (parsed.kind === 'command') {
    workspace.applyUserPanel(workspace.panel, `你输入了 ${parsed.raw}`)
    const res = await chat.sendCommand(parsed.name, parsed.args, parsed.raw)
    await handleResponse(res)
    return
  }
  workspace.applyUserPanel(workspace.panel, '你发送了一条消息')
  const res = await chat.sendText(text)
  await handleResponse(res)
}
```

- [ ] **Step 4: Re-run the frontend unit tests and verify they pass**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/frontend
npm run test:unit -- src/components/workspace/chatCommands.test.ts src/stores/chat.workspace.test.ts
```
Expected: PASS.

- [ ] **Step 5: Commit the command parsing layer**

```bash
cd /home/guixin/project_workspace/novelv3
git add frontend/src/components/workspace/chatCommands.ts frontend/src/components/workspace/chatCommands.test.ts \
  frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/chat.ts \
  frontend/src/stores/chat.workspace.test.ts frontend/src/views/ProjectDetail.vue
git commit -m "feat: add frontend slash command parsing"
```

## Task 5: Replace Quick Buttons with Slash Menu and Summary Card UI

**Files:**
- Create: `frontend/src/components/ChatSummaryCard.vue`
- Create: `frontend/src/components/workspace/ChatCommandMenu.vue`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/components/ChatMessage.vue`
- Modify: `frontend/src/components/workspace/ChatWorkspace.vue`
- Delete: `frontend/src/components/QuickActions.vue`
- Test: `frontend/src/components/workspace/ChatWorkspace.commands.test.ts`

- [ ] **Step 1: Write failing component tests for slash menu and summary card**

`frontend/src/components/workspace/ChatWorkspace.commands.test.ts`
```ts
// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatWorkspace from './ChatWorkspace.vue'

const baseProps = {
  project: { name: '测试项目', genre: '科幻', current_word_count: 0, status: 'draft', current_phase: 'setup' },
  tabs: [],
  panel: 'overview',
  mode: 'auto',
  source: 'system',
  reason: '',
  messages: [],
  diagnosis: null,
  pendingAction: null,
  loading: false,
}

describe('ChatWorkspace slash UI', () => {
  it('输入 / 时展示命令菜单并支持回车补全', async () => {
    const wrapper = mount(ChatWorkspace, { props: baseProps })
    const input = wrapper.get('input')

    await input.setValue('/')
    expect(wrapper.text()).toContain('/compact')

    await input.trigger('keydown.arrow-down')
    await input.trigger('keydown.enter')
    expect((input.element as HTMLInputElement).value).toBe('/compact ')
  })

  it('summary 消息渲染为可折叠摘要卡', async () => {
    const wrapper = mount(ChatWorkspace, {
      props: {
        ...baseProps,
        messages: [{
          role: 'system',
          content: '压缩摘要正文',
          message_type: 'summary',
          meta: { title: '上下文摘要', summary_text: '压缩摘要正文', compacted_count: 6 },
        }],
      },
    })

    expect(wrapper.text()).toContain('上下文摘要')
    expect(wrapper.text()).not.toContain('压缩摘要正文')

    await wrapper.get('[data-testid="summary-card"]').trigger('click')
    expect(wrapper.text()).toContain('压缩摘要正文')
  })
})
```

- [ ] **Step 2: Install missing test dependencies and confirm the new component test fails**

`frontend/package.json`
```json
{
  "devDependencies": {
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^25.0.1"
  }
}
```

Run:
```bash
cd /home/guixin/project_workspace/novelv3/frontend
npm install
npm run test:unit -- src/components/workspace/ChatWorkspace.commands.test.ts
```
Expected: FAIL because slash menu and summary card UI do not exist yet.

- [ ] **Step 3: Implement the menu, summary card, and quick-action removal**

`frontend/src/components/ChatSummaryCard.vue`
```vue
<template>
  <button data-testid="summary-card" class="summary-card" type="button" @click="expanded = !expanded">
    <div class="summary-card__head">
      <div>
        <p class="summary-card__title">{{ title }}</p>
        <p class="summary-card__meta">已压缩 {{ compactedCount }} 条消息</p>
      </div>
      <span class="summary-card__toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    <p v-if="expanded" class="summary-card__copy">{{ summaryText }}</p>
    <p v-else class="summary-card__hint">点击展开查看摘要</p>
  </button>
</template>
```

`frontend/src/components/ChatMessage.vue`
```vue
<template>
  <div v-if="msg.message_type === 'summary'" class="message-row justify-start">
    <ChatSummaryCard :meta="msg.meta" :content="msg.content" />
  </div>
  <div v-else class="message-row" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
    ...
  </div>
</template>
```

`frontend/src/components/workspace/ChatCommandMenu.vue`
```vue
<template>
  <div v-if="show && items.length" class="chat-command-menu">
    <button
      v-for="(item, index) in items"
      :key="item.name"
      type="button"
      class="chat-command-menu__item"
      :class="{ 'is-active': index === activeIndex }"
      @mousedown.prevent="$emit('pick', item.name)"
    >
      <div class="chat-command-menu__name">/{{ item.name }}</div>
      <div class="chat-command-menu__description">{{ item.description }}</div>
      <div class="chat-command-menu__example">{{ item.example }}</div>
    </button>
  </div>
</template>
```

`frontend/src/components/workspace/ChatWorkspace.vue`
```vue
<ChatCommandMenu
  :show="showCommandMenu"
  :items="commandSuggestions"
  :active-index="activeCommandIndex"
  @pick="applyCommandSelection"
/>

<input
  v-model="input"
  placeholder="输入消息，或键入 / 查看命令"
  @keydown.down.prevent="moveCommandSelection(1)"
  @keydown.up.prevent="moveCommandSelection(-1)"
  @keydown.esc="closeCommandMenu"
  @keydown.enter="onEnter"
/>
```

`frontend/src/components/workspace/ChatWorkspace.vue`
```ts
const commandSuggestions = computed(() => filterChatCommands(input.value))
const showCommandMenu = computed(() => input.value.startsWith('/') && !input.value.trim().includes(' ') ? commandSuggestions.value.length > 0 : input.value.trim() === '/')
const activeCommandIndex = ref(0)

function applyCommandSelection(name: string) {
  input.value = `/${name} `
  activeCommandIndex.value = 0
}

function onEnter(event: KeyboardEvent) {
  if (showCommandMenu.value) {
    event.preventDefault()
    const current = commandSuggestions.value[activeCommandIndex.value]
    if (current) applyCommandSelection(current.name)
    return
  }
  submit()
}
```

- [ ] **Step 4: Run component tests, unit tests, and build**

Run:
```bash
cd /home/guixin/project_workspace/novelv3/frontend
npm run test:unit -- src/components/workspace/ChatWorkspace.commands.test.ts src/components/workspace/chatCommands.test.ts src/stores/chat.workspace.test.ts
npm run build
```
Expected: PASS.

- [ ] **Step 5: Commit the slash UI**

```bash
cd /home/guixin/project_workspace/novelv3
git add frontend/package.json frontend/package-lock.json frontend/src/components/ChatSummaryCard.vue \
  frontend/src/components/ChatMessage.vue frontend/src/components/workspace/ChatCommandMenu.vue \
  frontend/src/components/workspace/ChatWorkspace.vue frontend/src/components/workspace/ChatWorkspace.commands.test.ts \
  frontend/src/components/workspace/chatCommands.test.ts
git rm frontend/src/components/QuickActions.vue
git commit -m "feat: replace quick chat buttons with slash command ui"
```

## Task 6: Extend Regression Coverage and Run Full Verification

**Files:**
- Modify: `scripts/verify_full_app_ui.sh`

- [ ] **Step 1: Extend the browser smoke flow to cover slash commands**

`scripts/verify_full_app_ui.sh`
```bash
TEMP_PROJECT_ID="$(curl -fsS -H 'Content-Type: application/json' -X POST \
  -d '{"name":"Slash Smoke Project","genre":"科幻"}' \
  "${BACKEND_BASE_URL}/api/v1/projects" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

run agent-browser --session "${AB_SESSION}" open "${FRONTEND_BASE_URL}/projects/${TEMP_PROJECT_ID}"
run agent-browser --session "${AB_SESSION}" wait 1000
run agent-browser --session "${AB_SESSION}" fill "input[placeholder*='键入 / 查看命令']" "/"
run agent-browser --session "${AB_SESSION}" wait 300

cat <<'EOF' | agent-browser --session "${AB_SESSION}" eval --stdin
(() => {
  const body = document.body.innerText
  if (!body.includes('/compact')) throw new Error('slash menu missing /compact')
  if (body.includes('生成设定') || body.includes('生成故事线') || body.includes('生成大纲')) {
    throw new Error('legacy quick action buttons still visible')
  }
  return true
})()
EOF
```

- [ ] **Step 2: Run the full verification script**

Run:
```bash
cd /home/guixin/project_workspace/novelv3
./scripts/verify_full_app_ui.sh
```
Expected: backend pytest PASS, frontend unit PASS, build PASS, agent-browser smoke PASS with zero page errors and zero console errors.

- [ ] **Step 3: Commit the verification update**

```bash
cd /home/guixin/project_workspace/novelv3
git add scripts/verify_full_app_ui.sh
git commit -m "test: cover slash command workspace smoke flow"
```

## Self-Review

Spec coverage check:

- Slash command registry and unknown slash fallback: Task 4 and Task 5.
- `/clear` persistence and pending-action reset: Task 2.
- `/compact` summary persistence and foldable summary card: Task 2 and Task 5.
- Removal of quick buttons: Task 5.
- Generation commands with extra args: Task 3.
- Browser smoke and regression coverage: Task 6.

Placeholder scan:

- No `TODO` / `TBD` markers remain.
- Every task names exact files, commands, and code shapes.

Type consistency:

- Backend command input uses `input_type='command'`, `command_name`, `command_args` across Task 1, 2, and 4.
- Frontend summary rendering uses `message_type='summary'` and `meta.summary_text` consistently across Task 1, 4, and 5.
