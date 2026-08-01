## Context

`route_after_classify` 将 `suggest` / `conversation` 导向 `call_clinic_agent`；建议生成已用 `clinic_answer`。`generate_response` 仍挂在 history 短链末端，但其内部 `if target_type == "suggest"` 与 `suggest_answer.py` 在正常图执行下不可达。

## Goals / Non-Goals

**Goals:**

- 删除 `suggest_answer.py` 与 `generate_response` 中的 suggest 分支
- 保留并明确 `generate_response` = history 同步回答

**Non-Goals:**

- 不改 intent 路由边
- 不改 `clinic_answer` / tip 提示词
- 不做喂养记录字段裁剪（另 change）
- 不删除 `TargetType.SUGGEST` 枚举（分类仍需要该标签以便路由到 clinic agent）

## Decisions

### 1. 删文件 + 瘦节点，而非保留空分支

- **选择**：删除 `suggest_answer.py`；`generate_response` 只调用 `history_answer`
- **理由**：消除「建议还用旧模板」的误导
- **备选**：仅加注释标记 deprecated → 死代码仍在

### 2. 模块 docstring 写明职责

- **选择**：更新 `generate_response` 模块/函数说明为「仅 history」
- **理由**：防止后人再加 suggest 分支而不知已有 clinic agent

## Risks / Trade-offs

- [外部脚本直接 import suggest_answer] → 仓库内 grep 仅 generate_response 引用；风险低
- [误删 generate_response 整文件] → 明确 Non-Goal；history 短链会断

## Migration Plan

1. 删除后跑 intent history / suggest 各一条：suggest 仍进 clinic agent；history 仍出回答
2. 回滚：从 git 恢复两文件即可

## Open Questions

- 无
