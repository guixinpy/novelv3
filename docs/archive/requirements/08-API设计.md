# 08-API设计

> **版本**: v3.0  
> **日期**: 2026-04-15

---

## 1. 接口规范

### 1.1 基础规范

- **Base URL**: `/api/v1`
- **Content-Type**: `application/json`
- **认证方式**: Bearer Token
- **响应格式**: 统一包装

### 1.2 统一响应格式

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    timestamp: number;
    requestId: string;
    pagination?: {
      page: number;
      pageSize: number;
      total: number;
      totalPages: number;
    };
  };
}
```

---

## 2. 项目 API

### 2.1 创建项目

```typescript
// POST /api/v1/projects
interface CreateProjectRequest {
  name: string;
  description?: string;
  genre: Genre;
  targetWordCount: number;
  style?: WritingStyle;
  language?: string;
}

interface CreateProjectResponse {
  id: string;
  name: string;
  status: ProjectStatus;
  createdAt: number;
}
```

### 2.2 获取项目列表

```typescript
// GET /api/v1/projects
interface ListProjectsRequest {
  page?: number;
  pageSize?: number;
  status?: ProjectStatus;
  sortBy?: 'createdAt' | 'updatedAt' | 'name';
  sortOrder?: 'asc' | 'desc';
}

interface ListProjectsResponse {
  items: ProjectSummary[];
  total: number;
}

interface ProjectSummary {
  id: string;
  name: string;
  genre: Genre;
  status: ProjectStatus;
  currentWordCount: number;
  targetWordCount: number;
  currentPhase: WritingPhase;
  updatedAt: number;
}
```

### 2.3 获取项目详情

```typescript
// GET /api/v1/projects/:projectId
interface GetProjectResponse extends Project {
  setup?: SetupSummary;
  outline?: OutlineSummary;
  progress: {
    completedChapters: number;
    totalChapters: number;
    percentage: number;
  };
}

interface SetupSummary {
  id: string;
  status: SetupStatus;
  characterCount: number;
}

interface OutlineSummary {
  id: string;
  status: OutlineStatus;
  totalChapters: number;
}
```

### 2.4 更新项目

```typescript
// PATCH /api/v1/projects/:projectId
interface UpdateProjectRequest {
  name?: string;
  description?: string;
  targetWordCount?: number;
  status?: ProjectStatus;
}
```

### 2.5 删除项目

```typescript
// DELETE /api/v1/projects/:projectId
// 响应: 204 No Content
```

---

## 3. 设定 API

### 3.1 生成设定

```typescript
// POST /api/v1/projects/:projectId/setup/generate
interface GenerateSetupRequest {
  additionalRequirements?: string;
}

interface GenerateSetupResponse {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}
```

### 3.2 获取设定

```typescript
// GET /api/v1/projects/:projectId/setup
interface GetSetupResponse extends Setup {}
```

### 3.3 审批设定

```typescript
// POST /api/v1/projects/:projectId/setup/review
interface ReviewSetupRequest {
  approved: boolean;
  comment?: string;
  correctionSuggestion?: string;
}
```

---

## 4. 大纲 API

### 4.1 生成大纲

```typescript
// POST /api/v1/projects/:projectId/outline/generate
interface GenerateOutlineRequest {
  targetChapters?: number;
  additionalRequirements?: string;
}

interface GenerateOutlineResponse {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}
```

### 4.2 获取大纲

```typescript
// GET /api/v1/projects/:projectId/outline
interface GetOutlineResponse extends Outline {}
```

### 4.3 更新大纲章节

```typescript
// PATCH /api/v1/projects/:projectId/outline/chapters/:chapterIndex
interface UpdateChapterOutlineRequest {
  title?: string;
  summary?: string;
  wordCount?: number;
  scenes?: SceneOutline[];
}
```

### 4.4 审批大纲

```typescript
// POST /api/v1/projects/:projectId/outline/review
interface ReviewOutlineRequest {
  approved: boolean;
  comment?: string;
  correctionSuggestion?: string;
}
```

---

## 5. 章节内容 API

### 5.1 生成章节

```typescript
// POST /api/v1/projects/:projectId/chapters/:chapterIndex/generate
interface GenerateChapterRequest {
  retry?: boolean;
  fixInstructions?: string;
}

interface GenerateChapterResponse {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}
```

### 5.2 获取章节

```typescript
// GET /api/v1/projects/:projectId/chapters/:chapterIndex
interface GetChapterResponse extends ChapterContent {}
```

### 5.3 获取章节列表

```typescript
// GET /api/v1/projects/:projectId/chapters
interface ListChaptersRequest {
  status?: ContentStatus;
  page?: number;
  pageSize?: number;
}

interface ListChaptersResponse {
  items: ChapterSummary[];
  total: number;
}

interface ChapterSummary {
  index: number;
  title: string;
  wordCount: number;
  status: ContentStatus;
  reviewStatus: ReviewStatus;
  updatedAt: number;
}
```

### 5.4 审批章节

```typescript
// POST /api/v1/projects/:projectId/chapters/:chapterIndex/review
interface ReviewChapterRequest {
  approved: boolean;
  comment?: string;
  correctionSuggestion?: string;
  rating?: number;
}
```

### 5.5 批量生成章节

```typescript
// POST /api/v1/projects/:projectId/chapters/batch-generate
interface BatchGenerateRequest {
  startChapter: number;
  endChapter: number;
  reviewInterval: number;
}

interface BatchGenerateResponse {
  taskId: string;
  status: 'queued';
  estimatedCompletionTime: number;
}
```

---

## 6. 拓扑图 API

### 6.1 获取拓扑图

```typescript
// GET /api/v1/projects/:projectId/topology
interface GetTopologyResponse extends Topology {}
```

### 6.2 查询相关节点

```typescript
// GET /api/v1/projects/:projectId/topology/nodes/:nodeId/related
interface GetRelatedNodesRequest {
  maxDepth?: number;
}

interface GetRelatedNodesResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}
```

### 6.3 获取角色关系图

```typescript
// GET /api/v1/projects/:projectId/topology/character-graph
interface GetCharacterGraphResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}
```

### 6.4 获取情节时间线

```typescript
// GET /api/v1/projects/:projectId/topology/timeline
interface GetTimelineResponse {
  events: Array<{
    chapter: number;
    description: string;
    impact: string;
  }>;
  totalChapters: number;
}
```

---

## 7. 反馈 API

### 7.1 提交反馈

```typescript
// POST /api/v1/projects/:projectId/feedback
interface SubmitFeedbackRequest {
  nodeId: string;
  chapterId?: string;
  type: FeedbackType;
  severity: FeedbackSeverity;
  content: {
    originalText?: string;
    userComment?: string;
    suggestedChange?: string;
    rating?: number;
  };
}

interface SubmitFeedbackResponse {
  feedbackId: string;
  status: 'received';
}
```

### 7.2 获取反馈列表

```typescript
// GET /api/v1/projects/:projectId/feedback
interface ListFeedbackRequest {
  type?: FeedbackType;
  severity?: FeedbackSeverity;
  page?: number;
  pageSize?: number;
}

interface ListFeedbackResponse {
  items: UserFeedback[];
  total: number;
}
```

---

## 8. 导出 API

### 8.1 导出项目

```typescript
// POST /api/v1/projects/:projectId/export
interface ExportProjectRequest {
  format: 'markdown' | 'txt' | 'docx' | 'epub';
  options?: {
    includeSetup?: boolean;
    includeOutline?: boolean;
    chapterRange?: [number, number];
  };
}

interface ExportProjectResponse {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}
```

### 8.2 获取导出状态

```typescript
// GET /api/v1/export/:taskId/status
interface GetExportStatusResponse {
  taskId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: number;
  downloadUrl?: string;
  error?: string;
}
```

### 8.3 下载导出文件

```typescript
// GET /api/v1/export/:taskId/download
// 响应: 文件流
```

---

## 9. 任务 API

### 9.1 获取任务状态

```typescript
// GET /api/v1/tasks/:taskId
interface GetTaskResponse {
  id: string;
  type: 'generate_setup' | 'generate_outline' | 'generate_content' | 'export';
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  result?: unknown;
  error?: {
    code: string;
    message: string;
  };
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
}
```

### 9.2 取消任务

```typescript
// POST /api/v1/tasks/:taskId/cancel
// 响应: 204 No Content
```

---

## 10. 错误码

| 错误码 | 描述 | HTTP 状态码 |
|--------|------|-------------|
| `INVALID_REQUEST` | 请求参数错误 | 400 |
| `UNAUTHORIZED` | 未授权 | 401 |
| `FORBIDDEN` | 禁止访问 | 403 |
| `NOT_FOUND` | 资源不存在 | 404 |
| `PROJECT_NOT_FOUND` | 项目不存在 | 404 |
| `INVALID_PROJECT_STATUS` | 项目状态不允许此操作 | 400 |
| `GENERATION_IN_PROGRESS` | 生成任务进行中 | 409 |
| `AI_SERVICE_ERROR` | AI 服务错误 | 502 |
| `INTERNAL_ERROR` | 内部错误 | 500 |
