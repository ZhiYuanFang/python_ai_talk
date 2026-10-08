## ADDED Requirements

### Requirement: 分类提示区分开表与闭合补记
意图分类 system 提示 MUST 说明：计时叶子在用户给出「时长」或「从某点到某点」时，create 须填写 `start_time` 与 `end_time`（闭合）；仅「开始/正在」且无时长、无结束点时 `end_time` 为 0 或不填以开表。

#### Scenario: 提示含闭合补记约定
- **WHEN** 加载意图分类 system 提示
- **THEN** 文案 SHALL 含计时闭合补记与开表的区分说明（或等价示例）
