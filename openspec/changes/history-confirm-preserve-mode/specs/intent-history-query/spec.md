## ADDED Requirements

### Requirement: 查史确认后须保留 history_mode 进入播报
当用户对查史意图完成确认（含叶子软确认是/否、父消歧选叶、或查父确认）后，系统在调用 `speak_history`（或等价）之前 MUST 将分类阶段得到的顶层 `history_mode`（`point`|`daily`）写回执行用意图字段；若分类曾给出 `limit`，MUST 一并保留。MUST NOT 因确认中间态丢失字段而将本应为 `daily` 的查询回落为默认 `point` 点查模板。

#### Scenario: 今天几次确认后仍走 daily
- **WHEN** 分类结果为 history + read + `history_mode=daily`（如「今天喝了几次水」）
- **AND** 用户经查史软确认通过后进入播报
- **THEN** 执行用意图的 `history_mode` SHALL 为 `daily`
- **AND** 播报 SHALL 使用日汇总/紧凑聚合路径
- **AND** MUST NOT 仅用「上一次…数量为…」点查话术回答次数问

#### Scenario: 点查确认后仍为 point
- **WHEN** 分类结果 `history_mode=point` 且用户确认通过
- **THEN** 播报路径 SHALL 保持 point（或既有父塌缩点查）行为
