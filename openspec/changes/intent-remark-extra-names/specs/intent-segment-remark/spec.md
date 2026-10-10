## ADDED Requirements

### Requirement: extra_names 作类别实例别名
事件字典字段 `extra_names` SHALL 表示该事件的近义或**实例词**（属于该事件类别的具体物名）。段 EVENT 维在正式名词典匹配未命中时，MUST 对段文本（及可选轻归一后的核心词）与全表各事件 `extra_names[]` 做**精确**比较。唯一命中时 MUST 将 `event_id`/`event_name` 定为该字典事件，并将命中别名词写入该段意图项的 `remark`。系统 MUST NOT 为此新建独立别名表或 Hub 别名 CRUD；维护沿用既有字典 `extraNames` 编辑能力。

#### Scenario: 菠菜定为辅食并备注
- **WHEN** 辅食事件的 `extra_names` 含「菠菜」，用户段文本为「菠菜」或等价仅含该实例词的记事句，且正式名词典未先命中
- **THEN** 该段 SHALL 解析为字典事件「辅食」（或该事件正式名）及对应 `event_id`
- **AND** 该段意图项的 `remark` SHALL 为「菠菜」
- **AND** MUST NOT 因「菠菜」≠「辅食」字面而调用满血多 events 分类或建新事件类型

#### Scenario: 一词多事件须消歧
- **WHEN** 同一别名词出现在两个及以上不同事件的 `extra_names` 中且段文本精确命中该词
- **THEN** 系统 SHALL 发起消歧（pending）列出这些字典事件
- **AND** SHALL NOT 静默任选其一落库

### Requirement: EVENT miss 后段级 Go 备注反查
当段 EVENT 维经词典名、`extra_names`、短说法向量均未得到可用 `event_id` 时，系统 SHALL 以该段原文或剥离钟点/量词后的核心词作为 `remark` 关键字，调用与既有备注反查相同的 Go filter（本设备、近窗、小 limit、空 `eventIds`）做模糊反查。唯一叶命中时 MUST 写入该叶子 `event_id`/`event_name`，并将用于反查的关键字写入 `remark`。多叶命中 MUST 消歧；零命中 MUST 按段失败引导重说（或等价无法识别），MUST NOT 新建事件类型，MUST NOT 用常识升格为某字典类别而跳过反查。

#### Scenario: AD 反查营养品
- **WHEN** 段文本核心词为「AD」，词典名与 `extra_names` 与短说法向量均未定事件，近窗备注含 AD 的记录均落在营养品
- **THEN** 段级备注反查后该段 SHALL 使用字典「营养品」与对应 `event_id`，且 `remark` 为 AD（或所用关键字）
- **AND** SHALL NOT 在反查前把全量 history 注入分句或满血分类 prompt

#### Scenario: 反查零命中
- **WHEN** 段 EVENT 阶梯走至 Go 反查且近窗无命中
- **THEN** 系统 SHALL 反馈无法识别或引导重说该段
- **AND** MUST NOT 设置新建事件类型并落库该专名

### Requirement: 全事件允许 LLM 明细备注
任意已定事件的段，在 EVENT 维完成后，系统 SHALL 调用专用小 LLM（提示词常量落在 `prompts/system.py`）从段原文抽取自由明细备注；输出可为空字符串。MUST NOT 用规则硬截「有点黄」类描述作为唯一备注来源。若 `extra_names` 或 Go 反查已写入非空 `remark`，且 LLM 返回非空且与已有不同，SHALL 合并（默认：已有在前，中文逗号拼接，去包含重复）；若 LLM 返回空则保留已有 `remark`。拼装后的 `remark` MUST 进入确认话术与 batch 落库字段。

#### Scenario: 尿尿有点黄
- **WHEN** 段文本为「尿尿了，这次有点黄」且事件已定为尿尿（或等价字典名）
- **THEN** 明细 LLM 抽取后该段 `remark` SHALL 含「有点黄」类明细（可带归一后的短句）
- **AND** 确认与落库 payload SHALL 带出该 `remark`

#### Scenario: 别名备注不被空 LLM 冲掉
- **WHEN** 段经 `extra_names` 命中已写入 `remark=菠菜`，且明细 LLM 返回空
- **THEN** 该段最终 `remark` SHALL 仍为「菠菜」
