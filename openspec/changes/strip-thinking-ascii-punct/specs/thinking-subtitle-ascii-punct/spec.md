## ADDED Requirements

### Requirement: 思考字幕去掉英文标点

系统经 `ThinkingSentenceCrRewriter` 向客户端推送的 LLM reasoning 增量 MUST 去掉英文标点。MUST 去掉的字符至少包括 `,` `.` `(` `)` `>`，以及 `-` `<` `;` `/` `\` `|` `=` `+` `~` `@` `%` `^` `&` `!` `?`。剔除后仅剩空白的增量 MUST NOT 推送。中文、数字、空白、段首 `\r`、中文句界（`。！？`）与中文标点 MUST 保留。回答正文与图节点固定编排字幕 MUST NOT 经此剔除。

#### Scenario: 英文思考削掉字母后不再剩标点

- **WHEN** 模型思考增量为 `(event_id) -> next, done.`
- **THEN** 对外 thinking 事件的 content MUST NOT 含有 `,` `.` `(` `)` `>` `-` 或拉丁字母
- **THEN** 该增量在字母与上述英文标点都去掉后若已无可见字符，MUST NOT 推送 thinking 事件

#### Scenario: 中文思考保留句界与中文标点

- **WHEN** 模型思考增量含有中文、中文逗号与中文句号，例如 `看一下，配方奶。`
- **THEN** 对外 thinking 的 content MUST 保留这些汉字、`，` 与 `。`
- **THEN** 句号结束之后的下一句 MUST 仍可在段首带 `\r`

#### Scenario: 回答正文不改写

- **WHEN** 同一轮 LLM 的回答正文含有英文标点或括号
- **THEN** 回答 content MUST 按模型原文聚合，MUST NOT 被思考字幕剔除规则改写
