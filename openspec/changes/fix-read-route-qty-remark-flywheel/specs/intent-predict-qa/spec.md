## ADDED Requirements

### Requirement: 下一次类问句进 R·predict
当用户询问下一次/下次喂养或护理事件「是什么时候」或「还有多久」类预期时，系统 SHALL 判定为 read 且 read_source=predict（并补齐合法 predict_channel 与 time_answer），MUST NOT 落入查史 record 播报「上一次…」。

#### Scenario: 下一次喂养是什么时候
- **WHEN** 用户输入「下一次喂养是什么时候」且无强制覆盖的确认态
- **THEN** 系统 SHALL 采用 read + read_source=predict
- **AND** SHALL 走预测播报路径（如 next 通道）
- **AND** MUST NOT 以查史点查模板回答「上一次喂养…」

### Requirement: OP 提示须区分下次与上次
OP 轨小 LLM 的系统约束 SHALL 明示：「下一次/下次…什么时候」归 predict；「上一次/上次/睡了多久了」归 record；禁止仅因「什么时候」判 record。

#### Scenario: 提示词含下次示例
- **WHEN** 系统组装 OP 轨 system 提示
- **THEN** 提示中 SHALL 包含下一次类 → predict 的纠偏说明
