# Inspector Compact Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把右侧 Inspector 头部压缩为精简结构，减少纵向占高，同时保留主线 tab 与低频面板入口。

**Architecture:** 在 `InspectorPanel` 内把头部分成“标题 + 模式按钮”和“主线 tab + 更多菜单”两层，保留现有面板切换协议，不改 `workspace` store 和后端接口。低频面板收纳为前端局部菜单，避免把所有入口平铺在头部。

**Tech Stack:** Vue 3 `script setup`、TypeScript、Vitest、Vue Test Utils、Vite

---

### Task 1: 为精简头部写失败测试

**Files:**
- Create: `frontend/src/components/workspace/InspectorPanel.compact.test.ts`
- Modify: `frontend/src/components/workspace/InspectorPanel.vue`
- Test: `frontend/src/components/workspace/InspectorPanel.compact.test.ts`

- [ ] **Step 1: 写失败测试，约束主线 tab 与“更多”行为**

```ts
it('只展示主线 tab，低频项收纳进更多菜单', async () => {
  const wrapper = mountInspector({ panel: 'setup' })

  expect(wrapper.text()).toContain('概览')
  expect(wrapper.text()).toContain('设定')
  expect(wrapper.text()).toContain('故事线')
  expect(wrapper.text()).toContain('大纲')
  expect(wrapper.text()).toContain('正文')
  expect(wrapper.text()).toContain('更多')
  expect(wrapper.text()).not.toContain('版本历史')

  await wrapper.get('[data-testid="inspector-more-toggle"]').trigger('click')
  expect(wrapper.text()).toContain('版本历史')
  expect(wrapper.text()).toContain('偏好设置')
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/workspace/InspectorPanel.compact.test.ts`
Expected: FAIL，当前实现仍直接渲染全量 tab，且不存在“更多”菜单。

- [ ] **Step 3: 最小实现精简头部**

```vue
const PRIMARY_TABS = new Set(['overview', 'setup', 'storyline', 'outline', 'content'])
const primaryTabs = computed(() => props.tabs.filter((tab) => PRIMARY_TABS.has(tab.id)))
const overflowTabs = computed(() => props.tabs.filter((tab) => !PRIMARY_TABS.has(tab.id)))
```

- [ ] **Step 4: 再跑测试，确认转绿**

Run: `cd frontend && npm run test:unit -- src/components/workspace/InspectorPanel.compact.test.ts`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/plans/2026-04-18-inspector-compact-header.md frontend/src/components/workspace/InspectorPanel.compact.test.ts frontend/src/components/workspace/InspectorPanel.vue
git commit -m "feat: compact inspector header"
```

### Task 2: 收紧头部样式并稳定交互

**Files:**
- Modify: `frontend/src/components/workspace/InspectorPanel.vue`
- Modify: `frontend/src/components/WorkspaceTabs.vue`
- Test: `frontend/src/components/workspace/InspectorPanel.compact.test.ts`

- [ ] **Step 1: 补测试，约束旧文案和眉标不再占位**

```ts
it('移除旧眉标和原因文案，只保留当前面板标题', () => {
  const wrapper = mountInspector({ panel: 'setup', reason: '你切换到设定' })

  expect(wrapper.text()).toContain('设定')
  expect(wrapper.text()).not.toContain('Inspector')
  expect(wrapper.text()).not.toContain('你切换到设定')
})
```

- [ ] **Step 2: 运行测试，确认先红**

Run: `cd frontend && npm run test:unit -- src/components/workspace/InspectorPanel.compact.test.ts`
Expected: FAIL，当前头部仍渲染眉标和原因文案。

- [ ] **Step 3: 最小实现样式收紧与按钮尺寸下调**

```css
.inspector-panel__toolbar {
  gap: 0.65rem;
  padding: 0.9rem 1rem 0.8rem;
}

.inspector-panel__title {
  font-size: 1.2rem;
  line-height: 1.15;
}
```

- [ ] **Step 4: 跑目标测试与全量前端单测**

Run: `cd frontend && npm run test:unit`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/workspace/InspectorPanel.vue frontend/src/components/WorkspaceTabs.vue frontend/src/components/workspace/InspectorPanel.compact.test.ts
git commit -m "fix: streamline inspector header layout"
```

### Task 3: 浏览器回归与构建验证

**Files:**
- Modify: `scripts/verify_full_app_ui.sh`
- Test: `scripts/verify_full_app_ui.sh`

- [ ] **Step 1: 如有必要补一条 browser smoke，检查“更多”菜单存在**

```bash
agent-browser snapshot -i
agent-browser click @eN
agent-browser wait --text "版本历史"
```

- [ ] **Step 2: 跑构建**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: 跑完整 UI 验证**

Run: `./scripts/verify_full_app_ui.sh`
Expected: PASS，右侧 Inspector 页面可正常切换，控制台无错误。

- [ ] **Step 4: 提交**

```bash
git add scripts/verify_full_app_ui.sh
git commit -m "test: cover compact inspector header"
```
