## ADDED Requirements

### Requirement: 仅日词无钟点须本地填窗且跳过 TIME LLM
当段文本含日历日词（至少支持今天/昨天/前天/本周或实现已支持的等价词）、且无可解析钟点/相对钟点线索，并需要时间窗时，系统 SHALL 在段 TIME 维使用本地日词规则（如 `parse_day_word_window` / `enum_to_unix` 语义，Asia/Shanghai）填入起止 unix。该路径 MUST NOT 调用 TIME 小 LLM，MUST NOT 因此写入 dimension=time 的规则缺口记录。

#### Scenario: 昨天几次不走 TIME LLM
- **WHEN** 用户说「昨天拉了几次屎」（或语义等价的 daily 查史）且段需时间窗
- **THEN** 系统 SHALL 以本地规则得到「昨天」日历日对应 unix 窗
- **AND** MUST NOT 为该段调用 TIME 小 LLM
- **AND** MUST NOT 仅因本句写入 time 规则缺口

#### Scenario: 日词加钟点不吃整日捷径
- **WHEN** 段同时含日词与可解析钟点（如「昨天晚上八点」）
- **THEN** 系统 MUST NOT 仅用整日窗短路而忽略钟点
- **AND** SHALL 走钟点/相对时间解析路径（规则、飞轮或必要时 LLM）
