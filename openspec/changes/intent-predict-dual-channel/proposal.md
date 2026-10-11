## Why

用户问「还有多久睡觉」「大概还有多久醒来」时，意图被打成 `history`+点查，答成「上一次睡眠…用时…」。产品要的是**预测问答**：进行中结束用 active-eta，下次发生用 imminent；Go Redis 已有数据（active-eta 已有 Python internal GET；imminent 仅 App PUT/推送，缺 Python 读）。须新增 `target_type=predict` 与分维，经 TYPE LLM/飞轮判定，禁止回落查史用时。

## What Changes

- 新增意图 `target_type=predict`；独立维 **`predict_channel`**（`active`|`next`）与 **`time_answer`**（`clock`|`remain`），**不合并**。
- TYPE 小 LLM 与 `feeding_type_cues` 飞轮载荷扩展上述字段；**不以本地词表/正则**判定 channel/time_answer 或「多久→history」。
- 新图节点（如 `speak_predict`）：按 channel 调 Go；按 time_answer 播报；remain 超时文案为「已经过了预计时间」；无数据明确降级，**MUST NOT** 回落「上一次…用时」。
- `http_client`：复用 active-eta GET；新增 imminent pending internal GET（依赖孪生 Go）。
- 孪生：`go_ai_talk` 暴露 `GET /voice/internal/api/predict/imminent/pending?deviceNo=`（字段对齐 App PUT events）；Flutter 侧以现有同步为准，本仓不改算法。
- 查史 `history`+`speak_history` / 已落地的「仅进行中」ETA 增强可保留，与 predict 路径分轨。

## Capabilities

### New Capabilities

- `intent-predict-qa`：预测意图分型、双通道拉数与按语境播报（含飞轮字段与降级）。

### Modified Capabilities

- （基线无独立 capability 树名时以本 change spec 为准；TYPE 飞轮/段多维行为变更写入本 capability 的 Requirement，实现时对照 `type-keyword-flywheel` 已落地代码。）

## Impact

- 代码：`TargetType`、TYPE LLM 提示与解析、`type_cue_store`、段多维组装、intent 图路由、`speak_predict`、`http_client`/settings（voice+密钥已有则复用）。
- 兄弟仓：Go voice imminent internal GET；Hub/admin 类型向量若展示载荷须认新字段。
- 不新建测试文件。
