## ADDED Requirements

### Requirement: Amount and duration aspects SHALL skip the clock template

When `read_source` is `predict` and `predict_aspect` is `amount` or `duration`, `speak_predict` MUST NOT answer with the Go active-eta or imminent clock/remain template, even if a matching `expectEndAt` or `nextAt` exists. Those turns MUST enter the existing cold path (local algorithm or appointment snapshot, then the predict fallback LLM). The fallback prompt MUST tell the model to answer the asked aspect and MUST NOT switch the answer to a clock time. When `predict_aspect` is `when` or absent, the existing hot-path template behavior MUST remain.

问用量或用时时，即使已有下次时间点，也 MUST NOT 念「预计几点」。何时题的热路径模板保持不变。

#### Scenario: Formula amount does not speak next clock

- **WHEN** 「这次配方奶要吃多少」已定为 `predict_aspect=amount`，且 imminent 里存在该事件的 `nextAt`
- **THEN** 回答 MUST NOT 使用「预计约 HH:mm 开始」模板，MUST 进入冷路径并按用量回答

#### Scenario: When-question still uses the hot path

- **WHEN** `predict_aspect=when` 且 Go 锚点匹配成功
- **THEN** 播报 MUST 仍用现有 clock/remain 模板，MUST NOT 改走用量或用时
