## ADDED Requirements

### Requirement: Normalized hard-match before LLM fallback

系统在 pending 续聊解析用户自由文本时，MUST 先对文本做轻量归一化（去除首尾空白、剥离句末标点 `。．.!！?？`、英文大小写折叠），再按现有顺序尝试硬匹配：子名/`extra_names` → 序号 → 拒绝词 →（仅当 `pending.kind` 为 `leaf_confirm` 时）肯定词。硬匹配唯一命中时 MUST NOT 调用澄清 LLM。

#### Scenario: Affirmative with trailing period resolves on hard match

- **WHEN** 存在 `leaf_confirm` pending
- **AND** 用户回复归一化后等于肯定词表中的词（例如原文为「是的。」）
- **THEN** 系统 SHALL 确认当前叶子并清 pending
- **AND** SHALL NOT 调用澄清 LLM

#### Scenario: Compound affirmative misses hard match

- **WHEN** 存在 pending
- **AND** 用户回复为复合句（例如「是的，喂了30毫升」）导致硬匹配未命中
- **THEN** 系统 SHALL 调用带 pending 语境的澄清 LLM 进行解析

### Requirement: LLM clarification actions for pending replies

硬匹配未命中时，系统 MUST 调用澄清 LLM，并注入 pending 的 `kind`、澄清问句、`options` 与消歧前原话。LLM MUST 返回下列动作之一：`confirm`、`select`、`correct`、`reject`、`new_intent`、`ask_again`。系统 MUST 按动作更新会话与喂养结果，MUST NOT 在硬匹配 miss 后无条件清 pending 当新意图。

#### Scenario: Confirm with quantity overwrite

- **WHEN** pending 为 `leaf_confirm`
- **AND** LLM 返回 `confirm` 且带 `quantity`
- **THEN** 系统 SHALL 以该 quantity **覆盖** pending 原有 quantity
- **AND** SHALL 清 pending 并以该叶子作为喂养结果返回

#### Scenario: Select child option in parent disambiguation

- **WHEN** pending 为 `parent_disambiguation`
- **AND** LLM 返回 `select` 且指向 options 中某一叶子
- **THEN** 系统 SHALL 清 pending
- **AND** SHALL 以该叶子作为喂养结果（若同时带 quantity 则覆盖写入结果）

#### Scenario: Bare yes under parent disambiguation asks again

- **WHEN** pending 为 `parent_disambiguation` 且存在多个子选项
- **AND** 用户仅表达笼统肯定且未指定选项
- **THEN** 系统 SHALL 保持 pending（`ask_again`）
- **AND** SHALL NOT 落库任一子事件或父事件

#### Scenario: Off-topic becomes new intent

- **WHEN** LLM 返回 `new_intent`
- **THEN** 系统 SHALL 清 pending
- **AND** SHALL 将本句作为新意图重新执行完整意图流程

### Requirement: Correct to named leaf lands directly

当 LLM（或等价解析）判定用户否定当前猜想并改选到事件字典中的某一**叶子**事件时，系统 MUST 清旧 pending，MUST 直接以该叶子作为喂养结果落地，MUST NOT 再强制进入一轮 `leaf_confirm`。若目标为**父**事件，系统 MUST 进入父事件消歧 pending，MUST NOT 落库父事件。

#### Scenario: Correct to leaf finalizes immediately

- **WHEN** 存在澄清 pending（例如误确认「奶粉」）
- **AND** 用户回复表达纠正到另一叶子（例如「不是的，是母乳」）且该事件为叶子
- **THEN** 系统 SHALL 清旧 pending
- **AND** SHALL 直接返回该叶子的喂养意图结果
- **AND** SHALL NOT 再次发送「您是要记录「母乳」吗」类确认问句

#### Scenario: Correct to parent forces disambiguation

- **WHEN** 用户纠正目标事件为父事件
- **THEN** 系统 SHALL 清旧 pending
- **AND** SHALL 创建针对该父事件子选项的 `parent_disambiguation` pending
- **AND** SHALL NOT 以父事件落库

### Requirement: Flywheel uses pre-disambiguation utterance on final leaf

数据飞轮 MUST 仅在最终唯一叶子落地后写入；写入表达 MUST 为消歧/确认前的用户原话（`pending.original_utterance`），MUST NOT 将复合澄清回句单独作为用户表达入库。对已被用户否定的旧向量命中，系统 MUST NOT 递增其 `success_count`。父事件 MUST NOT 写入飞轮。

#### Scenario: Flywheel after correct-to-leaf

- **WHEN** 用户纠正后直接落到叶子事件
- **THEN** 系统 MAY 将消歧前原话作为该叶子的用户表达写入飞轮
- **AND** SHALL NOT 对旧错误匹配的 `matched_vector_id` 递增 `success_count`

#### Scenario: Compound reply text not stored as expression

- **WHEN** 用户以「是的，喂了30毫升」确认并落地
- **THEN** 飞轮写入的表达 SHALL 为 pending 中的消歧前原话
- **AND** SHALL NOT 以「是的，喂了30毫升」作为表达入库

### Requirement: LLM infrastructure failure keeps pending

当澄清 LLM 超时、返回非 JSON 或缺少合法动作字段时，系统 MUST 保持现有 pending，MUST 以再问（`ask_again`）响应，MUST NOT 清 pending，MUST NOT 落库。

#### Scenario: Timeout asks again

- **WHEN** 硬匹配未命中且澄清 LLM 调用超时或失败
- **THEN** 系统 SHALL 保持 pending
- **AND** SHALL 再次返回澄清问句（或等价再问提示）
- **AND** SHALL NOT 将本句当作新意图冷启动
