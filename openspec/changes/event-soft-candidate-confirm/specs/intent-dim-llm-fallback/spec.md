## MODIFIED Requirements

### Requirement: EVENT 维阶梯末小 LLM 兜底
当段 EVENT 维经词典名、`extra_names`、短说法向量与 Go 备注反查仍未得到唯一 `event_id` 时，系统 SHALL 调用 EVENT 小 LLM：注入字典叶子候选，输出表内 `candidates`（0..N 条，每项含表内 `event_id`/`event_name`；实现可设上限如 3）。MUST 禁止编造 id；MUST 禁止新建事件类型。有 ≥1 条合法表内候选时，系统 SHALL 进入软确认或消歧（见 `event-soft-candidate-confirm`），MUST NOT 将候选静默定为最终事件并执行。候选为空时 SHALL 引导重说或无法识别，MUST NOT 回退满血 classify。提示词 MUST NOT 再以「禁止猜营养品」或「专名无把握必须空」禁止模型给出表内软候选；专名升格若发生 MUST 仅作为待确认候选。调用 MUST 经 SSE 真流式并透出中文 reasoning（对外 SSE 路径）。

#### Scenario: 睡着了对齐睡觉
- **WHEN** 用户段为「睡着了」，词典/extra_names/向量/Go 反查均未定事件，字典含叶子「睡觉」或「睡眠」
- **THEN** EVENT 小 LLM SHALL 选出表内睡觉或睡眠对应候选
- **AND** 系统 SHALL 继续拼装确认或执行路径（高置信唯一表内口语对齐时可按既有硬采用策略），MUST NOT 仅返回「无法识别对应的事件「睡着」」

#### Scenario: 专名可软候选须确认
- **WHEN** 段核心词为字典外专名（如 AD），且 Go 反查零命中，EVENT 小 LLM 将表内「营养品」列入候选
- **THEN** 系统 SHALL 对该候选走确认或消歧，MUST NOT 静默定为营养品并落库或播报
- **AND** MUST NOT 因「禁止猜营养品」类提示而强制跳过软候选、直接无法识别（若模型给出了合法表内候选）

#### Scenario: 午饭表内软候选
- **WHEN** 段含「午饭」等口语，梯子未硬命中，字典含「辅食」等近义叶
- **THEN** EVENT 小 LLM SHALL 可输出「辅食」等表内候选
- **AND** 系统 SHALL 进入软确认或消歧，而非仅因禁止猜测而硬空失败
