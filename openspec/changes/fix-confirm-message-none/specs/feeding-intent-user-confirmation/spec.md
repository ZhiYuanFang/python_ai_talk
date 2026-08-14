## ADDED Requirements

### Requirement: 用户确认后执行 MUST NOT 因 confirm_message 为 null 失败
当用户对喂养/历史意图确认请求作出肯定回复，系统继续执行落库或历史 CRUD 时，意图结果上的 `confirm_message` 若为空语义，MUST 以空字符串表示或可被归一为空字符串；系统 MUST NOT 因该字段为 JSON/`None` null 导致 Pydantic 校验失败或 HTTP 500。

#### Scenario: 确认结束睡眠后执行历史更新
- **WHEN** 首轮意图为 `op=update`、`action=end`、事件为睡眠且 `need_confirm=True`，用户随后回复「是的」并携带有效 `conversation_id`
- **THEN** 系统 SHALL 进入确认后执行路径（含历史 CRUD 或等价落库）
- **AND** MUST NOT 因 `confirm_message` 为 `None` 抛出 `ValidationError`
- **AND** 流式或非流式意图分析接口 MUST NOT 因此返回 500

#### Scenario: 叶子确认结果清确认态
- **WHEN** 确认管线构造已落地唯一叶子且不再需要确认的意图字典（如 `leaf_intent_result` 或等价）
- **THEN** `need_confirm` SHALL 为假
- **AND** `confirm_message` MUST 为可序列化的字符串（空串合法），MUST NOT 为 `None`
