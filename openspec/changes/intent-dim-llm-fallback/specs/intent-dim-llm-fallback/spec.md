## ADDED Requirements

### Requirement: TYPE 维规则 miss 后小 LLM 兜底
当段类型维无可用句级 `target_type`，且规则线索无法唯一判定类型/操作时，系统 SHALL 调用 TYPE 小 LLM（提示词常量落在 `prompts/system.py`），输出须落在约定枚举（如 `feeding|history|conversation|exit` 及可选 `op`/`history_mode`）。调用 MUST 经 SSE 真流式并透出中文 reasoning。调用后 MUST 写入 `rule_gap` 且 `llm_used` 为真。MUST NOT 借本调用输出完整多 events 落库 JSON。

#### Scenario: 类型无线索走 TYPE LLM
- **WHEN** 单段输入规则无法判定 target_type/op，且无句级 history/feeding 上下文
- **THEN** 系统 SHALL 调用 TYPE 小 LLM 得到枚举内类型
- **AND** 对应缺口记录 SHALL 含 `dimension=type` 与 `llm_used=true`

### Requirement: EVENT 维阶梯末小 LLM 兜底
当段 EVENT 维经词典名、`extra_names`、短说法向量与 Go 备注反查仍未得到唯一 `event_id` 时，系统 SHALL 调用 EVENT 小 LLM：注入字典叶子候选，输出仅可为表内 `event_id`/`event_name` 或空。MUST 禁止编造 id；MUST 禁止将无把握的专名常识升格为类别事件。有唯一表内命中时 SHALL 采用该事件继续后续维；仍空时 SHALL 引导重说或无法识别，MUST NOT 回退满血 classify。调用 MUST 写 `rule_gap` 且 `llm_used=true`。

#### Scenario: 睡着了对齐睡觉
- **WHEN** 用户段为「睡着了」，词典/extra_names/向量/Go 反查均未定事件，字典含叶子「睡觉」或「睡眠」
- **THEN** EVENT 小 LLM SHALL 选出表内睡觉或睡眠对应 `event_id`
- **AND** 系统 SHALL 继续拼装确认，MUST NOT 仅返回「无法识别对应的事件「睡着」」

#### Scenario: 专名无证据不升格
- **WHEN** 段核心词为字典外专名（如 AD），且 Go 反查零命中
- **THEN** EVENT 小 LLM SHALL 返回空 `event_id`（或不选表内类别）
- **AND** 系统 SHALL NOT 将专名静默定为营养品等类别事件

### Requirement: TIME 维半命中或规则 miss 后小 LLM 兜底
当时间维出现半命中（已抽 clock 仍有未消费日/段残留）或有时间线索但规则未能产出可用 unix 时，系统 MUST NOT 用残缺规则时间免确认落库；SHALL 弃权该次规则时间后调用 TIME 小 LLM 解析 `start_time`/`end_time`（可声明无法解析）。调用 MUST 写 `rule_gap` 且 `llm_used=true`。LLM 失败或无法解析时 SHALL 保持时间为空/0，MUST NOT 回退满血 classify。

#### Scenario: 昨晚六点半命中
- **WHEN** 段含「昨晚6点」类表述，规则只吃到钟点仍残留「昨晚」
- **THEN** 系统 SHALL 弃权该残缺规则时间并调用 TIME 小 LLM
- **AND** MUST NOT 将时间落成「今天早上 6 点」类错误免确认结果

### Requirement: QTY 维规则抽空但有量线索时小 LLM 兜底
当段文本存在数量线索但规则抽取结果为空时，系统 SHALL 调用 QTY 小 LLM 产出 `quantity`（可为 null）。若完全无数量线索且事件为 number 叶 create，系统 SHALL 走缺量追问，MUST NOT 调用 QTY LLM 臆造毫升数。调用 LLM 时 MUST 写 `rule_gap` 且 `llm_used=true`。

#### Scenario: 规则未吃到的数量口语
- **WHEN** 段含数量口语而 `extract_quantity_from_text` 为空，且非「完全无量线索」
- **THEN** 系统 SHALL 调用 QTY 小 LLM 尝试填充 `quantity`

#### Scenario: 无量线索仍追问
- **WHEN** number 叶 create 且段内无任何数量线索
- **THEN** 系统 SHALL 触发缺量追问
- **AND** MUST NOT 仅靠 QTY LLM 编造数量以跳过追问
