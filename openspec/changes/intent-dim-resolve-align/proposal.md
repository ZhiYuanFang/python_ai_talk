## Why

`intent-crud-other-reframe` 已落地六轨与 OP/数量/R·source 飞轮，但各维判定未共用同一套「规则→整段飞轮→维 LLM→回写/缺口」方法；R·predict、U/D 定位缺独立飞轮，R·record 播报仍以短关键词为主，与「整段 document、热路径少 LLM」目标冲突。现拍板：**history_speak 硬切整段**，并补齐缺层、统一维判定形态。

## What Changes

- **统一维判定方法**：各飞轮维（OP、事件、数量、R·source、R·record 播报、R·predict、U/D 定位）显式 `resolve_*`，共享同一判定形状；时间维保持「规则→TIME LLM→rule_gap」、禁止时间飞轮。
- **BREAKING（history_speak）**：查史播报飞轮 **硬切整段原文** 为 document；停用短关键词热路径与 `add_keywords` 主策略；清空/停用旧短词种子，改灌整句（如「睡了多久了」）。
- **补齐缺层**：新增（或演进）`feeding_predict_cues`（channel + time_answer）、`feeding_locate_cues`（定位策略码，不存 historyId）；predict 两维不再仅塞在 OP LLM。
- **事件冷路径**：LLM/定事件成功后按整段回写事件飞轮（与 qty/OP 同构），减少重复 LLM。
- **种子与 admin**：整句种子脚本；既有 admin 对齐整段契约；Hub 页标兄弟仓（可选任务）。

## Capabilities

### New Capabilities

- `intent-dim-resolve`: 各维判定统一方法（规则可选→整段飞轮→维 LLM→回写或 rule_gap）；缺层补齐清单的行为契约

### Modified Capabilities

- `intent-history-speak-flywheel`: 硬切整段 document；禁止短关键词主命中与短词回写
- `intent-flywheel-layers`: 落实 R·predict / U/D 定位为独立整段飞轮；与统一 resolve 对齐（相对 reframe 增量）
- `intent-predict-qa`: 预测两维经独立飞轮热路径，命中可跳过对应 LLM

## Impact

- Python：`history_speak_cue_store` / `history_speak_policy`、`segment_multidim`、`speak_history` / `speak_predict`、新 predict/locate store + admin、种子脚本、提示词
- 存量短词 `feeding_history_speak_cues`：硬切后旧短词条目失效或需清空
- Go：一期仍 batch；无强制 API 变更
- Hub：播报/分层飞轮页对齐整段（兄弟仓任务）
