## MODIFIED Requirements

### Requirement: TYPE 维规则 miss 后小 LLM 兜底
当段类型维无可用句级 `target_type`，且类型关键字向量库未命中时，系统 SHALL 调用 TYPE 小 LLM（提示词常量落在 `prompts/system.py`）。输出 MUST 落在约定枚举（`feeding|history|conversation|exit` 及可选 `op`/`history_mode`），并 MUST 含布尔 `need_confirm` 与字符串数组 `keywords`。调用 MUST 经 SSE 真流式并透出中文 reasoning。调用后 MUST NOT 写入 `rule_gap`（类型飞轮自更新）。MUST NOT 借本调用输出完整多 events 落库 JSON。MUST NOT 因弱喂养词短路而跳过本调用。

#### Scenario: 类型库未命中走 TYPE LLM
- **WHEN** 单段输入类型关键字库未命中，且无句级 history/feeding 上下文
- **THEN** 系统 SHALL 调用 TYPE 小 LLM 得到枚举内类型与 `need_confirm`、`keywords`
- **AND** MUST NOT 因此写入 `dimension=type` 的规则缺口

### Requirement: EVENT 维阶梯末小 LLM 兜底
当段 EVENT 维经词典名、`extra_names`、短说法向量与 Go 备注反查仍未得到唯一 `event_id` 时，系统 SHALL 调用 EVENT 小 LLM：注入字典叶子候选，输出仅可为表内 `event_id`/`event_name` 或空。MUST 禁止编造 id；MUST 禁止将无把握的专名常识升格为类别事件。有唯一表内命中时 SHALL 采用该事件继续后续维；仍空时 SHALL 引导重说或无法识别，MUST NOT 回退满血 classify。调用 MUST NOT 写入 `rule_gap`（事件种子由短说法库与 Hub 事件向量管理，不进缺口箱）。

#### Scenario: 睡着了对齐睡觉
- **WHEN** 用户段为「睡着了」，词典/extra_names/向量/Go 反查均未定事件，字典含叶子「睡觉」或「睡眠」
- **THEN** EVENT 小 LLM SHALL 选出表内睡觉或睡眠对应 `event_id`
- **AND** MUST NOT 因此写入 `dimension=event` 规则缺口

#### Scenario: 专名无证据不升格
- **WHEN** 段核心词为字典外专名（如 AD），且 Go 反查零命中
- **THEN** EVENT 小 LLM SHALL 返回空 `event_id`（或不选表内类别）
- **AND** 系统 SHALL NOT 将专名静默定为营养品等类别事件

### Requirement: TIME 维半命中或规则 miss 后小 LLM 兜底
当时间维出现半命中（已抽 clock 仍有未消费日/段残留）或有时间线索但规则未能产出可用 unix 时，系统 MUST NOT 用残缺规则时间免确认落库；SHALL 弃权该次规则时间后调用 TIME 小 LLM 解析 `start_time`/`end_time`（可声明无法解析）。调用 MUST 写 `rule_gap` 且 `llm_used=true`（供 Hub 整理 TIME 规则）。LLM 失败或无法解析时 SHALL 保持时间为空/0，MUST NOT 回退满血 classify。

#### Scenario: 昨晚六点半命中
- **WHEN** 段含「昨晚6点」类表述，规则只吃到钟点仍残留「昨晚」
- **THEN** 系统 SHALL 弃权该残缺规则时间并调用 TIME 小 LLM
- **AND** 缺口记录 SHALL 含 `dimension=time` 与 `llm_used=true`

### Requirement: QTY 维规则抽空但有量线索时小 LLM 兜底
当段文本存在数量线索但规则抽取结果为空时，系统 SHALL 调用 QTY 小 LLM 产出 `quantity`（可为 null）。若完全无数量线索且事件为 number 叶 create，系统 SHALL 走缺量追问，MUST NOT 调用 QTY LLM 臆造毫升数。调用 QTY LLM 时 MUST 写 `rule_gap` 且 `llm_used=true`。缺量追问本身 MUST NOT 写入规则缺口（或等价不得出现在 Hub 默认 TIME/QTY LLM 缺口列表）。

#### Scenario: 规则未吃到的数量口语
- **WHEN** 段含数量口语而规则抽取为空，且非「完全无量线索」
- **THEN** 系统 SHALL 调用 QTY 小 LLM 尝试填充 `quantity`
- **AND** 缺口记录 SHALL 含 `dimension=quantity` 与 `llm_used=true`

#### Scenario: 无量线索仍追问
- **WHEN** number 叶 create 且段内无任何数量线索
- **THEN** 系统 SHALL 触发缺量追问
- **AND** MUST NOT 仅靠 QTY LLM 编造数量以跳过追问
- **AND** MUST NOT 因缺量追问向 Hub 默认缺口列表灌入噪音条目
