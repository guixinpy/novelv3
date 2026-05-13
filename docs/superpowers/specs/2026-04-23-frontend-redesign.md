# 墨舟 (Mozhou) Frontend UI Redesign — Design Spec

**Date:** 2026-04-23
**Status:** Approved
**Scope:** Complete frontend view-layer rewrite — Vue 3 + TypeScript + Pinia + Tailwind

---

## 0. Design Philosophy

- Extreme minimalism. Every pixel earns its place.
- No decorative cards. Hierarchy through spacing, typography, and borders.
- Tables over grids for data display.
- Single brand color (indigo) for interactive elements only.
- Progressive disclosure — sub-nav items expand detail in main area.
- 4px grid, religiously.

---

## 1. Design Tokens

All tokens live in `src/styles/tokens.css` as CSS custom properties on `:root`.

### 1.1 Colors

```css
:root {
  /* --- Backgrounds --- */
  --color-bg-primary: #FAFAFA;
  --color-bg-secondary: #F5F5F5;
  --color-bg-tertiary: #EFEFEF;
  --color-bg-white: #FFFFFF;

  /* --- Text --- */
  --color-text-primary: #1A1A1A;
  --color-text-secondary: #6B7280;
  --color-text-tertiary: #9CA3AF;
  --color-text-inverse: #FFFFFF;

  /* --- Brand (Indigo) --- */
  --color-brand: #4F46E5;
  --color-brand-hover: #4338CA;
  --color-brand-active: #3730A3;
  --color-brand-light: #EEF2FF;       /* bg tint for selections, user messages */
  --color-brand-subtle: #E0E7FF;      /* lighter tint for hover states */

  /* --- Borders --- */
  --color-border: #E5E7EB;
  --color-border-strong: #D1D5DB;

  /* --- Semantic --- */
  --color-success: #16A34A;
  --color-success-light: #F0FDF4;
  --color-warning: #D97706;
  --color-warning-light: #FFFBEB;
  --color-error: #DC2626;
  --color-error-light: #FEF2F2;

  /* --- Activity Bar --- */
  --color-activity-bar-bg: #1E1E2E;
  --color-activity-bar-icon: #9CA3AF;
  --color-activity-bar-icon-active: #FFFFFF;
  --color-activity-bar-accent: var(--color-brand);
  --color-activity-bar-item-active-bg: rgba(255, 255, 255, 0.08);
}
```

### 1.2 Spacing

4px base unit. Scale: `--space-{n}` = `n * 4px`.

```css
:root {
  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-7: 28px;
  --space-8: 32px;
  --space-9: 36px;
  --space-10: 40px;
  --space-11: 44px;
  --space-12: 48px;
}
```

### 1.3 Typography

```css
:root {
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', monospace;

  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

### 1.4 Border Radius

```css
:root {
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;
}
```

### 1.5 Shadows

```css
:root {
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
}
```

### 1.6 Transitions

```css
:root {
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;
}
```

### 1.7 Layout Constants

```css
:root {
  --topbar-height: 48px;
  --activity-bar-width: 48px;
  --subnav-width: 220px;
  --content-padding: var(--space-6);  /* 24px */
  --athena-chat-width: 400px;
}
```

---

## 2. Global Layout Shell

### 2.1 Structure

```
┌──────────────────────────────────────────────────────┐
│  TopBar (48px)                                       │
├────────┬──────────┬──────────────────────────────────┤
│Activity│ Sub-Nav  │  Main Content Area               │
│  Bar   │  220px   │  (flex: 1, scrollable)           │
│  48px  │(collapse)│                                  │
│        │          │                                  │
└────────┴──────────┴──────────────────────────────────┘
```

### 2.2 CSS Grid Definition

```css
.app-shell {
  display: grid;
  grid-template-rows: var(--topbar-height) 1fr;
  grid-template-columns: var(--activity-bar-width) var(--subnav-width) 1fr;
  grid-template-areas:
    "topbar   topbar   topbar"
    "activity subnav   content";
  height: 100vh;
  overflow: hidden;
}

/* Collapsed sub-nav variant */
.app-shell--subnav-collapsed {
  grid-template-columns: var(--activity-bar-width) 0px 1fr;
}

/* No-sidebar variant (project list, settings) */
.app-shell--no-sidebar {
  grid-template-columns: 1fr;
  grid-template-areas:
    "topbar"
    "content";
}
```

### 2.3 TopBar

- Grid area: `topbar`
- Height: `48px`, fixed
- Background: `var(--color-bg-white)`
- Bottom border: `1px solid var(--color-border)`
- `z-index: 40`
- Layout: `display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-4);`

Content:
- **Left**: Brand mark "墨舟" — `font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--color-brand);`
- **Center-left**: Project selector dropdown (only visible when inside a project). Shows current project name, click opens dropdown to switch projects.
- **Right**: Settings gear icon button (navigates to `/settings`).

```typescript
// TopBar.vue props
interface TopBarProps {
  projectName?: string       // shown in project selector; undefined hides selector
  projects?: { id: string; title: string }[]
}
// emits: 'select-project', 'navigate-settings'
```

### 2.4 Activity Bar

- Grid area: `activity`
- Width: `48px`, fixed
- Background: `var(--color-activity-bar-bg)` (#1E1E2E)
- Full height below TopBar
- Layout: `display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: var(--space-2) 0;`

Top section (workspace icons, vertically stacked):
| Icon | Label    | Route target                    |
|------|----------|---------------------------------|
| ☿    | Hermes   | `/projects/:id/hermes`          |
| ⏣    | Athena   | `/projects/:id/athena`          |
| 📜   | Manuscript | `/projects/:id/manuscript`    |

Bottom section:
| Icon | Label    | Route target |
|------|----------|-------------|
| ⚙    | Settings | `/settings` |

Active state:
- Left accent bar: `3px solid var(--color-brand)`, positioned absolute left
- Background: `var(--color-activity-bar-item-active-bg)`
- Icon color: `var(--color-activity-bar-icon-active)` (white)

Inactive state:
- Icon color: `var(--color-activity-bar-icon)` (#9CA3AF)
- Hover: icon color transitions to white

```typescript
// ActivityBar.vue props
interface ActivityBarProps {
  activeWorkspace: 'hermes' | 'athena' | 'manuscript' | null
  projectId: string
}
// emits: 'navigate'
```

### 2.5 Sub-Navigation Panel

- Grid area: `subnav`
- Width: `220px`, collapsible to `0px` with CSS transition
- Background: `var(--color-bg-primary)` (#FAFAFA)
- Right border: `1px solid var(--color-border)`
- Overflow-y: auto (scrollable)
- Layout: `display: flex; flex-direction: column;`

Collapse toggle: small button at top-right corner of the panel (chevron icon). Clicking collapses the panel; the Activity Bar remains visible.

Content is determined by the active workspace (see Section 3 for per-workspace sub-nav content).

```typescript
// SubNav.vue props
interface SubNavProps {
  collapsed: boolean
}
// emits: 'toggle-collapse'
// slots: default (workspace-specific content)
```

### 2.6 Main Content Area

- Grid area: `content`
- `overflow-y: auto;`
- `padding: var(--content-padding);` (24px)
- Background: `var(--color-bg-white)`

---

## 3. Page Layouts

### 3.1 Project List Page (`/`)

**Shell mode:** `no-sidebar` — no Activity Bar, no Sub-Nav. TopBar + full-width content only.

**Layout:**

```
TopBar
─────────────────────────────────────────
  页面标题 "项目"                [+ 新建项目]
─────────────────────────────────────────
  项目名称        类型    字数    状态    最后修改    操作
  ─────────────────────────────────────────
  《三体》        科幻    120k   进行中  2h ago      🗑
  《红楼梦》      古典    350k   已完成  3d ago      🗑
  ...
─────────────────────────────────────────
```

Specifics:
- Top section: `display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6);`
  - Title: `font-size: var(--text-xl); font-weight: var(--font-semibold);`
  - "新建项目" button: `BaseButton variant="primary" size="sm"`
- Table: `BaseTable` component, full width
  - Columns: 项目名称 (bold, `font-weight: var(--font-medium)`), 类型, 字数, 状态 (`BaseBadge`), 最后修改 (relative time), 操作 (delete icon)
  - Row hover: `background: var(--color-bg-secondary);`
  - Row click: navigates to `/projects/:id/hermes`
  - Delete: icon button, opens `ConfirmDialog`
- Empty state: centered vertically, `color: var(--color-text-secondary);` text "还没有项目" + "新建项目" button
- Max content width: `960px`, centered

### 3.2 Hermes — Writing Dialog (`/projects/:id/hermes`)

**Shell mode:** `sidebar` — Activity Bar (Hermes active) + Sub-Nav + Content.

#### Sub-Nav Content

```
┌─────────────────────┐
│ 创作阶段             │  ← section header, text-xs uppercase
│                     │
│  ● 设定        ✓    │  ← done state: green dot + check
│  ● 故事线      ✓    │
│  ◉ 大纲        →    │  ← current: brand dot + arrow
│  ○ 正文             │  ← pending: gray dot
│                     │
│─────────────────────│  ← 1px border divider
│ 章节                 │
│                     │
│  第1章    2,340字    │  ← active: brand-light bg
│  第2章    1,890字    │
│  第3章    0字        │
│  ...                │
│                     │
│─────────────────────│
│  📤 导出             │  ← ghost button, opens modal
│  🕐 版本历史         │  ← ghost button, opens modal
└─────────────────────┘
```

Phase stepper component (`PhaseProgress`):

```typescript
interface PhaseProgressProps {
  phases: {
    key: string
    label: string
    status: 'done' | 'current' | 'pending'
  }[]
}
```

Phase status styling:
- `done`: `color: var(--color-success);` green dot, checkmark icon
- `current`: `color: var(--color-brand);` filled dot, arrow indicator
- `pending`: `color: var(--color-text-tertiary);` hollow dot

Chapter list (`ChapterList`):

```typescript
interface ChapterListProps {
  chapters: { index: number; wordCount: number }[]
  activeIndex: number | null
}
// emits: 'select'
```

- Active chapter: `background: var(--color-brand-light); color: var(--color-brand); font-weight: var(--font-medium);`
- Hover: `background: var(--color-bg-secondary);`
- Each row: `padding: var(--space-2) var(--space-3); font-size: var(--text-sm);`

#### Main Content — Chat Interface

```
┌─────────────────────────────────────────────┐
│                                             │
│  [Assistant message]                        │  ← left-aligned
│  ┌─────────────────────────────────┐        │
│  │ 白色背景, 左侧 3px brand border │        │
│  └─────────────────────────────────┘        │
│                                             │
│              [User message]                 │  ← right-aligned
│        ┌─────────────────────────────┐      │
│        │ brand-light 背景             │      │
│        └─────────────────────────────┘      │
│                                             │
│  [Loading...]                               │  ← pulse animation
│                                             │
├─────────────────────────────────────────────┤
│  / slash command menu (floating above)      │
│  ┌─────────────────────────────────────┐    │
│  │ [input field                    ] [➤]│    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

Message styling:
- Assistant: `background: var(--color-bg-white); border-left: 3px solid var(--color-brand); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md);`
- User: `background: var(--color-brand-light); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); margin-left: auto; max-width: 80%;`
- Loading: three dots with `animation: pulse 1.5s ease-in-out infinite;`

Input bar:
- Sticky to bottom of content area
- `display: flex; gap: var(--space-2); padding: var(--space-3); border-top: 1px solid var(--color-border); background: var(--color-bg-white);`
- Input: `flex: 1; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); font-size: var(--text-sm);`
- Send button: `BaseButton variant="primary" size="sm"`, icon-only (arrow)
- Slash command menu: floating panel above input, triggered by typing `/`. List of commands with keyboard navigation.

### 3.3 Athena — World Model (`/projects/:id/athena`)

**Shell mode:** `sidebar` — Activity Bar (Athena active) + Sub-Nav + Content.

#### Sub-Nav Content

```
┌─────────────────────┐
│ 本体                 │  ← section header
│   角色               │
│   地点               │
│   势力               │
│   物品               │
│   关系               │
│   规则               │
│                     │
│ 状态                 │
│   真相投影           │
│   时间线             │
│   主体认知           │
│                     │
│ 演化                 │
│   大纲               │
│   故事线             │
│   提案               │
│   一致性检查         │
│                     │
│─────────────────────│
│  💬 Athena 对话      │  ← opens slide-over chat
└─────────────────────┘
```

Section headers: `font-size: var(--text-xs); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-tertiary); padding: var(--space-3) var(--space-3) var(--space-1);`

Nav items: `font-size: var(--text-sm); padding: var(--space-1) var(--space-3) var(--space-1) var(--space-5); color: var(--color-text-secondary); cursor: pointer;`
- Hover: `color: var(--color-text-primary); background: var(--color-bg-secondary);`
- Active: `color: var(--color-brand); font-weight: var(--font-medium); background: var(--color-brand-light);`

Route mapping: clicking a sub-nav item navigates to `/projects/:id/athena/:section` where `:section` is one of: `characters`, `locations`, `factions`, `items`, `relations`, `rules`, `projection`, `timeline`, `knowledge`, `outline`, `storyline`, `proposals`, `consistency`.

#### Main Content — Detail Views

Each section renders a detail view in the main content area. All use clean table/list layouts.

**Entity lists** (角色, 地点, 势力, 物品):
- `BaseTable` with columns: 名称, 类型, 描述
- Row click expands inline detail or opens side panel
- Empty state: "暂无数据"

**Relations** (关系):
- `BaseTable` with columns: 源实体 → 关系类型 → 目标实体
- Arrow rendered as `color: var(--color-text-tertiary);`

**Rules** (规则):
- Numbered list, each rule in a row with `border-bottom: 1px solid var(--color-border);`
- `font-size: var(--text-sm); padding: var(--space-3) 0;`

**Timeline** (时间线):
- Vertical timeline layout
- Left: vertical line `2px solid var(--color-border)` with dots at each event
- Dot: `8px` circle, `background: var(--color-brand);` for current, `var(--color-border)` for past
- Right: event description + chapter reference + timestamp
- `padding-left: var(--space-6);` from the line

**Projection** (真相投影):
- Key-value table: subject → predicate → value
- Grouped by entity, collapsible sections

**Knowledge** (主体认知):
- Grouped by subject, each showing what they know vs ground truth
- Discrepancies highlighted with `background: var(--color-warning-light);`

**Proposals** (提案):
- List of proposal bundles
- Each row: title, status (`BaseBadge`), created date, item count
- Click expands to show proposal items, reviews, impact
- Status badges: `draft` → neutral, `pending` → warning, `approved` → success, `rejected` → error

**Consistency** (一致性检查):
- List of check results
- Each row: check type, status badge, description
- Expandable detail with evidence references

#### Athena Chat Slide-Over

- Triggered by "Athena 对话" button in sub-nav
- Slides in from right edge
- Width: `400px`
- Background: `var(--color-bg-white)`
- Left border: `1px solid var(--color-border)`
- Shadow: `var(--shadow-md)`
- `z-index: 30`
- Header: "Athena" title + close button
- Body: same chat message layout as Hermes (scrollable messages + input bar)
- Transition: `transform 200ms ease` (translateX)

```typescript
interface AthenaChatPanelProps {
  open: boolean
  projectId: string
}
// emits: 'close'
```

### 3.4 Manuscript (`/projects/:id/manuscript`)

**Shell mode:** `sidebar` — Activity Bar (Manuscript active) + Sub-Nav + Content.

Sub-Nav: same chapter list as Hermes (reuse `ChapterList` component).

Main Content: centered placeholder.
```html
<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--color-text-tertiary); font-size: var(--text-lg);">
  正文编辑器即将推出
</div>
```

### 3.5 Settings Page (`/settings`)

**Shell mode:** `no-sidebar`.

Layout: max-width `720px`, centered. Clean form sections.

```
┌─────────────────────────────────────┐
│ 设置                                │
│                                     │
│ API 配置                            │  ← section header
│ ─────────────────────────────────── │
│ API Key    [••••••••••••]  [保存]   │
│ 模型       [deepseek-chat ▾]       │
│                                     │
│ 偏好设置                            │
│ ─────────────────────────────────── │
│ 语言       [中文 ▾]                │
│                                     │
└─────────────────────────────────────┘
```

Section header: `font-size: var(--text-lg); font-weight: var(--font-semibold); margin-bottom: var(--space-4); padding-bottom: var(--space-2); border-bottom: 1px solid var(--color-border);`

Form rows: `display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-4);`

---

## 4. Component Architecture

### 4.1 Directory Structure

```
src/
├── assets/
├── components/
│   ├── base/
│   │   ├── BaseButton.vue
│   │   ├── BaseInput.vue
│   │   ├── BaseSelect.vue
│   │   ├── BaseModal.vue
│   │   ├── BaseBadge.vue
│   │   ├── BaseDropdown.vue
│   │   ├── BaseTabs.vue
│   │   ├── BaseTable.vue
│   │   ├── BaseTooltip.vue
│   │   └── ConfirmDialog.vue
│   ├── layout/
│   │   ├── AppShell.vue
│   │   ├── TopBar.vue
│   │   ├── ActivityBar.vue
│   │   ├── SubNav.vue
│   │   └── ContentArea.vue
│   ├── chat/
│   │   ├── ChatMessage.vue
│   │   ├── ChatInput.vue
│   │   ├── ChatMessageList.vue
│   │   └── CommandMenu.vue
│   ├── athena/
│   │   ├── EntityTable.vue
│   │   ├── RelationTable.vue
│   │   ├── RuleList.vue
│   │   ├── TimelineView.vue
│   │   ├── ProjectionViewer.vue
│   │   ├── KnowledgeViewer.vue
│   │   ├── ProposalList.vue
│   │   ├── ConsistencyList.vue
│   │   └── AthenaChatPanel.vue
│   ├── project/
│   │   ├── ProjectTable.vue
│   │   └── ProjectCreateDialog.vue
│   └── shared/
│       ├── PhaseProgress.vue
│       ├── ChapterList.vue
│       ├── ExportModal.vue
│       └── VersionsModal.vue
├── composables/
│   ├── useModal.ts
│   ├── useToast.ts
│   └── useKeyboard.ts
├── stores/
│   ├── project.ts
│   ├── chat.ts
│   ├── workspace.ts       (simplified)
│   ├── athena.ts
│   ├── worldModel.ts
│   └── ui.ts              (new)
├── api/
│   ├── client.ts
│   └── types.ts
├── router/
│   └── index.ts
├── views/
│   ├── ProjectListView.vue
│   ├── HermesView.vue
│   ├── AthenaView.vue
│   ├── ManuscriptView.vue
│   └── SettingsView.vue
├── styles/
│   ├── tokens.css
│   ├── reset.css
│   ├── base.css
│   └── utilities.css
├── App.vue
└── main.ts
```

### 4.2 Base Component Interfaces

#### BaseButton

```typescript
interface BaseButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'  // default: 'secondary'
  size?: 'sm' | 'md'                                       // default: 'md'
  disabled?: boolean
  loading?: boolean
  iconOnly?: boolean    // square button for icon-only use
}
```

Styling by variant:
- `primary`: `background: var(--color-brand); color: white; &:hover { background: var(--color-brand-hover); }`
- `secondary`: `background: transparent; border: 1px solid var(--color-border); color: var(--color-text-primary); &:hover { background: var(--color-bg-secondary); }`
- `ghost`: `background: transparent; color: var(--color-text-secondary); &:hover { color: var(--color-text-primary); background: var(--color-bg-secondary); }`
- `danger`: `background: transparent; color: var(--color-error); border: 1px solid var(--color-error); &:hover { background: var(--color-error); color: white; }`

Sizing:
- `sm`: `height: 32px; padding: 0 var(--space-3); font-size: var(--text-sm);`
- `md`: `height: 36px; padding: 0 var(--space-4); font-size: var(--text-sm);`

Common: `border-radius: var(--radius-md); transition: all var(--transition-fast); cursor: pointer; font-weight: var(--font-medium);`

#### BaseInput

```typescript
interface BaseInputProps {
  modelValue: string
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  type?: 'text' | 'password' | 'email'
}
// emits: 'update:modelValue'
```

Styling:
- `height: 36px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-bg-white); transition: border-color var(--transition-fast);`
- Focus: `border-color: var(--color-brand); outline: none; box-shadow: 0 0 0 2px var(--color-brand-subtle);`
- Error: `border-color: var(--color-error);`
- Label: `font-size: var(--text-sm); font-weight: var(--font-medium); margin-bottom: var(--space-1); color: var(--color-text-primary);`
- Error text: `font-size: var(--text-xs); color: var(--color-error); margin-top: var(--space-1);`

#### BaseModal

```typescript
interface BaseModalProps {
  open: boolean
  title?: string
  width?: string   // default: '480px'
}
// emits: 'close'
```

- Backdrop: `position: fixed; inset: 0; background: rgba(0, 0, 0, 0.3); z-index: 50;`
- Panel: `background: var(--color-bg-white); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); max-height: 85vh; overflow-y: auto;`
- Header: `padding: var(--space-4); border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center;`
- Body slot: `padding: var(--space-4);`
- Footer slot: `padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: var(--space-2);`
- Close on Escape key, close on backdrop click
- Teleported to `<body>`

#### BaseBadge

```typescript
interface BaseBadgeProps {
  variant?: 'success' | 'warning' | 'error' | 'neutral'  // default: 'neutral'
  size?: 'sm' | 'md'
}
```

Styling:
- `display: inline-flex; align-items: center; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium);`
- `sm`: `padding: 2px 8px;` / `md`: `padding: 4px 10px;`
- `success`: `background: var(--color-success-light); color: var(--color-success);`
- `warning`: `background: var(--color-warning-light); color: var(--color-warning);`
- `error`: `background: var(--color-error-light); color: var(--color-error);`
- `neutral`: `background: var(--color-bg-tertiary); color: var(--color-text-secondary);`

#### BaseTable

```typescript
interface BaseTableColumn {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
}

interface BaseTableProps {
  columns: BaseTableColumn[]
  data: Record<string, unknown>[]
  rowKey?: string                    // default: 'id'
  hoverable?: boolean                // default: true
  clickable?: boolean                // default: false
  emptyText?: string                 // default: '暂无数据'
}
// emits: 'row-click', 'sort'
```

Styling:
- `width: 100%; border-collapse: collapse;`
- Header: `font-size: var(--text-xs); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-tertiary); border-bottom: 1px solid var(--color-border); padding: var(--space-2) var(--space-3);`
- Row: `border-bottom: 1px solid var(--color-border); font-size: var(--text-sm);`
- Cell: `padding: var(--space-3);`
- Hover (when `hoverable`): `background: var(--color-bg-secondary);`
- Clickable: `cursor: pointer;`

#### BaseDropdown, BaseTabs, BaseTooltip, BaseSelect

Follow the same pattern: minimal props, design-token-based styling, no decorative elements. Detailed interfaces omitted for brevity — follow the same conventions as above.

#### ConfirmDialog

```typescript
interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmText?: string    // default: '确认'
  cancelText?: string     // default: '取消'
  variant?: 'danger' | 'default'
}
// emits: 'confirm', 'cancel'
```

Built on `BaseModal`. Confirm button uses `BaseButton variant="danger"` when `variant="danger"`.

---

## 5. State Management

### 5.1 Existing Stores — Changes

**`project.ts`** — No API changes. Remove any theme/palette-related state if present.

**`chat.ts`** — Remove `dialogType` concept. The Hermes chat and Athena chat are separate concerns:
- Hermes chat: managed by `chat.ts` (existing)
- Athena chat: managed by `athena.ts` (add chat methods there)

**`workspace.ts`** — Simplify significantly. Remove `mode`, `lockedPanel`, `returnPanel`, `source`, `reason`, `lastUserPanel` complexity. The new sidebar-driven navigation replaces the AI-driven panel switching:

```typescript
// Simplified workspace store
interface WorkspaceState {
  activePanel: WorkspacePanel  // which tab/section is shown in main content
}
```

The `applyUiHint` / `settleUiAction` / `toggleLock` logic is removed. Navigation is now explicit via router + sub-nav clicks.

**`athena.ts`** — Keep existing world model data fetching. Add Athena chat state:

```typescript
// Add to athena store
interface AthenaChatState {
  messages: ChatHistoryMessage[]
  loading: boolean
  chatOpen: boolean
}
```

**`worldModel.ts`** — No changes.

### 5.2 New Store: `ui.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Workspace = 'hermes' | 'athena' | 'manuscript'
export type AthenaSection =
  | 'characters' | 'locations' | 'factions' | 'items' | 'relations' | 'rules'
  | 'projection' | 'timeline' | 'knowledge'
  | 'outline' | 'storyline' | 'proposals' | 'consistency'

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const activeAthenaSection = ref<AthenaSection>('characters')
  const modals = ref<string[]>([])  // stack of open modal IDs

  function toggleSubNav() {
    subNavCollapsed.value = !subNavCollapsed.value
  }

  function openModal(id: string) {
    if (!modals.value.includes(id)) modals.value.push(id)
  }

  function closeModal(id?: string) {
    if (id) {
      modals.value = modals.value.filter(m => m !== id)
    } else {
      modals.value.pop()
    }
  }

  function setWorkspace(ws: Workspace) {
    activeWorkspace.value = ws
  }

  function setAthenaSection(section: AthenaSection) {
    activeAthenaSection.value = section
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaSection,
    modals,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaSection,
  }
})
```

---

## 6. Router Changes

### 6.1 Route Definitions

```typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import ProjectListView from '../views/ProjectListView.vue'
import HermesView from '../views/HermesView.vue'
import AthenaView from '../views/AthenaView.vue'
import ManuscriptView from '../views/ManuscriptView.vue'
import SettingsView from '../views/SettingsView.vue'

export interface AppRouteMeta {
  showSidebar: boolean
  workspace: 'hermes' | 'athena' | 'manuscript' | null
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: ProjectListView,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id',
    redirect: to => `/projects/${to.params.id}/hermes`,
  },
  {
    path: '/projects/:id/hermes',
    component: HermesView,
    meta: { showSidebar: true, workspace: 'hermes' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/athena/:section',
    component: AthenaView,
    meta: { showSidebar: true, workspace: 'athena' } satisfies AppRouteMeta,
  },
  {
    path: '/projects/:id/manuscript',
    component: ManuscriptView,
    meta: { showSidebar: true, workspace: 'manuscript' } satisfies AppRouteMeta,
  },
  {
    path: '/settings',
    component: SettingsView,
    meta: { showSidebar: false, workspace: null } satisfies AppRouteMeta,
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

### 6.2 Route Guards

The `AppShell` reads `route.meta.showSidebar` and `route.meta.workspace` to determine layout mode. No additional guards needed beyond existing project-loading logic.

When entering a project route, the existing `projectDetailHydration.ts` logic loads project data. This should be preserved as a navigation guard or called from the view's `onMounted`.

---

## 7. Migration Strategy

This is a full rewrite of the view layer. The API client (`api/client.ts`, `api/types.ts`) and store logic are preserved.

### Phase 1: Foundation
1. Create `src/styles/tokens.css` with all design tokens
2. Create `src/styles/reset.css` — minimal CSS reset
3. Create `src/styles/base.css` — base element styles using tokens (body, headings, links)
4. Update `src/style.css` to import the new style files, remove old Hermes/Athena/paper palettes
5. Update `tailwind.config` to reference token values where useful

### Phase 2: Base Components
6. Create all `components/base/` components
7. Each component is self-contained, uses design tokens, no external dependencies

### Phase 3: Layout Shell
8. Rewrite `AppShell.vue` with CSS grid layout
9. Create `TopBar.vue`, `ActivityBar.vue`, `SubNav.vue`, `ContentArea.vue`
10. Update `App.vue` to use new shell
11. Create `stores/ui.ts`

### Phase 4: Page Views (one at a time)
12. `ProjectListView.vue` — replace `ProjectList.vue` + `ProjectCard.vue` with table layout
13. `HermesView.vue` — replace `ProjectDetail.vue` + `ChatWorkspace.vue` + tab components
14. `AthenaView.vue` — replace existing `AthenaView.vue` + world components
15. `ManuscriptView.vue` — replace `ManuscriptPlaceholder.vue`
16. `SettingsView.vue` — rewrite with new form layout

### Phase 5: Shared Components
17. Create `PhaseProgress.vue`, `ChapterList.vue`, `ExportModal.vue`, `VersionsModal.vue`
18. Migrate chat components to `components/chat/`
19. Migrate Athena-specific components to `components/athena/`

### Phase 6: Cleanup
20. Delete old components: `ProjectCard.vue`, `ActionCard.vue`, `ChatSummaryCard.vue`, `ProjectSidebar.vue`, `WorkspaceTabs.vue`, `ProjectWorkspaceShell.vue`, `AppTopNav.vue`
21. Delete old tab components that are replaced
22. Remove old CSS variables (paper, hermes, athena palettes)
23. Simplify `workspace.ts` store
24. Update router to new route definitions

### Verification at Each Phase
- `npm run test:unit` — all existing tests pass (update as needed)
- `vue-tsc --noEmit` — no type errors
- `npm run build` — clean build
- Visual inspection in browser

---

## 8. Key Design Principles

1. **No decorative cards.** Use borders, spacing, and typography to create visual hierarchy. The old `ProjectCard`, `ActionCard`, `ChatSummaryCard` patterns are eliminated.

2. **Tables over grids.** Data display uses clean tables or simple lists. No card grids for entities, proposals, or project lists.

3. **Consistent spacing.** The 4px grid (`--space-1` through `--space-12`) is the only spacing system. No arbitrary pixel values.

4. **Minimal color.** Brand indigo (`#4F46E5`) appears only on:
   - Interactive elements (buttons, links, active states)
   - Activity bar accent
   - Active sub-nav items
   - User message backgrounds (light tint)
   - Assistant message left border
   Everything else is grayscale.

5. **Typography hierarchy.** Use `font-weight` and `font-size` to show importance. Never use color alone for hierarchy. Never use decorative text treatments.

6. **Progressive disclosure.** Sub-nav items expand detail in the main content area. Don't show everything at once. Athena sections load on demand.

7. **Single theme.** No dual Hermes/Athena visual themes. One consistent light minimalist theme across all workspaces. Future theme support (dark mode, etc.) is planned but not part of this redesign.

8. **Utility over decoration.** Every element serves a function. No ornamental borders, gradients, shadows, or animations beyond the minimal set defined in tokens.

---

## Appendix A: Color Reference

| Token                        | Hex       | Usage                              |
|------------------------------|-----------|------------------------------------|
| `--color-bg-primary`         | `#FAFAFA` | Page background, sub-nav bg        |
| `--color-bg-secondary`       | `#F5F5F5` | Hover states, alternating rows     |
| `--color-bg-tertiary`        | `#EFEFEF` | Neutral badge bg, disabled states  |
| `--color-bg-white`           | `#FFFFFF` | Content area, modals, cards        |
| `--color-text-primary`       | `#1A1A1A` | Body text, headings                |
| `--color-text-secondary`     | `#6B7280` | Secondary text, labels             |
| `--color-text-tertiary`      | `#9CA3AF` | Placeholders, disabled text        |
| `--color-brand`              | `#4F46E5` | Primary actions, active states     |
| `--color-brand-hover`        | `#4338CA` | Button hover                       |
| `--color-brand-active`       | `#3730A3` | Button active/pressed              |
| `--color-brand-light`        | `#EEF2FF` | User message bg, active nav item   |
| `--color-brand-subtle`       | `#E0E7FF` | Focus rings                        |
| `--color-border`             | `#E5E7EB` | All borders                        |
| `--color-success`            | `#16A34A` | Success states                     |
| `--color-warning`            | `#D97706` | Warning states                     |
| `--color-error`              | `#DC2626` | Error states, danger actions       |
| `--color-activity-bar-bg`    | `#1E1E2E` | Activity bar background            |

## Appendix B: Existing Files to Delete After Migration

```
components/ActionCard.vue
components/ChatSummaryCard.vue
components/ProjectCard.vue
components/ProjectSidebar.vue
components/WorkspaceTabs.vue
components/layout/AppTopNav.vue
components/workspace/ProjectWorkspaceShell.vue
components/workspace/AnnotationSidebar.vue
components/workspace/InspectorPanel.vue
components/tabs/OverviewTab.vue
components/tabs/SetupTab.vue
components/tabs/SetupSectionTabs.vue
components/tabs/SetupDetailModal.vue
components/tabs/SetupSummaryCard.vue
components/tabs/SetupWorldPanel.vue
components/tabs/SetupCharactersPanel.vue
components/tabs/SetupConceptPanel.vue
components/tabs/StorylineTab.vue
components/tabs/OutlineTab.vue
components/tabs/ContentTab.vue
components/tabs/TopologyTab.vue
components/tabs/VersionsTab.vue
components/tabs/PreferencesTab.vue
components/tabs/VersionDiff.vue
components/list/ProjectMatrixHero.vue
components/list/ProjectFocusRail.vue
views/ProjectList.vue          → replaced by ProjectListView.vue
views/ProjectDetail.vue        → replaced by HermesView.vue
views/ManuscriptPlaceholder.vue → replaced by ManuscriptView.vue
```

## Appendix C: Tailwind Config Alignment

Extend `tailwind.config.js` to reference design tokens for consistency:

```javascript
export default {
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          active: '#3730A3',
          light: '#EEF2FF',
          subtle: '#E0E7FF',
        },
      },
      fontFamily: {
        sans: ['var(--font-family)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
    },
  },
}
```

This allows using both CSS custom properties (in component styles) and Tailwind utilities (in templates) with consistent values.
