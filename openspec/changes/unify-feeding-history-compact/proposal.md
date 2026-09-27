## Why

值得留意、成长轨迹、clinic 与 intent 日汇总各自用不同方式把喂养史塞进提示或播报（compact / 原 JSON / slim+薄按日汇总），导致「优化聚合形态」必须改多处。拉史节点已共享，但聚合算法仍分叉。需要先把值得留意现用聚合提成 `app/shared` 唯一实现，多 Agent 同形态消费，再在后续变更里只改一处算法。

## What Changes

- 将 `care_alert` 现有「日历日 × 事件名」紧凑聚合（含可选 `eventName=eventId` legend）上提到 `app/shared/`，算法本变更**不优化**。
- **care_alert**：改调共享函数；继续消费 `history_text` + `legend`（Flutter 仍要求 item 带合法 `eventId`）。
- **growth_trajectory**：生成（及需要史摘要的规划侧）改注入同一套 `history_text`；`prior_feedback` / 问答 / 画像不变；**不**强制注入 legend。
- **clinic**：有史归纳路径改用同一套聚合文本（汇总题不再依赖 `build_daily_history_summary`）；点查相对时间 / slim 明细策略以 design 为准收敛到共享聚合或保留点查裁剪。
- **intent** `history_mode=daily`：播报改用共享 `history_text`（不向用户念 legend）；`point` 模板不动。
- **删除** `build_daily_history_summary`，不留死代码。
- 各 Agent **窗长 / limit / DataRequirement 各自保留**（如留意约 2 天、轨迹约 7 天）；本变更不统一窗口。
- 不改 Flutter / Go 契约；不改分类是否产出 `history_mode=daily`。

## Capabilities

### New Capabilities

- `shared-feeding-history-compact`: 共享喂养史紧凑聚合 API 与多 Agent 消费约定（形态统一、窗长分治、legend 可选）。

### Modified Capabilities

- `nl-history-via-clinic`: clinic 向 LLM 注入喂养史时，归纳/有史路径改为共享紧凑聚合形态（不再以「仅字段裁剪 JSON + 薄按日汇总」为唯一形态）。

## Impact

- 代码：`app/care_alert/graphs/nodes/prompts/history_compact.py` → `app/shared/`；`care_alert` / `growth_trajectory` / `clinic` / `feeding.speak_history` 消费点；删除 `history_prompt_fields.build_daily_history_summary`。
- API：无对外 HTTP 契约变更；care-alert items 仍须带 `eventId`。
- 后续：下一次变更可只优化 shared 聚合算法，多 Agent 共同受益。
