## ADDED Requirements

### Requirement: 按 document 精确查询九个飞轮

系统 MUST 提供 `GET /v1/admin/cues/by-document`。查询参数 `document` 在去除首尾空白后 MUST 与条目的 document 精确相等才算命中。系统 MUST 查询且只查询这九个集合：`feeding_op_cues`、`feeding_intents`、`feeding_qty_cues`、`feeding_time_cues`、`feeding_remark_cues`、`feeding_read_source_cues`、`feeding_predict_cues`、`feeding_history_speak_cues`、`feeding_locate_cues`。每条命中 MUST 包含维度键、集合名、向量 id、document 与 payload。系统 MUST NOT 把该接口实现为向量近邻检索。

#### Scenario: 同一原文命中多个维度

- **WHEN** 调用方传入一句已同时写入 OP 轨与备注飞轮的原文
- **THEN** 响应 MUST 包含这两条命中，且维度键分别为 `op` 与 `remark`

#### Scenario: 空白查询被拒绝

- **WHEN** `document` 去除空白后为空
- **THEN** 系统 MUST 拒绝该请求，且 MUST NOT 扫描集合

#### Scenario: 任一集合失败则整次失败

- **WHEN** 九个集合中有一个读取失败
- **THEN** 系统 MUST 让本次查询失败，且 MUST NOT 只返回其余集合的命中
