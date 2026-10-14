## ADDED Requirements

### Requirement: 时间相对配方飞轮对各 CRUD 轨同等读写
当段需要相对时间解析（含钟点或相对口语，且非「仅日词已由本地规则解决」）时，系统 SHALL 对 create、read、update、delete 各轨同等检索与回写时间相对配方飞轮（`feeding_time_cues` 或等价）。飞轮载荷 MUST 为可校验相对配方；MUST NOT 以绝对 Unix 作为主缓存载荷。点查且 `ignore_time_range` 为真时，系统 MAY 跳过时间窗解析与飞轮。

#### Scenario: read 轨可命中飞轮
- **WHEN** 用户以相对时间口语查史（非仅日词短路），且飞轮中已有同段或高置信匹配的相对配方
- **THEN** 系统 SHALL 物化该配方得到当次 unix 窗
- **AND** MUST NOT 仅因轨为 read 而跳过飞轮检索

#### Scenario: 冷路径 LLM 后各轨可回写
- **WHEN** 任意 CRUD 轨上 TIME 小 LLM 产出合法可物化相对配方
- **THEN** 系统 SHALL 允许将该配方写入时间飞轮（document 为约定段文）
- **AND** MUST NOT 仅因轨为 read 而禁止回写

### Requirement: 日词或飞轮命中时 TIME 维禁止调 LLM
当本地日词规则已填窗，或时间飞轮高置信命中并成功物化时，该段 TIME 维 MUST NOT 再调用 TIME 小 LLM。TIME LLM 仅在上述均未解决时作为冷路径；不保证全部同义改写免 LLM。

#### Scenario: 飞轮命中免 LLM
- **WHEN** 段相对时间飞轮检索命中且物化成功
- **THEN** 系统 MUST NOT 再调用 TIME 小 LLM 解析该段时间
