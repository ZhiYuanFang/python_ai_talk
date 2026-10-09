## Context

`intent-history-mode-daily` 已让分类产出 `history_mode`，叶子确认路径（`postprocess_feeding_result` → `create_leaf_confirm_pending`）与 `try_handle_pending` 的叶子 restore 已透传该字段。但查史主路径的软确认走 `create_history_confirm_response`，创建 pending 时未写入 `history_mode`/`limit`；父消歧工厂与查父确认拼 fields 分支同样缺失。结果：LLM 写 `daily`，确认后 `speak_history` 仍 `(history_mode or "point")` → 点查模板。

## Goals / Non-Goals

**Goals:**

- 查史软确认 pending 持久化分类给出的 `history_mode`、`limit`。
- 父消歧 pending 与查父确认执行前回填同样字段。
- 确认后 `speak_history` 看到的 mode 与分类一致（daily 走紧凑汇总）。

**Non-Goals:**

- 不改分类提示、不改启发纠偏逻辑。
- 不改确认话术、不改 Go filter API。
- 不解决 number 叶「几次」口语是否显式说「N次」（可另开 change）。
- 不强制清意图缓存；新写入缓存仍带 mode 即可。

## Decisions

### D1: 在现有 pending 字段上补齐写入，不新增协议

- **选择**：`PendingClarification` 已有 `history_mode`/`limit`；缺口是工厂与调用方未赋值。
- **备选**：确认后再跑一次分类 — 浪费且可能漂移，否决。

### D2: 三处对称修补

| 缺口 | 修补 |
|------|------|
| `create_history_confirm_response` | 调 `create_leaf_confirm_pending` 时传入 `fields.history_mode` / `limit` |
| `create_parent_disambiguation_pending`（及 remark/try_parent 调用链） | 增加可选参数并写入 pending；查史进入父消歧时从 intent 带入 |
| `try_handle_pending` 查父确认拼 `fields`（约 215–249 行） | 与叶子 restore 相同：合法则写回 `history_mode`/`limit` |

### D3: 空值语义

- pending 上 mode 为空 → 确认后仍可不写，speak 保持默认 point（与现网兼容）。
- 仅当分类给出 `point|daily` 时强制保留，避免把空串当成合法 mode。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 旧进程内存里已有无 mode 的 pending | 重启/过期后自然消失；仅影响进行中会话 |
| 父路径调用点多、漏传一处 | tasks 按工厂 + 所有创建入口列清单；中文注释标明「查史必带」 |
| 只修 soft confirm 仍漏父路径 | D2 显式覆盖查父分支 |

## Migration Plan

1. 部署本仓 Python 即可；无 DB / Go 迁移。
2. 回滚：还原上述传参即可；行为退回「确认后默认 point」。

## Open Questions

（无；范围已由复现路径钉死。）
