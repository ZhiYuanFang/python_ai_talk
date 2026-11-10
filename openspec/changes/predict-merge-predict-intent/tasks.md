## 1. 读模型

- [x] 1.1 imminent pending 解析：可选 `parentEventName`（trim；空=无父）；忽略 `expectLeafTitle`；名称优先 `title`
- [x] 1.2 active-eta 解析：`expectEndAt` 省略/null/0 视为无结束；命中项后走进行中降级话术；**不**读 `parentEventName`

## 2. 匹配与播报

- [x] 2.1 next：先按 eventId（leaf/root）匹配；未命中再用根权威名对齐 `parentEventName`；多条仍按 nextAt 择优
- [x] 2.2 active：身份匹配保持 leaf/root/eventId；有正结束用既有模板；无正结束 MUST 播进行中且 MUST NOT 编造结束钟点
- [x] 2.3 手工回归：旧根级 pending、根名→子 pending、有结束 active、无结束 active、子 eventId 直命中

## 3. 文档

- [x] 3.1 相关注释 / 对端说明统一为三仓字段名 `parentEventName`（仅 pending；对齐 Go `predict-merge-predict-contract`）
