## ADDED Requirements

### Requirement: Progressive thinking excludes tip

渐进/编排 thinking 约定适用于存活图（clinic、intent、care-alert、growth-trajectory 等）。系统 MUST NOT 再要求 tip 数据准备阶段的逐步 thinking。

#### Scenario: Tip thinking not required

- **WHEN** tip 模块已删除
- **THEN** 规格 MUST NOT 强制 `/v1/tip/stream` 的逐步 thinking 行为
