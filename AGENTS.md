# 仓库级 AI 执行约定

## 权威文档

编写或修改代码、OpenSpec 产物前，**必须**阅读：

1. **[openspec/project.md](openspec/project.md)** — 工程约束全文（代码注释、模块分离、OpenSpec 基线、归档等）。
2. **[openspec/specs/v0.0.1.md](openspec/specs/v0.0.1.md)** — 当前合并行为基线（Requirement / Scenario 验收）。

OpenSpec CLI 制品生成时亦须对照 `openspec/project.md`；细则以 project.md 为准，本文仅摘要高频 MUST。

## 代码与模块

- **禁止**自动生成测试文件；用户明确要求时例外。
- 业务代码须有详细**中文**注释（文件/类/方法/关键行）。
- 按业务模块分离（`feeding` / `clinic` / `tip` / `shared` / `config`）；禁止 feeding↔clinic 直接互引。

## OpenSpec 工作流

- 新变更前对照 **`openspec/specs/v0.0.1.md`**；行为变更须有 spec delta。
- **收版快捷方式**：用户说 `archive vX.Y.Z` / `/opsx-archive vX.Y.Z` 时，执行：

  ```bash
  python scripts/sync_specs_to_version.py vX.Y.Z --remove-changes
  ```

  然后更新 `openspec/project.md`（及本文、`.cursor/skills/openspec/SKILL.md`）中的基线版本号。
- **默认删除** `openspec/changes/*`；**不**创建 dated `archive/YYYY-MM-DD-*` 目录。
- 细则见 **`openspec/project.md`**「OpenSpec 基线参考约定」「OpenSpec 归档约定」。
- 工作流技能：`.cursor/skills/openspec/SKILL.md`、`.cursor/skills/openspec-archive-change/SKILL.md`。
