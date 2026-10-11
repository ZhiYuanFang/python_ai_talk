## ADDED Requirements

### Requirement: TYPE 维关键字向量为类型飞轮单位
系统 SHALL 使用独立于事件短说法库的 Chroma 集合（如 `feeding_type_cues`）存储 **类型关键字 → TYPE 结果**：`document` 为短关键字或短说法，metadata/payload 至少含 `target_type`、`op`，history 时含 `history_mode`。系统 MUST NOT 将该集合用于整包 multi-events 免确认回放，MUST NOT 与 `feeding_intents` 事件短说法混存同一匹配空间。

#### Scenario: 命中关键字只定类型
- **WHEN** 段文本与库内关键字「多久了」相似度不低于实现所定门槛（默认与事件短说法门槛一致，如 0.72）
- **THEN** 系统 SHALL 采用该条 payload 的 `target_type`/`op`/`history_mode` 填入 TYPE 维
- **AND** SHALL NOT 因该命中而回放历史整包 multi-events 载荷

### Requirement: TYPE 冷路径同次 LLM 产出确认标志与关键字
当类型关键字库未命中且无可用句级 `target_type` 时，系统 SHALL 调用 TYPE 小 LLM（提示词在 `prompts/system.py`），同一次输出 MUST 包含：枚举内 `target_type`、可选 `op`/`history_mode`、布尔 `need_confirm`、字符串数组 `keywords`。调用 MUST 经 SSE 真流式并透出中文 reasoning。MUST NOT 借本调用输出完整多 events 落库 JSON。MUST NOT 仅因句内含「睡」「吃」等弱喂养词而跳过本调用并默认 create。

#### Scenario: 睡了多久了走 TYPE LLM
- **WHEN** 用户输入「睡了多久了」且类型关键字库未命中
- **THEN** 系统 SHALL 调用 TYPE 小 LLM
- **AND** MUST NOT 因段内含「睡」而直接判定 feeding+create

#### Scenario: 同次带出 keywords
- **WHEN** TYPE 小 LLM 返回可用类型结果
- **THEN** 响应 JSON SHALL 含 `keywords` 数组（可为空）与 `need_confirm`

### Requirement: 高置信写入与确认后写入
当 TYPE LLM 返回 `need_confirm=false` 时，系统 SHALL 采用其类型结果继续后续维，并 SHALL 将非空 `keywords` 逐条写入类型关键字库（同一 payload）。当 `need_confirm=true` 时，系统 MUST 先完成用户确认，确认通过后 MUST 再按 `keywords`（或确认所采纳结果对应关键字）写入类型库。写入 MUST NOT 使用未拆分的复合整句作为唯一 document。

#### Scenario: 高置信直灌关键字
- **WHEN** TYPE LLM 对「睡了多久了」给出 history+read 且 `need_confirm=false` 与 keywords 含「多久了」
- **THEN** 系统 SHALL 将「多久了」写入类型库并关联 history+read
- **AND** MUST NOT 要求用户再确认类型后才写入

#### Scenario: 需确认则确认后写
- **WHEN** TYPE LLM 返回 `need_confirm=true`
- **THEN** 系统 SHALL 向用户确认类型意图
- **AND** 仅在用户确认后 SHALL 写入 keywords 到类型库

### Requirement: SHAPE 并入 TYPE
系统 MUST NOT 再将 SHAPE 作为独立于 TYPE 的必经小 LLM 维。计时开表/结束/查史等形态 SHALL 由 TYPE 飞轮命中或 TYPE LLM 的 `op`（及等价 action）表达。独立 `dimension=shape` 的规则缺口写入 MUST NOT 再作为主路径行为。

#### Scenario: 睡醒了由 TYPE 定 end
- **WHEN** 「睡醒了」经 TYPE 飞轮或 TYPE LLM 定为 `op=end`（或等价结束）
- **THEN** 后续拼装与执行 SHALL 走结束计时路径
- **AND** MUST NOT 要求再调用独立 SHAPE 小 LLM 才能结束
