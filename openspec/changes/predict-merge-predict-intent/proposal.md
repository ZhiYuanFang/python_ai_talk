## Why

Go `predict-merge-predict-contract` 已落地新预测契约：imminent pending 可选 `parentEventName`（字典根权威名）、全链路丢弃 `expectLeafTitle`、active-eta 允许省略/null/0 的 `expectEndAt`。非合并根下 pending 按**子** `eventId` 落条；用户常说根名（如「吃奶」），意图若仍只按 `eventId` 对齐或仍依赖 leafTitle，会 miss 子 pending，或在无结束 ETA 上捏造钟点。须与 Go 字段名与读语义对齐后再改代码。

## What Changes

- **imminent/pending 读路径**：匹配主键仍为条目 `eventId`；未命中且用户指向根名时，MUST 可用可选 `parentEventName` 反推命中子项（缺省兼容旧包）；播报名用 `title` 或目录；**MUST NOT** 依赖 `expectLeafTitle`。
- **active-eta 读路径**：省略 / null / 非正（含 `0`）的 `expectEndAt` MUST 仍可识别进行中；播报 MUST NOT 捏造结束钟点。active-eta **不**读 `parentEventName`（Go 未投影该字段）。
- **字段名锁定**：与 Go/Flutter 一致为 **`parentEventName`**（字符串根名，非 `parentEventId`）。
- **非目标**：不实现 mergePredict 算法；不改 Go 写路径；不改 Flutter UI；**不**接入 `GET .../latest-by-event`（语音「上一次」仍走既有 history point）。

## Capabilities

### New Capabilities

- `intent-predict-merge-dimension-read`：意图预测通道对新 pending/active 可选字段、根名反推与空结束的读取/降级规则。

### Modified Capabilities

- 既有 `intent-predict` / imminent·active 读 Go 的匹配与播报（去掉 leafTitle 依赖；补 `parentEventName` 反推；容忍无结束 active）。

## Impact

- `http_client` / `predict_qa` / speak_predict 路径；OpenSpec 基线中「leafTitle / 强制结束 / parentEventId」相关表述。
- 对端权威：Go `predict-merge-predict-contract`（已完成）；Flutter `predict-merge-predict-dimension`。
