---
name: openspec-archive-change
description: >-
  将 OpenSpec changes 合并到版本基线并删除 change 目录。
  在用户执行 /opsx-archive、archive vX.Y.Z、收版、合并基线时使用。
license: MIT
compatibility: Requires openspec CLI and scripts/sync_specs_to_version.py
metadata:
  author: openspec
  version: "1.1"
  generatedBy: "1.3.0"
---

# OpenSpec 收版（本仓库约定，覆盖上游 dated-archive）

本仓库 **不** 使用 `openspec/changes/archive/YYYY-MM-DD-<name>/` 按变更移动归档。

权威基线是 **`openspec/specs/vX.Y.Z.md`**。收版 = 合并全部 change delta → 写版本基线 → **删除** `openspec/changes/*`（跳过 `archive/`）。

## 输入

- **版本号**（推荐）：`/opsx-archive v0.0.2`、`archive v0.1.0`、`收版到 v1.0.0`
- 若只给 change 名而无版本：先列出活跃 change，并 **追问目标版本号**（如基于当前基线建议下一 patch）
- 若无输入：`openspec list --json` 提示有哪些 change，并要求用户给出 **目标版本号**

版本标签统一为 `v` + semver（缺 `v` 时脚本会补上）。

## 步骤（强制）

### 1. 读取全局规范

读取并遵守：

1. `openspec/project.md`（基线参考约定 + 归档约定）
2. 当前基线文件（`project.md` 中写明的 `openspec/specs/v*.md`）

### 2. 预警（不阻塞）

```bash
openspec list --json
```

- 列出 in-progress / 未完成任务的 change 数量与名称
- **默认不阻塞**（除非用户明确要求「只合并 complete」）
- 摘要中保留 Warnings

### 3. 执行收版（默认删除 changes）

```bash
python scripts/sync_specs_to_version.py <version> --remove-changes
```

- 从最新（或 `--base`）`openspec/specs/v*.md` 起步，应用 `openspec/changes/*/specs/**/spec.md`
- 写出 `openspec/specs/<version>.md`
- **删除** 全部 change 目录（保留 `archive/` 若存在）
- **禁止** 创建 dated archive 目录，除非用户显式要求保留 change（`--keep-changes` / 「不要删 change」）

仅当用户显式要求保留 change 时：

```bash
python scripts/sync_specs_to_version.py <version>
```

### 4. 更新基线版本引用

收版成功后 **必须** 更新 `openspec/project.md`「OpenSpec 基线参考约定」中所有旧版本号为新版本（路径与正文中的 `vX.Y.Z`）。

同步检查并更新（若存在）：

- `AGENTS.md` 中的基线路径
- `.cursor/skills/openspec/SKILL.md` 中的基线路径

### 5. 摘要输出

```
## Archive Complete

**Version:** vX.Y.Z
**Baseline:** openspec/specs/vX.Y.Z.md (N capabilities, M deltas)
**Changes removed:** yes (K)   # 或 no（用户要求保留）
**Specs:** ✓ Synced to version baseline (no dated archive)

### Warnings
- …（如有 in-progress change 被一并合并）
```

## Guardrails

- 用户说 **`archive v版本号`** / **`/opsx-archive v版本号`** → 直接按本 skill 收版，**不要**再走「选单个 change → mv 到 archive/」流程
- 默认 **`--remove-changes`**
- 不要把 delta 同步成 `openspec/specs/<capability>/spec.md` 树；本仓库权威产物是 **`openspec/specs/v*.md`**
- 收版后 `openspec list` 应为空（在删除 changes 的情况下）
- 合并冲突（同名 Requirement）以 change 目录 mtime 顺序由脚本处理；勿手工改脚本逻辑 unless 用户要求
