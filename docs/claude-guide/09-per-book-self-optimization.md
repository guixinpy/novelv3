# 09 · per-book 自优化系统设计定稿（写作经验积累）

需求来源：用户预想（2026-08-02 澄清）——单本书内 agent 持续积累学习（章末自省 → 书级记忆 → 后续注入），非旧 learned PromptRule（已永久放弃）。经需求讨论（7 决策）→ 4 视角多视角评审 → 3 最终决策定稿。

## 一、需求与决策记录

### 用户预想
- 作用于**单本小说**（per-book，不跨书污染）
- agent 在创作中不断积累：每章写完后章末自省（LLM 总结本章写作经验）
- 经验存入该书记忆，后续章节写作时注入

### 讨论确认的 7 项决策（2026-08-02）
1. **内容形态**：分类结构化（节奏 / 文风 / 设定运用 / 教训）
2. **注入方式**：自动注入（快照携带，模型无需主动查询）
3. **成本控制**：分级准入——特化适配：自省本身是 LLM 调用，准入由自省 LLM 顺带判断（不值得记录就不输出），不做 openhuman 三带打分
4. **生命周期**：信任度 + 衰减
5. **重复判定**：LLM 结构化键（每条经验带 key + action: new / reinforce / override）
6. **触发**：自动（原定 pipeline，评审修正为双触发点）
7. **注入形态**：最近 2-3 条 + 高信任 1-2 条

### 4 视角评审结论（2026-08-02，子代理）
- **创作视角**：需修改后做——自省必须锚定"意图 vs 产出"并强制负面采样（对抗自夸偏置）；注入改写后校验为主；信任度需效用信号
- **读者视角**：需修改后做——悬念/伏笔管理才是弃书第一主因（本设计未覆盖，定为独立后续项）；经验与设定卡构成双源事实漂移（权威优先级：设定卡 > 经验）
- **工程视角**：契合度高但关键修正——**pipeline 在生产代码中无调用方**（生产走 harness + write_chapter 工具），自省必须做成领域服务 + 双触发点；信任度放 memory_metadata 不加表；override 靠 scope_key 复用 + 自省提示词携带候选 key 防漂移
- **成本视角**：边界偏负 → 修正后可行——LLM 成本可忽略（~¥0.26/100 章），真正成本是架构复杂度与劣化风险；MVP 建议作者在环

### 3 项最终决策（2026-08-02）
1. **范围**：四分类 + 评审修正（保留用户预想，修复全部已知缺陷）
2. **作者在环**：自动执行 + **否决入口**（作者可删除任意经验、钉住重要经验不衰减）
3. **伏笔账本**：独立后续项（track_plotline 已覆盖基础登记 + 超 30 章 stale 警告）

## 二、最终设计

### 流程
```
每章 finalize / harness 回合结束
  → 自省（LLM 短调用，锚定章纲 + 负面采样）
  → 结构化输出（分类 + [{key, action, text}]）
  → 记忆入库（LongformMemory, memory_type="writing_experience", 信任度记账）
  → 下一章快照【写作经验】段自动携带
```

### 自省（领域服务 domain/memory/writing_experience.py）
- **输入**：章纲（plan 上下文）+ 最终稿 + review 的 REVISE 理由（若有）+ 该类目最近 5 个候选 key
- **输出**（结构化 JSON，~0.3-1k token）：
  ```json
  {"category": "节奏|文风|设定运用|教训",
   "experiences": [
     {"key": "战斗场景长度", "action": "new|reinforce|override", "text": "..."}
   ]}
  ```
- **提示词纪律**（评审护栏）：
  - 强制负面采样："本章相对章纲偏离了什么？最失败的三处是什么？"
  - 只记写作实践（节奏手段/文风手段/设定使用方式/过程教训），**禁记情节内容类教训**（题材无关边界）
  - **设定事实不入经验库**（"灵力消耗规则"只存在于设定卡；只可记"灵力消耗在战斗里自然带出效果好"这类呈现手法）
  - 格式类问题已由规则 review 覆盖，不要重复记录
- **fail-open**：自省调用失败仅记 `memory_metadata.last_introspect_error`，不阻塞 finalize、不阻塞注入

### 存储与信任度
- `LongformMemory` 复用：`memory_type="writing_experience"`，`scope_key=经验键`（唯一约束复用），`memory_metadata={trust_score, category, last_reinforce_chapter_index, pinned, provenance:"agent_inferred"}`
- **记账**（代码惰性执行，无后台任务）：
  - new → trust_score=1
  - reinforce（LLM 判定同 key 重复出现）→ +1
  - override（LLM 判定新文本推翻旧）→ 旧经验 -1 且新文本覆盖
  - 30 章未强化（last_reinforce_chapter_index 距当前 ≥30）→ -1；trust_score ≤0 → status="archived"（不再注入）
  - pinned=True 的经验：不衰减、不淘汰
- **预算**：每类上限 20 条，超限按 trust_score 淘汰（复用 _cap_by_channel 模式）
- 自省提示词携带候选 key：LLM 必须命中已有 key 或新建，防 key 漂移导致 override 永不生效

### 注入（快照段）
- `build_project_snapshot` 加【写作经验·仅供参考】段：
  - 最近 2 条（按 last_reinforce_chapter_index 倒序）
  - 高信任 1 条（trust_score ≥3，轮转避免同条连续注入）
  - 每条 ≤60 字 + 章节锚点（如"Ch12 验证"）
  - 注入措辞统一"经验"而非"规则"
- 预算：~120 token 固定开销，查询侧截断（快照是字符串拼接无硬预算，靠条目数 + 截断控制）
- `include_experience: bool = True` 参数（config 可关）

### 触发（双触发点，评审关键修正）
- 触发点 1：`ChapterPipeline.run` 中 `engine.run` 之后（同步 worker 形态，不动 WorkflowEngine）
- 触发点 2：harness 回合结束（write_chapter 落库后）——**生产路径**（agent.py 的 harness 是唯一生产调用方）
- 均 config 可关

### 作者否决入口（MVP）
- domain 函数：`delete_experience(db, project_id, key)` / `pin_experience(db, project_id, key, pinned)`
- API 端点预留（前端重写时接线）；MVP 提供函数 + 测试

## 三、验收标准

1. **端到端**：写一章（harness 路径）→ 自省触发 → 下一章快照带经验段
2. **fail-open**：自省 provider 抛错时，finalize 结果与不启用时逐字段一致
3. **信任度记账**：new/reinforce/override/30 章衰减/归档/pinned 的单元测试
4. **注入预算**：快照经验段 ≤3 条、每条 ≤60 字
5. **题材无关**：自省提示词禁记情节内容（评审护栏入测试？至少提示词常量可断言）

## 四、实现计划

- **Phase 1**：领域服务（introspect_and_record + 记账函数 + 作者入口函数）+ 快照段 + 双触发点 + 全套测试
- **Phase 2**：API 端点（否决入口）——前端重写时接线
- **独立后续项**：伏笔/悬念账本（结构化寄存器：埋设章/承诺/预计回收/状态，注入优先超期钩子）——track_plotline 升级或新模块
