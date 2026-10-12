## 1. 定轨：删除害人本地短路

- [x] 1.1 从 `resolve_type` 删除「查史强线索→强制 read+record」整块
- [x] 1.2 删除「OP=read 且 source 未命中时因 infer 填 record」分支；source 未命中改走 OP LLM
- [x] 1.3 保留 exit/delete/end；仅在 read_source 已为 record 后用 infer 填 history_mode
- [x] 1.4 `SEGMENT_TYPE_LLM_PROMPT` 补「下一次…什么时候→predict+next」及禁止仅因「什么时候」判 record

## 2. 数量：规则→飞轮→LLM

- [x] 2.1 调整 `resolve_segment` QTY 顺序为规则→飞轮→LLM→回写
- [x] 2.2 收紧 `has_quantity_clue` / `_QTY_CLUE_RE`（禁止裸「一」）
- [x] 2.3 read 轨跳过数量维（不调 QTY LLM、不写 qty 飞轮）

## 3. 备注飞轮

- [x] 3.1 新增 `remark_cue_store`（整段 document，payload.remark 可空）+ admin 路由
- [x] 3.2 接线：C/U 事件已定后 飞轮→备注 LLM→回写；已有别名备注可跳过
- [x] 3.3 read 轨跳过备注维

## 4. 验收

- [ ] 4.1 手工：下一次喂养是什么时候 → read+predict，不得答「上一次…」
- [ ] 4.2 手工：同句二次无备注 LLM、无 QTY LLM
- [ ] 4.3 手工：吃了差不多一百二 → 二次可 qty 飞轮跳过 QTY LLM
- [ ] 4.4（可选兄弟仓）Hub 备注飞轮页
