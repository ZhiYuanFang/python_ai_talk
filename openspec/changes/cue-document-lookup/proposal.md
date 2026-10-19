## Why

运维要按一整句 `document` 查看它落在哪些喂养飞轮里，并删掉某一条。现在每个集合只有分页列表，Hub 无法一次对上原文。

## What Changes

- 新增 `GET /v1/admin/cues/by-document?document=`。对门户上的 9 个飞轮集合做 trim 后的原文精确匹配，返回维度键、集合名、向量 id、document、payload。
- 覆盖：`feeding_op_cues`、`feeding_intents`、`feeding_qty_cues`、`feeding_time_cues`、`feeding_remark_cues`、`feeding_read_source_cues`、`feeding_predict_cues`、`feeding_history_speak_cues`、`feeding_locate_cues`。
- 不查已停热路径的类型向量，不查规则缺口与 miss-inbox。
- `document` 为空时拒绝，不扫库。任一集合读取失败则整次查询失败。
- 不新增删除接口；删除仍用各集合现有的按 id 删除。
- 不做语义近邻检索。

## Capabilities

### New Capabilities

- `cue-document-lookup`：按整段 document 精确列出九个飞轮集合中的命中条目。

### Modified Capabilities

- （无）

## Impact

- `app/api/routes` 新增聚合查询路由；各 cue store 增加按原文过滤的读取，避免为一次查询把分页列表反复拉全量到 Go。
- 兄弟仓 `go_ai_talk` 变更 `hub-intent-document-lookup` 消费该接口并在 Hub 上删除。
