## ADDED Requirements

### Requirement: 成长建议接口
系统 SHALL 在意图分析接口中支持成长建议场景，当识别到成长建议意图时，生成个性化成长建议。

#### Scenario: 生成喂养建议
- **WHEN** 用户输入"宝宝最近食量怎么样"，意图分析结果为 suggest
- **THEN** 系统根据历史喂养记录生成个性化喂养建议

#### Scenario: 生成睡眠建议
- **WHEN** 用户输入"宝宝睡眠情况如何"，意图分析结果为 suggest
- **THEN** 系统根据历史睡眠记录生成个性化睡眠建议

### Requirement: 历史数据聚合
系统 SHALL 根据用户问题聚合历史数据，计算相关统计指标。

#### Scenario: 计算日均喂养量
- **WHEN** 用户询问"最近一周宝宝平均每天吃多少"
- **THEN** 系统计算最近 7 天的日均喂养量

#### Scenario: 计算喂养频率
- **WHEN** 用户询问"宝宝一天喂几次"
- **THEN** 系统计算日均喂养次数

### Requirement: LLM 建议生成
系统 SHALL 使用 LLM 生成自然语言建议，结合历史数据和宝宝画像。

#### Scenario: 生成详细建议
- **WHEN** 系统完成历史数据聚合
- **THEN** 系统将聚合数据和宝宝画像作为 context，调用 LLM 生成自然语言建议

#### Scenario: 建议包含行动项
- **WHEN** LLM 生成建议
- **THEN** 建议中包含具体的行动建议和注意事项