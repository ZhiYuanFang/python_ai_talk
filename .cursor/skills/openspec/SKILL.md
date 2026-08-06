---
name: openspec
description: >-
  指导基于规格的变更提案、增量规格、校验与归档，配合 OpenSpec CLI 与本仓库目录结构。
  在用户提到 OpenSpec、变更提案、规格增量、openspec validate、规划功能、破坏性变更、
  架构调整，或要求创建/应用规格与变更、收版 archive v版本号时使用。
---

# OpenSpec（本仓库）

## 权威文档

编写或修改 OpenSpec 产物、或实现变更代码前，请先阅读：

1. **[openspec/project.md](../../openspec/project.md)** — 工程约束全文。
2. **[AGENTS.md](../../AGENTS.md)** — 仓库级 AI 执行约定（摘要 + 链接）。
3. **[openspec/specs/v0.0.1.md](../../openspec/specs/v0.0.1.md)** — 当前合并行为基线。

## 何时走 OpenSpec

**创建变更**（提案 + 增量 + `tasks.md`）适用于：新增能力、破坏性 API/架构变更、或改变行为的优化。

**可跳过提案**的情况：恢复规格所描述行为的缺陷修复、错别字、非破坏性依赖升级、仅配置调整——除非需求模糊。

## 助手工作流（精简）

### 编写或实现之前

- 阅读 **`openspec/project.md`** 与 **`AGENTS.md`**。
- 运行 `openspec list` 了解上下文。
- 对照 **`openspec/specs/v0.0.1.md`**；检查 `openspec/changes/` 是否已有重叠变更。

### 创建变更

1. 选取唯一的动词开头 **change-id**（kebab-case）。
2. 在 `openspec/changes/<change-id>/` 下搭建：`proposal.md`、`tasks.md`、可选 `design.md`，以及 `specs/**` 增量。
3. 每条 Requirement 至少包含一个 `#### Scenario:` 块；正文须含 **SHALL** 或 **MUST**。
4. 分享前运行 **`openspec validate <change-id> --strict`**。

### 实现已批准的变更

按顺序阅读 `proposal.md` → `design.md`（若有）→ `tasks.md`；完成任务后勾选 `tasks.md`。

### 收版（/opsx-archive v版本号）

用户只需提供版本号，例如：`/opsx-archive v0.0.2` 或 `archive v0.0.2`。

```bash
python scripts/sync_specs_to_version.py <version> --remove-changes
```

- 合并全部 `openspec/changes/*/specs/**` 到 `openspec/specs/<version>.md`
- **默认删除**全部 change 目录（不创建 dated archive）
- 收版后更新 **`openspec/project.md`**（及 AGENTS.md / 本 skill）中的基线版本引用
- 摘要须说明 **Changes removed: yes/no**

详细步骤见 `.cursor/skills/openspec-archive-change/SKILL.md`。

## CLI 速查

```bash
openspec list
openspec status --change "<name>" --json
openspec validate <id> --strict
openspec instructions apply --change "<name>" --json
python scripts/sync_specs_to_version.py vX.Y.Z --remove-changes
```

## 延伸阅读

- 命令：`/opsx-propose`、`/opsx-apply`、`/opsx-archive`、`/opsx-explore`
- 技能：`.cursor/skills/openspec-propose/`、`.cursor/skills/openspec-apply-change/`、`.cursor/skills/openspec-archive-change/`
