# Phase 1 设计文档：核心数据流 + 单章写作

> **版本**: v3.0 Phase 1  
> **日期**: 2026-04-15  
> **目标**: 建立端到端的最小可用写作流程

---

## 1. 功能边界

Phase 1 聚焦"创建项目 → 生成设定 → 生成单章正文"的完整闭环。

### 1.1 包含功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 项目 CRUD | 创建、列表、详情、删除项目 | P0 |
| 设定生成 | 基于项目信息调用 DeepSeek API 生成世界观、角色、核心概念 | P0 |
| 单章生成 | 基于设定生成第 1 章正文（支持重试） | P0 |
| 基础对话 UI | 聊天输入、消息渲染、快速开始选项 | P1 |
| 项目列表/详情页 | 展示项目进度、设定内容、已生成章节 | P1 |
| API Key 配置 | 前端提供页面配置 DeepSeek API Key | P1 |

### 1.2 不包含功能（推迟到后续阶段）

- 大纲生成与管理
- 拓扑图
- 一致性检查引擎
- 审批流程
- 版本管理
- 批量生成
- 反馈收集

---

## 2. 技术栈（已锁定）

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + TypeScript + Vite | 响应式成熟，组件化清晰 |
| 后端框架 | FastAPI (Python) | 异步支持好，AI 生态适配 |
| 数据存储 | SQLite + SQLAlchemy 2.0 + Alembic | 零配置本地文件，Alembic 管理 schema 变更 |
| AI 服务 | 自封装 `AIService` | `httpx` 直调 DeepSeek API（OpenAI-compatible 格式） |
| 部署形态 | FastAPI 挂载 Vue 静态资源 | 单进程启动，个人本地使用最友好 |

### 2.1 运行方式

**开发模式：**
```bash
# 后端
uvicorn main:app --reload --port 8000

# 前端
npm run dev
```
前端通过 Vite proxy 将 `/api` 转发到 `http://localhost:8000`。

**使用模式：**
```bash
python mozhou.py
```
FastAPI 服务启动并挂载前端打包后的静态文件，自动打开浏览器。

---

## 3. 数据模型

Phase 1 只建立三张核心表，其余表推迟到 Phase 2。

### 3.1 projects

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| name | String | 项目名称 |
| description | String | 项目描述 |
| genre | String | 类型 |
| target_word_count | Integer | 目标字数 |
| current_word_count | Integer | 当前字数（默认 0） |
| status | String | `draft` / `setup_pending` / `setup_approved` / `writing` / `completed` |
| current_phase | String | `setup` / `storyline` / `outline` / `content` / `revision` |
| ai_model | String | 默认使用模型 |
| language | String | 语言（默认 `zh-CN`） |
| style | String | 写作风格 |
| complexity | Integer | 复杂度 1-5 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.2 setups

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| world_building | JSON | 世界观（background, geography, society, rules, atmosphere） |
| characters | JSON | 角色列表 `CharacterProfile[]`（含 name, age, gender, personality, background, goals, character_status 等） |
| core_concept | JSON | 核心概念（theme, premise, hook, unique_selling_point） |
| status | String | `pending` / `generating` / `generated` / `approved` / `rejected` |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.3 chapter_contents

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(PK) | UUID |
| project_id | String(FK) | 关联项目 |
| chapter_index | Integer | 章节序号（Phase 1 只支持 1） |
| title | String | 章节标题 |
| content | Text | 正文（Markdown） |
| word_count | Integer | 字数 |
| status | String | `pending` / `generating` / `generated` / `approved` / `rejected` |
| model | String | 生成使用的模型 |
| prompt_tokens | Integer | prompt token 数 |
| completion_tokens | Integer | completion token 数 |
| generation_time | Integer | 生成耗时（ms） |
| temperature | Float | 温度参数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

> **关于 `language` 字段**：仅标记输出语言风格（默认 `zh-CN`），系统不提供翻译功能。

---

## 4. 基础设施与中间件

### 4.1 事件总线（Event Bus）

Phase 1 只需最简的事件传递，用一个内部列表或 `asyncio.Queue` 即可，无需通用订阅-发布机制。

```python
class SimpleEventBus:
    def __init__(self):
        self._handlers: dict[str, list[callable]] = {}

    def on(self, event_type: str, handler: callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, payload: any) -> None:
        for handler in self._handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")
```

### 4.2 Token 预算管理（简化版）

优先使用 `tiktoken` 或模型对应的 tokenizer；若未安装则回退到字符估算。

```python
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

    def estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fa5'])
            return math.ceil(chinese_chars * 0.6 + len(text.split()) * 0.5)
```

### 4.3 上下文压缩器（简化版）

```python
class ContextCompressor:
    def compress_previous_chapters(self, chapters: list, target_tokens: int) -> str:
        result = []
        current_tokens = 0
        for chapter in reversed(chapters):
            summary = f"第{chapter['index']}章《{chapter['title']}》：{chapter['summary']}"
            tokens = TokenBudgetManager().estimate_tokens(summary)
            if current_tokens + tokens <= target_tokens:
                result.insert(0, summary)
                current_tokens += tokens
            else:
                break
        return "\n".join(result)
```

### 4.4 错误处理与重试

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.status_code = status_code
        super().__init__(message)

async def with_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as e:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
```

### 4.5 缓存策略（内存 LRU）

```python
class LRUCache:
    def __init__(self, max_size: int):
        self._cache: dict[str, any] = {}
        self._max_size = max_size

    def get(self, key: str) -> any:
        if key not in self._cache:
            return None
        value = self._cache.pop(key)
        self._cache[key] = value
        return value

    def set(self, key: str, value: any) -> None:
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

### 4.6 结构化日志

```python
import logging

logger = logging.getLogger("mozhou")
logger.setLevel(logging.INFO)

class StructuredLogger:
    @staticmethod
    def info(message: str, **ctx):
        logger.info(json.dumps({"msg": message, **ctx}, ensure_ascii=False))

    @staticmethod
    def error(message: str, **ctx):
        logger.error(json.dumps({"msg": message, **ctx}, ensure_ascii=False))
```

---

## 5. 核心 API 列表

### 4.1 项目 API

```
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
```

### 4.2 设定 API

```
POST /api/v1/projects/{project_id}/setup/generate
GET  /api/v1/projects/{project_id}/setup
```

### 4.3 章节 API

```
POST /api/v1/projects/{project_id}/chapters/{chapter_index}/generate
GET  /api/v1/projects/{project_id}/chapters/{chapter_index}
```

### 4.4 配置 API

```
GET    /api/v1/config
PUT    /api/v1/config
```

用于读取/保存 API Key 等本地配置。

**API Key 存储安全**：
1. **第一优先级**：读取 `DEEPSEEK_API_KEY` 环境变量
2. **第二优先级**：尝试 `keyring` 模块读取系统密钥库
3. **保存时**：如果 `keyring` 可用则写入 keyring，否则回退到项目目录下的 `.env` 文件
4. **绝不写入 SQLite**

```python
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

---

## 6. AI 服务设计

### 5.1 AIService 职责

- 统一封装 DeepSeek / OpenAI / Anthropic 的 API 调用
- Phase 1 优先实现 DeepSeek 适配器
- 处理重试、超时、错误码映射、token 估算

### 5.2 DeepSeek 适配器

```python
class DeepSeekAdapter:
    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> CompletionResult:
        ...
```

使用 `httpx.AsyncClient` 发送请求，格式兼容 OpenAI Chat Completions API。

**JSON 解析降级策略**：模型可能将 JSON 包裹在 markdown 代码块中，解析失败时需做正则提取和二次清洗：

```python
def parse_json_safely(text: str) -> dict:
    text = text.strip()
    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 寻找第一个 { 或 [ 到最后一个 } 或 ]
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        candidate = match.group(1)
        # 修复常见格式错误
        candidate = candidate.replace("'", '"')
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 4. 保存原始响应供排查
    logger.error("json_parse_failed", raw_preview=text[:500])
    raise AppError("PARSE_ERROR", "无法解析模型返回的 JSON")
```

### 5.3 PromptManager

Phase 1 内置两个核心模板：
- `generate_setup`：根据项目信息生成设定
- `generate_chapter`：根据设定生成第 1 章正文

模板支持变量替换（`{{variable}}` 语法），暂不支持用户偏好动态注入（Phase 4 引入）。

---

## 7. 工作流简化版

```
用户输入（如"帮我写一本修仙小说"）
    ↓
[隐式创建项目 or 选择已有项目]
    ↓
调用 POST /setup/generate
    ↓
展示生成的设定
    ↓
用户确认/要求修改
    ↓
调用 POST /chapters/1/generate
    ↓
展示第 1 章正文
```

Phase 1 暂不做审批节点，只做展示和重试。用户在对话中可以直接说"重新生成"来触发重试。

---

## 8. 前端页面结构

| 页面/组件 | 说明 |
|-----------|------|
| `/` | 项目列表页 |
| `/projects/:id` | 项目详情页（包含设定、章节标签页） |
| `/chat` | 对话界面（全局入口，可切换上下文到当前项目） |
| `/settings` | 设置页（配置 API Key） |
| `ChatMessage` | 消息气泡组件 |
| `ProjectCard` | 项目卡片组件 |

---

## 9. 目录结构

```
novelv3/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── projects.py
│   │   │   ├── setups.py
│   │   │   ├── chapters.py
│   │   │   └── config.py
│   │   ├── core/
│   │   │   ├── ai_service.py
│   │   │   ├── deepseek_adapter.py
│   │   │   ├── prompt_manager.py
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── project.py
│   │   │   ├── setup.py
│   │   │   └── chapter_content.py
│   │   ├── schemas/
│   │   │   ├── project.py
│   │   │   ├── setup.py
│   │   │   └── chapter.py
│   │   └── db.py
│   ├── alembic/
│   ├── main.py
│   └── mozhou.py           # 单进程启动入口
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── ProjectList.vue
│   │   │   ├── ProjectDetail.vue
│   │   │   ├── ChatView.vue
│   │   │   └── SettingsView.vue
│   │   ├── components/
│   │   │   ├── ChatMessage.vue
│   │   │   └── ProjectCard.vue
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── stores/
│   │   │   ├── project.ts
│   │   │   └── chat.ts
│   │   └── main.ts
│   ├── index.html
│   └── vite.config.ts
├── data/
│   └── mozhou.db           # SQLite 数据库文件
└── docs/
    └── phases/
        └── phase1-design.md
```

---

## 10. 里程碑 M1 验收标准

- [ ] 可创建项目并生成设定
- [ ] 可基于设定生成至少 1 章正文
- [ ] 用户可在对话界面中触发以上流程
- [ ] 项目列表页可查看所有项目
- [ ] 项目详情页可查看设定和第 1 章内容

---

## 11. 风险与应对

| 风险 | 应对 |
|------|------|
| AI 服务不稳定 | 实现 3 次指数退避重试 + 超时控制 |
| 生成质量不达标 | Prompt 工程先行，保留"重生成"入口 |
| SQLite 并发写冲突 | 个人单用户场景下基本可忽略；必要时加文件锁 |
| Phase 1 排期紧张 | 基础对话 UI 和项目页可简化，优先保证生成链路 |
