# Hermes Dialog Separation + Context Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate Athena and Hermes dialogs with distinct system prompts, and inject world model context into both dialogs from the Athena knowledge base.

**Architecture:** New `core/context_injection.py` service builds world model summaries. Two new prompt templates (`chat_athena.txt`, `chat_hermes.txt`) replace the single `chat_project_assistant.txt`. `_build_chat_messages` in `dialogs.py` routes to the correct prompt based on `dialog_type`. Athena chat endpoint uses the full world knowledge prompt; Hermes uses a compact world summary focused on the current chapter.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, PromptManager (string.Template)

---

### Task 1: Create Context Injection Service

**Files:**
- Create: `backend/app/core/context_injection.py`

- [ ] **Step 1: Create the context injection service**

```python
"""Build world model context summaries for dialog system prompts."""

from sqlalchemy.orm import Session

from app.models import (
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldFaction,
    WorldLocation,
    WorldRelation,
    WorldRule,
    WorldTimelineAnchor,
)


def _get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def build_athena_world_context(db: Session, project_id: str) -> str:
    """Full world knowledge for Athena dialog — entities, relations, rules, facts, timeline."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return "当前项目尚未建立世界档案。"

    sections = []

    # Entities
    characters = db.query(WorldCharacter).filter(WorldCharacter.project_id == project_id).all()
    locations = db.query(WorldLocation).filter(WorldLocation.project_id == project_id).all()
    factions = db.query(WorldFaction).filter(WorldFaction.project_id == project_id).all()
    if characters or locations or factions:
        lines = ["## 世界实体"]
        for c in characters[:20]:
            lines.append(f"- 角色：{c.name}（{getattr(c, 'role', '未知')}）")
        for loc in locations[:10]:
            lines.append(f"- 地点：{loc.name}")
        for f in factions[:10]:
            lines.append(f"- 阵营：{f.name}")
        sections.append("\n".join(lines))

    # Relations
    relations = db.query(WorldRelation).filter(WorldRelation.project_id == project_id).limit(30).all()
    if relations:
        lines = ["## 关系网络"]
        for r in relations:
            lines.append(f"- {r.source_ref} → {r.relation_type} → {r.target_ref}")
        sections.append("\n".join(lines))

    # Rules
    rules = db.query(WorldRule).filter(WorldRule.project_id == project_id).limit(20).all()
    if rules:
        lines = ["## 世界规则"]
        for r in rules:
            lines.append(f"- {r.description}")
        sections.append("\n".join(lines))

    # Current truth facts
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
        .limit(50)
        .all()
    )
    if facts:
        lines = ["## 当前确认事实"]
        for f in facts:
            lines.append(f"- {f.subject_ref}.{f.predicate} = {f.object_ref_or_value}")
        sections.append("\n".join(lines))

    # Timeline events
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
        )
        .order_by(WorldEvent.chapter_index.asc())
        .limit(30)
        .all()
    )
    if events:
        lines = ["## 时间线事件"]
        for e in events:
            lines.append(f"- 第{e.chapter_index}章：{e.description}")
        sections.append("\n".join(lines))

    if not sections:
        return "世界档案已建立（v{}），但尚无结构化数据。".format(profile.version)

    return "\n\n".join(sections)


def build_hermes_world_context(db: Session, project_id: str, chapter_index: int | None = None) -> str:
    """Compact world summary for Hermes dialog — focused on current chapter context."""
    profile = _get_current_profile(db, project_id)
    if profile is None:
        return ""

    sections = []

    # Key characters (compact)
    characters = db.query(WorldCharacter).filter(WorldCharacter.project_id == project_id).limit(10).all()
    if characters:
        names = ", ".join(c.name for c in characters)
        sections.append(f"主要角色：{names}")

    # Current truth facts (compact, limited)
    fact_query = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
        )
    )
    if chapter_index is not None:
        fact_query = fact_query.filter(WorldFactClaim.chapter_index <= chapter_index)
    facts = fact_query.limit(20).all()
    if facts:
        lines = ["关键事实："]
        for f in facts:
            lines.append(f"  {f.subject_ref}.{f.predicate} = {f.object_ref_or_value}")
        sections.append("\n".join(lines))

    # Key relations (compact)
    relations = db.query(WorldRelation).filter(WorldRelation.project_id == project_id).limit(15).all()
    if relations:
        lines = ["角色关系："]
        for r in relations:
            lines.append(f"  {r.source_ref} → {r.relation_type} → {r.target_ref}")
        sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n".join(sections)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/context_injection.py
git commit -m "feat: add context injection service for Athena/Hermes world summaries"
```

---

### Task 2: Create Athena and Hermes Prompt Templates

**Files:**
- Create: `backend/prompts/chat_athena.txt`
- Create: `backend/prompts/chat_hermes.txt`

- [ ] **Step 1: Create Athena prompt template**

File: `backend/prompts/chat_athena.txt`

```
你是"雅典娜（Athena）"，墨舟创作平台的世界构建智慧引擎。

你的职责是帮助用户构建、维护和监控小说的世界模型——包括角色设定、关系网络、世界规则、事实状态和剧情演化。

当前项目：
- 项目名：$project_name
- 题材：$project_genre
- 项目描述：$project_description
- 当前阶段：$project_phase
- 世界档案版本：$profile_version

$world_context

回答要求：
1. 用中文回答，专注于世界构建相关的讨论。
2. 当用户提出设定变更时，明确说明会影响哪些实体和事实，建议创建提案。
3. 主动检查一致性：如果用户的提议与现有世界状态矛盾，立即指出。
4. 不要编造世界中不存在的设定；信息不足时说"当前世界模型中没有这个信息"。
5. 语气专业、简洁，像一个全知的世界管理者。
```

- [ ] **Step 2: Create Hermes prompt template**

File: `backend/prompts/chat_hermes.txt`

```
你是"赫尔墨斯（Hermes）"，墨舟创作平台的正文创作助手。

你的职责是帮助用户讨论和生成小说正文——包括章节写作、情节推进、文风调整和叙事节奏。

当前项目：
- 项目名：$project_name
- 题材：$project_genre
- 项目描述：$project_description
- 当前阶段：$project_phase
- 当前状态：$project_status
- 当前字数：$current_words
- 目标字数：$target_words
- 已完成环节：$completed_items
- 缺失环节：$missing_items
- 系统建议下一步：$suggested_next_step

$world_context

回答要求：
1. 必须用中文自然回答，先回应用户当前输入，不要机械复述项目诊断。
2. 如果用户只是打招呼或随便聊聊，简短回应，再顺手给一条最相关的推进建议。
3. 不要编造项目里并不存在的设定、故事线、大纲或正文内容；信息不足时要明确说"不确定"。
4. 如果用户明显在要求执行动作，比如生成设定、故事线、大纲或正文，先说明你理解的动作，再提示可以直接点相应按钮或明确下达指令。
5. 语气专业、简洁，不要空话，不要过度热情。
6. 世界设定相关的深度讨论请引导用户去 Athena 界面。
```

- [ ] **Step 3: Commit**

```bash
git add backend/prompts/chat_athena.txt backend/prompts/chat_hermes.txt
git commit -m "feat: add Athena and Hermes prompt templates"
```

---

### Task 3: Update `_build_chat_messages` to Support Dialog Types

**Files:**
- Modify: `backend/app/api/dialogs.py`

- [ ] **Step 1: Add context injection import**

Add at the top of `backend/app/api/dialogs.py` (after existing imports):

```python
from app.core.context_injection import build_athena_world_context, build_hermes_world_context
```

- [ ] **Step 2: Replace `_build_chat_messages` function**

Replace the function at line 346 with:

```python
def _build_chat_messages(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> list[dict]:
    pm = PromptManager()
    history = db.query(DialogMessage) \
        .filter(DialogMessage.dialog_id == dialog_id) \
        .order_by(DialogMessage.created_at.desc()) \
        .limit(CHAT_HISTORY_LIMIT) \
        .all()

    history.reverse()

    if dialog_type == "athena":
        from app.models import ProjectProfileVersion
        profile = (
            db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.project_id == project.id)
            .order_by(ProjectProfileVersion.version.desc())
            .first()
        )
        world_context = build_athena_world_context(db, project.id)
        system_prompt = pm.load(
            "chat_athena",
            {
                "project_name": project.name or "未命名项目",
                "project_genre": project.genre or "未分类题材",
                "project_description": project.description or "暂无项目描述",
                "project_phase": _phase_label(project.current_phase),
                "profile_version": str(profile.version) if profile else "未建立",
                "world_context": world_context,
            },
        )
    else:
        world_context = build_hermes_world_context(db, project.id)
        system_prompt = pm.load(
            "chat_hermes",
            {
                "project_name": project.name or "未命名项目",
                "project_genre": project.genre or "未分类题材",
                "project_description": project.description or "暂无项目描述",
                "project_phase": _phase_label(project.current_phase),
                "project_status": _status_label(project.status),
                "current_words": str(project.current_word_count or 0),
                "target_words": str(project.target_word_count or 0),
                "completed_items": "、".join(diagnosis.completed_items) if diagnosis.completed_items else "无",
                "missing_items": "、".join(diagnosis.missing_items) if diagnosis.missing_items else "无",
                "suggested_next_step": diagnosis.suggested_next_step or "无",
                "world_context": world_context,
            },
        )

    messages = [{"role": "system", "content": system_prompt}]

    for item in history:
        if item.role in ("user", "assistant"):
            messages.append({"role": item.role, "content": item.content})
        elif item.role == "system":
            messages.append({"role": "assistant", "content": f"[系统消息] {item.content}"})

    return messages
```

- [ ] **Step 3: Update `_free_chat_reply` to pass dialog_type**

Change the function signature and the `_build_chat_messages` call:

```python
async def _free_chat_reply(
    db: Session,
    dialog: Dialog,
    project: Project,
    diagnosis: ProjectDiagnosisOut,
    dialog_type: str = "hermes",
) -> str:
    if not load_api_key():
        return _chat_unavailable_reply(diagnosis, "当前未配置模型 API Key，聊天还没有真实接入 AI")

    try:
        messages = _build_chat_messages(db, dialog.id, project, diagnosis, dialog_type=dialog_type)
        result = await ai_service.complete(
            messages,
            temperature=0.7,
            max_tokens=900,
            model=project.ai_model or "deepseek-chat",
        )
        content = (result.content or "").strip()
        if content:
            return content
    except Exception as exc:
        return _chat_unavailable_reply(diagnosis, f"模型调用失败：{str(exc)}")

    return _chat_unavailable_reply(diagnosis, "模型返回了空内容")
```

- [ ] **Step 4: Update the main `chat` endpoint to pass dialog_type**

In the `chat` function (around line 454), find the call to `_free_chat_reply` and add `dialog_type="hermes"`:

```python
reply = await _free_chat_reply(db, dialog, project, diagnosis, dialog_type="hermes")
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/dialogs.py
git commit -m "feat: route dialog prompts by dialog_type with world context injection"
```

---

### Task 4: Update Athena Chat Endpoint to Use Enhanced Prompt

**Files:**
- Modify: `backend/app/api/athena.py`

- [ ] **Step 1: Update `athena_chat` to pass dialog_type to `_free_chat_reply`**

Replace the `athena_chat` function in `backend/app/api/athena.py`:

```python
@router.post("/dialog/chat")
async def athena_chat(project_id: str, payload: ChatIn, db: Session = Depends(get_db)):
    from app.api.dialogs import (
        _get_or_create_dialog,
        _build_diagnosis,
        _save_message,
        _build_chat_idle_hint,
        _free_chat_reply,
    )
    project = _require_project(db, project_id)
    payload.project_id = project_id
    dialog = _get_or_create_dialog(db, project_id, dialog_type="athena")
    diagnosis = _build_diagnosis(db, project_id)

    user_text = (payload.text or "").strip()
    if user_text:
        _save_message(db, dialog.id, "user", user_text)

    reply = await _free_chat_reply(db, dialog, project, diagnosis, dialog_type="athena")
    _save_message(db, dialog.id, "assistant", reply)
    return ChatOut(
        message=reply,
        pending_action=None,
        ui_hint=_build_chat_idle_hint("Athena 对话"),
        refresh_targets=[],
        project_diagnosis=diagnosis,
    )
```

The only change is adding `dialog_type="athena"` to the `_free_chat_reply` call.

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/athena.py
git commit -m "feat: Athena chat uses world-aware prompt via dialog_type"
```

---

### Task 5: Frontend Chat Store — Dual Dialog Support

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Add `dialogType` to chat API calls in `frontend/src/api/client.ts`**

Find the `sendChat` method and add `dialogType` parameter. Find the `getMessages` method and add `dialogType` query param:

```typescript
getMessages: (projectId: string, dialogType: string = 'hermes') =>
  request<DialogMessage[]>(`/dialog/projects/${projectId}/messages?dialog_type=${dialogType}`),
```

The `sendChat` method doesn't need changes — it already posts to `/dialog/chat` which defaults to hermes.

- [ ] **Step 2: Add `dialogType` state to chat store**

In `frontend/src/stores/chat.ts`, add:

```typescript
const dialogType = ref<'hermes' | 'athena'>('hermes')

function setDialogType(type: 'hermes' | 'athena') {
  dialogType.value = type
}
```

Update `loadMessages` to pass `dialogType.value`:

```typescript
async function loadMessages(projectId: string) {
  const msgs = await api.getMessages(projectId, dialogType.value)
  messages.value = msgs
}
```

Export `dialogType` and `setDialogType` in the return block.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/chat.ts frontend/src/api/client.ts
git commit -m "feat: frontend chat store supports dual dialog type"
```

---

### Task 6: Verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest -v`
Expected: All PASS

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Test Athena dialog with world context**

```bash
cd backend && .venv/bin/python -c "
from app.main import app
from fastapi.testclient import TestClient
c = TestClient(app)
pid = '5b95b442-724b-4187-9507-283bf709dffa'

# Test Athena dialog messages (should be empty initially)
r = c.get(f'/api/v1/projects/{pid}/athena/dialog/messages')
print(f'athena messages: {r.status_code}, count: {len(r.json())}')

# Test Hermes dialog messages (existing)
r = c.get(f'/api/v1/dialog/projects/{pid}/messages?dialog_type=hermes')
print(f'hermes messages: {r.status_code}, count: {len(r.json())}')

# Verify they are separate
r_athena = c.get(f'/api/v1/projects/{pid}/athena/dialog/messages')
r_hermes = c.get(f'/api/v1/dialog/projects/{pid}/messages')
print(f'separate sessions: {len(r_athena.json()) != len(r_hermes.json()) or len(r_athena.json()) == 0}')
"
```

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: cleanup after Hermes dialog separation"
```