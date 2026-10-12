## ADDED Requirements

### Requirement: 时间飞轮仅缓存相对配方
系统 SHALL 支持时间整段飞轮（如 `feeding_time_cues`）：`document` 为段完整原文，payload 为相对时间配方（含 kind 与 points / duration_minutes 等约定字段）。payload MUST NOT 以绝对 `start_time`/`end_time` Unix 秒作为主缓存内容。系统 MUST NOT 实现「仅同日历日有效的绝对 Unix TTL」作为本维主策略。

#### Scenario: 回写不含绝对 Unix 主字段
- **WHEN** TIME 小 LLM 产出合法相对配方并被采用
- **THEN** 系统 SHALL 以段整句为 document 写入时间飞轮
- **AND** 写入 payload MUST 为相对配方
- **AND** MUST NOT 仅以绝对 Unix 对作为该条权威载荷

### Requirement: 规则优先再飞轮再 LLM
时间解析 MUST 按顺序：本地规则产出可用起止则采用；否则检索时间飞轮，命中合法配方后按当前 Asia/Shanghai 物化为 Unix；仍未得且存在时间线索时 MAY 调用 TIME 小 LLM。仅当 LLM 产出可校验的相对配方时 SHALL 整段回写飞轮；仅有 Unix、无合法配方时当次 MAY 用于落库但 MUST NOT 回写时间飞轮。

#### Scenario: 跨日同句跳过 TIME LLM
- **WHEN** 「昨晚八点喂了」首次经 TIME LLM 写入合法相对配方
- **AND** 次日再次相同段原文且规则仍未完整抽出
- **THEN** 系统 SHALL 可从时间飞轮命中配方并物化为该次「昨晚 20:00」对应 Unix
- **AND** MUST NOT 为此再调用 TIME 小 LLM

#### Scenario: 仅 Unix 不写飞轮
- **WHEN** TIME LLM 仅返回可用 Unix 且无合法相对配方
- **THEN** 系统 MAY 将该 Unix 用于当次落库
- **AND** MUST NOT 将该结果写入时间飞轮

### Requirement: 读路径跳过时间飞轮
当段顶层轨为 `read`（含 read_source 为 record 或 predict）时，系统 MUST NOT 检索或写入时间飞轮以解析落库钟点。

#### Scenario: 预测问句不跑时间飞轮
- **WHEN** 段判定为 read 且 read_source=predict
- **THEN** 解析路径 MUST NOT 为该段读写时间飞轮
