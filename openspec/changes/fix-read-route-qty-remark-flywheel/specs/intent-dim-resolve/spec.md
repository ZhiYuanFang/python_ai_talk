## ADDED Requirements

### Requirement: 定轨禁止查史词表短路
系统 MUST NOT 仅因原文含「什么时候」或 `infer_expected_history_mode` 返回 point|daily，而将段强制判定为 read 且 read_source=record。`record|predict` MUST 由 OP 整段飞轮、R·source 飞轮或 OP 小 LLM 判定。

#### Scenario: 下一次什么时候不因词表进 record
- **WHEN** 用户段为「下一次喂养是什么时候」且无 read_source=record 的合法整段飞轮命中
- **THEN** 系统 MUST NOT 仅因含「什么时候」直接采用 read+record
- **AND** SHALL 继续走 source/predict 飞轮或 OP 小 LLM 判定

### Requirement: 有效本地规则可保留
系统 MAY 保留高精度本地规则用于 exit、delete、计时结束（如睡醒→update/end）。在 read_source 已确定为 record 之后，系统 MAY 使用 `infer_expected_history_mode` 仅填充 history_mode（point|daily），MUST NOT 用该推断改写 read_source。

#### Scenario: record 已定后可填 history_mode
- **WHEN** 飞轮或 OP LLM 已判定 read_source=record
- **AND** 原文含「上次」
- **THEN** 系统 MAY 将 history_mode 设为 point
- **AND** MUST NOT 将 read_source 改为 predict
