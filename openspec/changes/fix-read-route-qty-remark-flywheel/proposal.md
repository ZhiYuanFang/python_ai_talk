## Why

「下一次喂养是什么时候」被本地「什么时候→查史 point」规则强制打成 `read+record`，答成「上一次…」，且未进 R·predict。同时读路径仍无条件跑备注/数量 LLM（数量线索还对「下一次」里的「一」假阳性）。需去掉害人的**定轨**本地规则，保留有效规则，并为数量/备注补齐与其它维同构的飞轮，使重复问句少打无关 LLM。

## What Changes

- **BREAKING（定轨）**：删除 `resolve_type` 中用 `infer_expected_history_mode`（含「什么时候」）**强制** `read+record` 的短路；删除「OP=read 且 source 未命中时用 infer 填 record」。主判轨改为 OP 飞轮 → R·source/predict 飞轮 → OP 小 LLM。
- **保留有效规则**：exit / delete / 睡醒→end 等；`infer_expected_history_mode` 仅用于 **record 已定后** 的 `history_mode`（point|daily）及缓存冲突门闩，不拍 `record|predict`。
- OP 提示词补例：「下一次…什么时候」→ `read` + `predict` + `next` + clock/remain。
- **数量维**：改为本地规则 → 整段飞轮补缺 → 真线索才 QTY LLM → 整段回写；收紧线索正则（禁止裸「一」假阳性）。
- **备注维**：新增整段飞轮（可缓存空 remark）；别名已有可跳过；LLM 成功回写。
- **读路径门闩**：`read`（record|predict）MUST NOT 跑备注维与数量维。

## Capabilities

### New Capabilities

- `intent-qty-remark-flywheel`：数量（规则→飞轮→LLM→回写）与备注整段飞轮；读路径跳过；QTY 线索收紧

### Modified Capabilities

- `intent-dim-resolve`：定轨不再依赖查史词表短路；record|predict 仅由飞轮/OP LLM 判定
- `intent-predict-qa`：含「下一次…什么时候」类须进 R·predict，不得因「什么时候」落查史
- `intent-flywheel-layers`：数量顺序改为规则优先再飞轮；备注层纳入分层清单

## Impact

- Python：`segment_multidim.resolve_type`、`history_mode_cues` 调用点、`SEGMENT_TYPE_LLM_PROMPT`、qty/remark 解析与新 `remark_cue_store`（及 admin）、QTY 线索、读路径跳过
- 存量：用户自行清理已污染的 history_speak/OP 等错条目；本 change 不强制清库脚本
- Go / Hub：无强制；Hub 备注飞轮页可标兄弟仓可选任务
