# Longform Scale Phase 41: 冷启动与版本列表避免加载正文

## 目标

工作区冷启动和版本历史列表只展示章节摘要与版本摘要，不应该读取章节正文或版本正文。千章项目中这两个接口会频繁触发，若携带 `chapter_contents.content` 或 `versions.content`，会把首页和版本弹窗变成无意义的大文本加载。

## 验收标准

1. `/workspace-bootstrap` 返回结构保持不变。
2. `/workspace-bootstrap` 的章节摘要查询不选择 `chapter_contents.content`。
3. `/workspace-bootstrap` 的版本摘要查询不选择 `versions.content`。
4. `/versions` 列表查询不选择 `versions.content`。
5. 相关测试和完整验证通过。
