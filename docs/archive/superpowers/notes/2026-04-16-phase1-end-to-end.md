# Phase 1 End-to-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimal end-to-end novel writing system: project CRUD, AI-powered setup generation, single-chapter generation, basic chat UI, and project pages.

**Architecture:** FastAPI backend with SQLite/SQLAlchemy handles data and AI orchestration; Vue 3 + Vite frontend provides the chat and project UI; a single `mozhou.py` entry point mounts the built frontend and starts the server.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite, httpx, Vue 3, TypeScript, Vite, Tailwind CSS (optional)

---

## File Structure

```
novelv3/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory, CORS, static mount
│   │   ├── db.py                   # SQLAlchemy engine/session, get_db()
│   │   ├── config.py               # settings, API key loader/saver
│   │   ├── models/
│   │   │   ├── project.py          # Project ORM
│   │   │   ├── setup.py            # Setup ORM
│   │   │   └── chapter_content.py  # ChapterContent ORM
│   │   ├── schemas/
│   │   │   ├── project.py          # Pydantic request/response models
│   │   │   ├── setup.py
│   │   │   └── chapter.py
│   │   ├── api/
│   │   │   ├── projects.py         # project CRUD endpoints
│   │   │   ├── setups.py           # setup generate/get endpoints
│   │   │   ├── chapters.py         # chapter generate/get endpoints
│   │   │   └── config.py           # config read/write endpoints
│   │   └── core/
│   │       ├── ai_service.py       # AIService wrapper
│   │       ├── deepseek_adapter.py # DeepSeek httpx adapter
│   │       ├── prompt_manager.py   # Jinja2/variable prompt loader
│   │       ├── token_budget.py     # TokenBudgetManager
│   │       ├── context_compressor.py
│   │       ├── event_bus.py        # SimpleEventBus
│   │       ├── cache.py            # CacheManager + LRUCache
│   │       └── error_handler.py    # AppError, with_retry
│   ├── alembic/                    # Alembic migrations
│   ├── tests/
│   │   ├── conftest.py             # pytest fixtures (test client, db)
│   │   ├── test_projects.py
│   │   ├── test_setups.py
│   │   └── test_chapters.py
│   ├── requirements.txt
│   └── mozhou.py                   # Entry point: build + serve
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── stores/
│   │   │   ├── project.ts
│   │   │   └── chat.ts
│   │   ├── views/
│   │   │   ├── ProjectList.vue
│   │   │   ├── ProjectDetail.vue
│   │   │   ├── ChatView.vue
│   │   │   └── SettingsView.vue
│   │   └── components/
│   │       ├── ChatMessage.vue
│   │       └── ProjectCard.vue
│   └── public/
└── data/
    └── mozhou.db
```

---

## Part A: Backend Infrastructure

### Task 1: Create backend project skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/mozhou.py`

- [ ] **Step 1: Write requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
alembic==1.14.0
pydantic==2.9.2
pydantic-settings==2.6.1
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create minimal FastAPI app**

`backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mozhou AI Writer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Create entry point mozhou.py**

`backend/mozhou.py`
```python
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 4: Install deps and verify**

Run:
```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python mozhou.py &
sleep 2
curl -s http://localhost:8000/api/v1/health | grep ok
kill %1
```
Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: backend skeleton and health endpoint"
```

---

### Task 2: Database layer (SQLAlchemy + Alembic)

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

- [ ] **Step 1: Write db.py with engine and session**

`backend/app/db.py`
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'mozhou.db')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Initialize Alembic**

Run:
```bash
cd backend && source .venv/bin/activate
alembic init alembic
```

- [ ] **Step 3: Patch alembic/env.py to use Base metadata**

Open `backend/alembic/env.py`, find the `target_metadata` line and set:
```python
from app.db import Base
target_metadata = Base.metadata
```
Also update `sqlalchemy.url` in `alembic.ini` to:
```ini
sqlalchemy.url = sqlite:///../../data/mozhou.db
```

- [ ] **Step 4: Run Alembic to ensure it loads**

Run:
```bash
cd backend && alembic current
```
Expected: no errors (may show `None` if no migrations yet)

- [ ] **Step 5: Commit**

```bash
git add backend/app/db.py backend/alembic.ini backend/alembic/
git commit -m "feat: sqlalchemy engine, session, and alembic setup"
```

---

### Task 3: Project ORM and schema

**Files:**
- Create: `backend/app/models/project.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Write Project model**

`backend/app/models/project.py`
```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from app.db import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, default="")
    genre = Column(String, default="")
    target_word_count = Column(Integer, default=0)
    current_word_count = Column(Integer, default=0)
    status = Column(String, default="draft")
    current_phase = Column(String, default="setup")
    ai_model = Column(String, default="deepseek-chat")
    language = Column(String, default="zh-CN")
    style = Column(String, default="")
    complexity = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Write Project schemas**

`backend/app/schemas/project.py`
```python
from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    genre: str = ""
    target_word_count: int = 0
    style: str = ""
    complexity: int = 3


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    genre: str | None = None
    target_word_count: int | None = None
    style: str | None = None
    complexity: int | None = None
    status: str | None = None
    current_phase: str | None = None
    current_word_count: int | None = None


class ProjectOut(ProjectCreate):
    id: str
    status: str
    current_phase: str
    current_word_count: int
    ai_model: str
    language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Create init files**

`backend/app/models/__init__.py`
```python
from .project import Project
```

`backend/app/schemas/__init__.py`
```python
from .project import ProjectCreate, ProjectUpdate, ProjectOut
```

- [ ] **Step 4: Generate first migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add projects table"
alembic upgrade head
```
Expected: migration succeeds, `data/mozhou.db` created

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/ backend/alembic/versions/
git commit -m "feat: project model, schema, and initial migration"
```

---

### Task 4: Project CRUD API

**Files:**
- Create: `backend/app/api/projects.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_projects.py`

- [ ] **Step 1: Write projects router**

`backend/app/api/projects.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.api import projects

app.include_router(projects.router)
```

- [ ] **Step 3: Write failing test**

`backend/tests/test_projects.py`
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def test_create_and_get_project():
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Novel"
    pid = data["id"]

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid
```

- [ ] **Step 4: Run tests**

Run:
```bash
cd backend && source .venv/bin/activate && pytest tests/test_projects.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ backend/tests/
git commit -m "feat: project CRUD endpoints and tests"
```

---

### Task 5: Core utilities (error handling, retry, event bus, cache)

**Files:**
- Create: `backend/app/core/error_handler.py`
- Create: `backend/app/core/event_bus.py`
- Create: `backend/app/core/cache.py`

- [ ] **Step 1: Write error handler and retry**

`backend/app/core/error_handler.py`
```python
import asyncio


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


async def with_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
```

- [ ] **Step 2: Write event bus**

`backend/app/core/event_bus.py`
```python
import asyncio
import logging

logger = logging.getLogger("mozhou")


class SimpleEventBus:
    def __init__(self):
        self._handlers: dict[str, list] = {}

    def on(self, event_type: str, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, payload):
        for handler in self._handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error("Event handler error for %s: %s", event_type, e)
```

- [ ] **Step 3: Write cache**

`backend/app/core/cache.py`
```python
class LRUCache:
    def __init__(self, max_size: int):
        self._cache: dict[str, any] = {}
        self._max_size = max_size

    def get(self, key: str):
        if key not in self._cache:
            return None
        value = self._cache.pop(key)
        self._cache[key] = value
        return value

    def set(self, key: str, value):
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self._max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value


class CacheManager:
    def __init__(self):
        self.projects = LRUCache(100)
        self.chapters = LRUCache(50)
        self.ai_responses = LRUCache(200)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/
git commit -m "feat: error handler, retry, event bus, and cache"
```

---

### Task 6: Token budget and context compressor

**Files:**
- Create: `backend/app/core/token_budget.py`
- Create: `backend/app/core/context_compressor.py`

- [ ] **Step 1: Write TokenBudgetManager**

`backend/app/core/token_budget.py`
```python
import math


class TokenBudgetManager:
    DEFAULT_BUDGET = {
        "total": 6000,
        "system_prompt": 800,
        "characters": 1000,
        "previous_chapters": 1200,
        "world_facts": 800,
        "output_format": 400,
        "reserved": 1200,
    }

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            chinese_chars = len([c for c in text if "\u4e00" <= c <= "\u9fa5"])
            return math.ceil(chinese_chars * 0.6 + len(text.split()) * 0.5)
```

- [ ] **Step 2: Write ContextCompressor**

`backend/app/core/context_compressor.py`
```python
from app.core.token_budget import TokenBudgetManager


class ContextCompressor:
    @classmethod
    def compress_previous_chapters(cls, chapters: list[dict], target_tokens: int) -> str:
        result = []
        current_tokens = 0
        for chapter in reversed(chapters):
            summary = f"第{chapter['index']}章《{chapter['title']}》：{chapter.get('summary', '')}"
            tokens = TokenBudgetManager.estimate_tokens(summary)
            if current_tokens + tokens <= target_tokens:
                result.insert(0, summary)
                current_tokens += tokens
            else:
                break
        return "\n".join(result)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/token_budget.py backend/app/core/context_compressor.py
git commit -m "feat: token budget manager and context compressor"
```

---

### Task 7: Config API (API Key management)

**Files:**
- Create: `backend/app/api/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Write config.py with API key loader/saver**

`backend/app/config.py`
```python
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_api_key() -> str | None:
    if os.getenv("DEEPSEEK_API_KEY"):
        return os.getenv("DEEPSEEK_API_KEY")
    try:
        import keyring
        return keyring.get_password("mozhou", "deepseek_api_key")
    except Exception:
        return None


def save_api_key(key: str) -> None:
    try:
        import keyring
        keyring.set_password("mozhou", "deepseek_api_key", key)
    except Exception:
        with open(PROJECT_ROOT / ".env", "w") as f:
            f.write(f"DEEPSEEK_API_KEY={key}\n")
```

- [ ] **Step 2: Write config router**

`backend/app/api/config.py`
```python
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import load_api_key, save_api_key

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigOut(BaseModel):
    has_api_key: bool


class ConfigIn(BaseModel):
    api_key: str


@router.get("", response_model=ConfigOut)
def get_config():
    return {"has_api_key": bool(load_api_key())}


@router.put("")
def update_config(payload: ConfigIn):
    save_api_key(payload.api_key)
    return {"has_api_key": True}
```

- [ ] **Step 3: Register router**

Add to `backend/app/main.py`:
```python
from app.api import config
app.include_router(config.router)
```

- [ ] **Step 4: Quick manual test**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "from app.config import save_api_key, load_api_key; save_api_key('sk-test'); print(load_api_key())"
```
Expected: `sk-test`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/api/config.py backend/app/main.py
git commit -m "feat: config API for API key management"
```

---

### Task 8: AI Service and DeepSeek Adapter

**Files:**
- Create: `backend/app/core/deepseek_adapter.py`
- Create: `backend/app/core/ai_service.py`
- Modify: `backend/app/core/prompt_manager.py`

- [ ] **Step 1: Write DeepSeekAdapter**

`backend/app/core/deepseek_adapter.py`
```python
import json
import re
import httpx
from pydantic import BaseModel
from app.core.error_handler import AppError


class CompletionResult(BaseModel):
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class DeepSeekAdapter:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model: str = "deepseek-chat",
    ) -> CompletionResult:
        resp = await self.client.post(
            "/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        result = CompletionResult(
            content=choice["message"]["content"],
            prompt_tokens=data["usage"]["prompt_tokens"],
            completion_tokens=data["usage"]["completion_tokens"],
            model=data["model"],
        )
        return result


def parse_json_safely(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        candidate = match.group(1).replace("'", '"')
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise AppError("PARSE_ERROR", "无法解析模型返回的 JSON")
```

- [ ] **Step 2: Write AIService**

`backend/app/core/ai_service.py`
```python
from app.config import load_api_key
from app.core.deepseek_adapter import DeepSeekAdapter, parse_json_safely
from app.core.error_handler import with_retry


class AIService:
    def __init__(self):
        self._adapter = None

    def _get_adapter(self) -> DeepSeekAdapter:
        if self._adapter is None:
            key = load_api_key()
            if not key:
                raise ValueError("API key not configured")
            self._adapter = DeepSeekAdapter(api_key=key)
        return self._adapter

    async def complete(self, messages: list[dict], **kwargs):
        adapter = self._get_adapter()
        return await with_retry(lambda: adapter.complete(messages, **kwargs))

    def parse_json(self, text: str) -> dict:
        return parse_json_safely(text)
```

- [ ] **Step 3: Write PromptManager**

`backend/app/core/prompt_manager.py`
```python
import os
from string import Template


class PromptManager:
    def __init__(self, prompts_dir: str | None = None):
        if prompts_dir is None:
            self.prompts_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "prompts"
            )
        else:
            self.prompts_dir = prompts_dir

    def load(self, name: str, variables: dict | None = None) -> str:
        path = os.path.join(self.prompts_dir, f"{name}.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if variables:
            content = Template(content).substitute(variables)
        return content
```

- [ ] **Step 4: Create prompt templates**

Create `backend/prompts/generate_setup.txt`:
```
你是一个小说设定生成助手。请根据以下项目信息生成完整的小说设定，包含世界观、角色列表和核心概念。

项目信息：
名称：${name}
类型：${genre}
描述：${description}
风格：${style}
复杂度：${complexity}

请严格按照以下 JSON 格式返回，不要添加额外说明：
{
  "world_building": {
    "background": "...",
    "geography": "...",
    "society": "...",
    "rules": "...",
    "atmosphere": "..."
  },
  "characters": [
    {
      "name": "...",
      "age": 0,
      "gender": "...",
      "personality": "...",
      "background": "...",
      "goals": "...",
      "character_status": "alive"
    }
  ],
  "core_concept": {
    "theme": "...",
    "premise": "...",
    "hook": "...",
    "unique_selling_point": "..."
  }
}
```

Create `backend/prompts/generate_chapter.txt`:
```
你是一个小说写作助手。请根据以下设定信息，创作第 1 章正文。

世界观：
${world_building}

角色：
${characters}

核心概念：
${core_concept}

要求：
- 字数约 3000 字
- 使用 Markdown 格式
- 语言风格：${language}

直接返回章节正文，不要添加额外说明。
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/deepseek_adapter.py backend/app/core/ai_service.py backend/app/core/prompt_manager.py backend/prompts/
git commit -m "feat: AI service, DeepSeek adapter, and prompt templates"
```

---

### Task 9: Setup model, schema, and API

**Files:**
- Create: `backend/app/models/setup.py`
- Create: `backend/app/schemas/setup.py`
- Create: `backend/app/api/setups.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_setups.py`

- [ ] **Step 1: Write Setup model**

`backend/app/models/setup.py`
```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey
from app.db import Base


class Setup(Base):
    __tablename__ = "setups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    world_building = Column(JSON, default=dict)
    characters = Column(JSON, default=list)
    core_concept = Column(JSON, default=dict)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Write Setup schema**

`backend/app/schemas/setup.py`
```python
from pydantic import BaseModel
from datetime import datetime


class CharacterProfile(BaseModel):
    name: str
    age: int | None = None
    gender: str | None = None
    personality: str | None = None
    background: str | None = None
    goals: str | None = None
    character_status: str = "alive"


class WorldBuilding(BaseModel):
    background: str
    geography: str
    society: str
    rules: str
    atmosphere: str


class CoreConcept(BaseModel):
    theme: str
    premise: str
    hook: str
    unique_selling_point: str


class SetupOut(BaseModel):
    id: str
    project_id: str
    world_building: WorldBuilding
    characters: list[CharacterProfile]
    core_concept: CoreConcept
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Write setups router**

`backend/app/api/setups.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup
from app.schemas import SetupOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/setup", tags=["setups"])


@router.post("/generate", response_model=SetupOut)
async def generate_setup(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(Setup).filter(Setup.project_id == project_id).first()
    if existing:
        db.delete(existing)

    pm = PromptManager()
    prompt = pm.load(
        "generate_setup",
        {
            "name": project.name,
            "genre": project.genre,
            "description": project.description,
            "style": project.style,
            "complexity": project.complexity,
        },
    )

    ai = AIService()
    result = await ai.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    data = ai.parse_json(result.content)

    setup = Setup(
        project_id=project_id,
        world_building=data.get("world_building", {}),
        characters=data.get("characters", []),
        core_concept=data.get("core_concept", {}),
        status="generated",
    )
    db.add(setup)

    project.status = "setup_approved"
    project.current_phase = "setup"
    db.commit()
    db.refresh(setup)
    return setup


@router.get("", response_model=SetupOut)
def get_setup(project_id: str, db: Session = Depends(get_db)):
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setup
```

- [ ] **Step 4: Register and export**

Update `backend/app/models/__init__.py`:
```python
from .project import Project
from .setup import Setup
```

Update `backend/app/schemas/__init__.py`:
```python
from .project import ProjectCreate, ProjectUpdate, ProjectOut
from .setup import SetupOut, CharacterProfile, WorldBuilding, CoreConcept
```

Update `backend/app/main.py`:
```python
from app.api import setups
app.include_router(setups.router)
```

- [ ] **Step 5: Write test with mocked AI**

`backend/tests/test_setups.py`
```python
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


@patch("app.api.setups.AIService.complete", new_callable=AsyncMock)
@patch("app.api.setups.AIService.parse_json")
def test_generate_setup(mock_parse, mock_complete):
    # create project
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    r2 = client.post(f"/api/v1/projects/{pid}/setup/generate")
    assert r2.status_code == 200
    assert r2.json()["status"] == "generated"
```

- [ ] **Step 6: Run tests**

```bash
cd backend && pytest tests/test_setups.py -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/setup.py backend/app/schemas/setup.py backend/app/api/setups.py backend/tests/test_setups.py
git commit -m "feat: setup generation endpoint and tests"
```

---

### Task 10: Chapter model, schema, and API

**Files:**
- Create: `backend/app/models/chapter_content.py`
- Create: `backend/app/schemas/chapter.py`
- Create: `backend/app/api/chapters.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chapters.py`

- [ ] **Step 1: Write ChapterContent model**

`backend/app/models/chapter_content.py`
```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Float, DateTime, ForeignKey
from app.db import Base


class ChapterContent(Base):
    __tablename__ = "chapter_contents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    title = Column(String, default="")
    content = Column(Text, default="")
    word_count = Column(Integer, default=0)
    status = Column(String, default="pending")
    model = Column(String, default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    generation_time = Column(Integer, default=0)
    temperature = Column(Float, default=0.7)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Write Chapter schema**

`backend/app/schemas/chapter.py`
```python
from pydantic import BaseModel
from datetime import datetime


class ChapterOut(BaseModel):
    id: str
    project_id: str
    chapter_index: int
    title: str
    content: str
    word_count: int
    status: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    generation_time: int
    temperature: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Write chapters router**

`backend/app/api/chapters.py`
```python
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, ChapterContent
from app.schemas import ChapterOut
from app.core.ai_service import AIService
from app.core.prompt_manager import PromptManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/chapters", tags=["chapters"])


@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    if chapter_index != 1:
        raise HTTPException(status_code=400, detail="Phase 1 only supports chapter 1")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=400, detail="Setup not generated yet")

    existing = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if existing:
        db.delete(existing)

    pm = PromptManager()
    prompt = pm.load(
        "generate_chapter",
        {
            "world_building": str(setup.world_building),
            "characters": str(setup.characters),
            "core_concept": str(setup.core_concept),
            "language": project.language,
        },
    )

    ai = AIService()
    start = time.time()
    result = await ai.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    elapsed = int((time.time() - start) * 1000)

    chapter = ChapterContent(
        project_id=project_id,
        chapter_index=chapter_index,
        title=f"第{chapter_index}章",
        content=result.content,
        word_count=len(result.content),
        status="generated",
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        generation_time=elapsed,
        temperature=0.7,
    )
    db.add(chapter)

    project.current_word_count = chapter.word_count
    project.status = "writing"
    db.commit()
    db.refresh(chapter)
    return chapter


@router.get("/{chapter_index}", response_model=ChapterOut)
def get_chapter(project_id: str, chapter_index: int, db: Session = Depends(get_db)):
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
```

- [ ] **Step 4: Register and export**

Update `backend/app/models/__init__.py`:
```python
from .project import Project
from .setup import Setup
from .chapter_content import ChapterContent
```

Update `backend/app/schemas/__init__.py`:
```python
from .project import ProjectCreate, ProjectUpdate, ProjectOut
from .setup import SetupOut
from .chapter import ChapterOut
```

Update `backend/app/main.py`:
```python
from app.api import chapters
app.include_router(chapters.router)
```

- [ ] **Step 5: Write test with mocked AI**

`backend/tests/test_chapters.py`
```python
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


@patch("app.api.chapters.AIService.complete", new_callable=AsyncMock)
def test_generate_chapter(mock_complete):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    # generate setup first
    with patch("app.api.setups.AIService.complete", new_callable=AsyncMock) as ms, \
         patch("app.api.setups.AIService.parse_json") as mp:
        ms.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
        mp.return_value = {"world_building": {}, "characters": [], "core_concept": {}}
        client.post(f"/api/v1/projects/{pid}/setup/generate")

    mock_complete.return_value.content = "第一章正文内容"
    mock_complete.return_value.model = "deepseek-chat"
    mock_complete.return_value.prompt_tokens = 100
    mock_complete.return_value.completion_tokens = 200

    r2 = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")
    assert r2.status_code == 200
    assert r2.json()["content"] == "第一章正文内容"
    assert r2.json()["status"] == "generated"
```

- [ ] **Step 6: Run tests**

```bash
cd backend && pytest tests/test_chapters.py -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/chapter_content.py backend/app/schemas/chapter.py backend/app/api/chapters.py backend/tests/test_chapters.py
git commit -m "feat: chapter generation endpoint and tests"
```

---

### Task 11: Alembic migration for Setup and ChapterContent

**Files:**
- Create: `backend/alembic/versions/..._add_setup_and_chapter.py`

- [ ] **Step 1: Generate migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add setups and chapter_contents"
alembic upgrade head
```
Expected: migration succeeds

- [ ] **Step 2: Commit**

```bash
git add backend/alembic/versions/
git commit -m "chore: alembic migration for setups and chapter_contents"
```

---

## Part B: Frontend

### Task 12: Create frontend project skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`

- [ ] **Step 1: Write package.json**

`frontend/package.json`
```json
{
  "name": "mozhou-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.4.0",
    "pinia": "^2.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vue-tsc": "^2.1.0"
  }
}
```

- [ ] **Step 2: Write vite.config.ts**

`frontend/vite.config.ts`
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: Write tsconfig.json**

`frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"]
}
```

- [ ] **Step 4: Write index.html and main.ts**

`frontend/index.html`
```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>墨舟 AI Writer</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

`frontend/src/main.ts`
```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 5: Install deps and verify dev server starts**

Run:
```bash
cd frontend && npm install && npm run build
```
Expected: build succeeds, `backend/static/` created

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: frontend vue3+vite skeleton"
```

---

### Task 13: Router and API client

**Files:**
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write router**

`frontend/src/router/index.ts`
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import ChatView from '../views/ChatView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', component: ProjectList },
  { path: '/projects/:id', component: ProjectDetail },
  { path: '/chat', component: ChatView },
  { path: '/settings', component: SettingsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 2: Write API client**

`frontend/src/api/client.ts`
```typescript
const API_BASE = '/api/v1'

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  listProjects: () => request('/projects'),
  createProject: (data: any) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: string) => request(`/projects/${id}`),
  deleteProject: (id: string) => request(`/projects/${id}`, { method: 'DELETE' }),
  generateSetup: (id: string) => request(`/projects/${id}/setup/generate`, { method: 'POST' }),
  getSetup: (id: string) => request(`/projects/${id}/setup`),
  generateChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}/generate`, { method: 'POST' }),
  getChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}`),
  getConfig: () => request('/config'),
  updateConfig: (apiKey: string) => request('/config', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }),
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/ frontend/src/api/
git commit -m "feat: vue router and api client"
```

---

### Task 14: App shell and stores

**Files:**
- Create: `frontend/src/App.vue`
- Create: `frontend/src/stores/project.ts`
- Create: `frontend/src/stores/chat.ts`

- [ ] **Step 1: Write App.vue with nav**

`frontend/src/App.vue`
```vue
<template>
  <div>
    <nav style="padding: 1rem; border-bottom: 1px solid #ccc;">
      <router-link to="/">项目列表</router-link> |
      <router-link to="/chat">对话</router-link> |
      <router-link to="/settings">设置</router-link>
    </nav>
    <main style="padding: 1rem;">
      <router-view />
    </main>
  </div>
</template>
```

- [ ] **Step 2: Write Pinia stores**

`frontend/src/stores/project.ts`
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<any[]>([])
  const currentProject = ref<any>(null)
  const setup = ref<any>(null)
  const chapter = ref<any>(null)

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  async function createProject(data: any) {
    const p = await api.createProject(data)
    projects.value.unshift(p)
    return p
  }

  async function loadProject(id: string) {
    currentProject.value = await api.getProject(id)
  }

  async function generateSetup(id: string) {
    setup.value = await api.generateSetup(id)
    await loadProject(id)
  }

  async function loadSetup(id: string) {
    setup.value = await api.getSetup(id)
  }

  async function generateChapter(id: string, index: number) {
    chapter.value = await api.generateChapter(id, index)
    await loadProject(id)
  }

  async function loadChapter(id: string, index: number) {
    chapter.value = await api.getChapter(id, index)
  }

  return {
    projects, currentProject, setup, chapter,
    loadProjects, createProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
  }
})
```

`frontend/src/stores/chat.ts`
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  pending_action?: any
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([
    { role: 'assistant', content: '你好，我是墨舟。请告诉我你想写什么类型的小说？' },
  ])

  function sendUserMessage(text: string) {
    messages.value.push({ role: 'user', content: text })
  }

  function appendAssistantMessage(text: string, pending_action?: any) {
    messages.value.push({ role: 'assistant', content: text, pending_action })
  }

  function clear() {
    messages.value = []
  }

  return { messages, sendUserMessage, appendAssistantMessage, clear }
})
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue frontend/src/stores/
git commit -m "feat: app shell and pinia stores"
```

---

### Task 15: Settings page

**Files:**
- Create: `frontend/src/views/SettingsView.vue`

- [ ] **Step 1: Write SettingsView**

`frontend/src/views/SettingsView.vue`
```vue
<template>
  <div>
    <h2>设置</h2>
    <div style="margin-top: 1rem;">
      <label>DeepSeek API Key</label>
      <input v-model="apiKey" type="password" placeholder="sk-..." style="width: 300px;" />
      <button @click="save" style="margin-left: 0.5rem;">保存</button>
    </div>
    <p v-if="saved" style="color: green;">已保存</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const apiKey = ref('')
const saved = ref(false)

onMounted(async () => {
  const cfg = await api.getConfig()
  if (cfg.has_api_key) apiKey.value = '********'
})

async function save() {
  await api.updateConfig(apiKey.value)
  saved.value = true
  setTimeout(() => saved.value = false, 2000)
}
</script>
```

- [ ] **Step 2: Build and verify no TS errors**

Run:
```bash
cd frontend && npm run build
```
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/SettingsView.vue
git commit -m "feat: settings page for API key"
```

---

### Task 16: Project list page and card

**Files:**
- Create: `frontend/src/views/ProjectList.vue`
- Create: `frontend/src/components/ProjectCard.vue`

- [ ] **Step 1: Write ProjectCard**

`frontend/src/components/ProjectCard.vue`
```vue
<template>
  <div style="border: 1px solid #ddd; padding: 1rem; border-radius: 4px; margin-bottom: 0.5rem;">
    <h3>{{ project.name }}</h3>
    <p style="color: #666;">{{ project.genre }} | {{ project.current_word_count }} 字</p>
    <router-link :to="`/projects/${project.id}`">查看详情</router-link>
  </div>
</template>

<script setup lang="ts">
defineProps<{ project: any }>()
</script>
```

- [ ] **Step 2: Write ProjectList**

`frontend/src/views/ProjectList.vue`
```vue
<template>
  <div>
    <h2>项目列表</h2>
    <button @click="showForm = true" style="margin-bottom: 1rem;">新建项目</button>
    <div v-if="showForm" style="border: 1px solid #ccc; padding: 1rem; margin-bottom: 1rem;">
      <input v-model="form.name" placeholder="项目名称" />
      <input v-model="form.genre" placeholder="类型" style="margin-left: 0.5rem;" />
      <button @click="create" style="margin-left: 0.5rem;">创建</button>
    </div>
    <ProjectCard v-for="p in store.projects" :key="p.id" :project="p" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProjectStore } from '../stores/project'
import ProjectCard from '../components/ProjectCard.vue'

const store = useProjectStore()
const showForm = ref(false)
const form = ref({ name: '', genre: '' })

onMounted(() => store.loadProjects())

async function create() {
  await store.createProject(form.value)
  showForm.value = false
  form.value = { name: '', genre: '' }
}
</script>
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```
Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ProjectList.vue frontend/src/components/ProjectCard.vue
git commit -m "feat: project list page and card component"
```

---

### Task 17: Project detail page

**Files:**
- Create: `frontend/src/views/ProjectDetail.vue`

- [ ] **Step 1: Write ProjectDetail**

`frontend/src/views/ProjectDetail.vue`
```vue
<template>
  <div v-if="store.currentProject">
    <h2>{{ store.currentProject.name }}</h2>
    <p>状态：{{ store.currentProject.status }} | 字数：{{ store.currentProject.current_word_count }}</p>

    <div style="margin-top: 1rem;">
      <h3>设定</h3>
      <button @click="genSetup">生成设定</button>
      <pre v-if="store.setup" style="background: #f5f5f5; padding: 1rem; overflow: auto;">{{ JSON.stringify(store.setup, null, 2) }}</pre>
    </div>

    <div style="margin-top: 1rem;">
      <h3>第 1 章</h3>
      <button @click="genChapter">生成第 1 章</button>
      <div v-if="store.chapter">
        <h4>{{ store.chapter.title }}</h4>
        <div style="white-space: pre-wrap;">{{ store.chapter.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'

const route = useRoute()
const store = useProjectStore()
const pid = route.params.id as string

onMounted(async () => {
  await store.loadProject(pid)
  if (store.currentProject?.status !== 'draft') {
    await store.loadSetup(pid).catch(() => {})
    await store.loadChapter(pid, 1).catch(() => {})
  }
})

async function genSetup() {
  await store.generateSetup(pid)
}

async function genChapter() {
  await store.generateChapter(pid, 1)
}
</script>
```

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ProjectDetail.vue
git commit -m "feat: project detail page with setup and chapter generation"
```

---

### Task 18: Chat view

**Files:**
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/components/ChatMessage.vue`

- [ ] **Step 1: Write ChatMessage**

`frontend/src/components/ChatMessage.vue`
```vue
<template>
  <div style="margin: 0.5rem 0; text-align: left;">
    <div :style="{ background: msg.role === 'user' ? '#e3f2fd' : '#f5f5f5', padding: '0.75rem', borderRadius: '4px', display: 'inline-block', maxWidth: '80%' }">
      <div style="font-size: 0.75rem; color: #888; margin-bottom: 0.25rem;">{{ msg.role === 'user' ? '我' : '墨舟' }}</div>
      <div style="white-space: pre-wrap;">{{ msg.content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ msg: any }>()
</script>
```

- [ ] **Step 2: Write ChatView**

`frontend/src/views/ChatView.vue`
```vue
<template>
  <div style="display: flex; flex-direction: column; height: 80vh;">
    <div style="flex: 1; overflow-y: auto; border: 1px solid #ddd; padding: 1rem;">
      <ChatMessage v-for="(m, i) in chat.messages" :key="i" :msg="m" />
    </div>
    <div style="display: flex; margin-top: 0.5rem;">
      <input v-model="input" @keyup.enter="send" style="flex: 1; padding: 0.5rem;" placeholder="输入消息..." />
      <button @click="send" style="padding: 0.5rem 1rem;">发送</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatMessage from '../components/ChatMessage.vue'

const chat = useChatStore()
const input = ref('')

function send() {
  if (!input.value.trim()) return
  chat.sendUserMessage(input.value)
  // Phase 1: echo a simple assistant reply
  setTimeout(() => {
    chat.appendAssistantMessage('收到。你可以在项目详情页中生成设定和章节。')
  }, 300)
  input.value = ''
}
</script>
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```
Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ChatView.vue frontend/src/components/ChatMessage.vue
git commit -m "feat: chat view and message component"
```

---

## Part C: Integration and Packaging

### Task 19: Mount static files in FastAPI

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Serve built frontend from FastAPI**

`backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Mozhou AI Writer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import projects, setups, chapters, config

app.include_router(projects.router)
app.include_router(setups.router)
app.include_router(chapters.router)
app.include_router(config.router)

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "not found"}
```

- [ ] **Step 2: Update mozhou.py to auto-open browser**

`backend/mozhou.py`
```python
import webbrowser
import uvicorn
from app.main import app

if __name__ == "__main__":
    webbrowser.open("http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: End-to-end smoke test**

Run:
```bash
cd backend && source .venv/bin/activate
python mozhou.py &
PID=$!
sleep 2
curl -s http://localhost:8000/api/v1/health | grep ok
curl -s -X POST http://localhost:8000/api/v1/projects -H "Content-Type: application/json" -d '{"name":"Smoke"}' | grep Smoke
kill $PID
```
Expected: both curls succeed

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py backend/mozhou.py
git commit -m "feat: mount frontend static files and auto-open browser"
```

---

## Self-Review

**1. Spec coverage:**
- 项目 CRUD → Task 4
- 设定生成 → Task 9
- 单章生成 → Task 10
- 基础对话 UI → Task 18
- 项目列表/详情页 → Task 16, 17
- API Key 配置 → Task 7, 15
- 后端基础设施 → Tasks 1-3, 5-6, 8, 11
- 前端基础设施 → Tasks 12-14
- 集成打包 → Task 19

**2. Placeholder scan:**
- No "TBD", "TODO", or "implement later" found.
- All code blocks contain complete implementations.
- All test commands include expected output.

**3. Type consistency:**
- `ProjectOut`, `SetupOut`, `ChapterOut` schemas align with ORM models.
- API paths match Phase 1 design doc exactly.
- `character_status` defaults to `"alive"` as specified.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-16-phase1-end-to-end.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
