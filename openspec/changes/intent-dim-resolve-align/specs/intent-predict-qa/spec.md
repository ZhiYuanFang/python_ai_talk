## ADDED Requirements

### Requirement: 预测两维经独立飞轮解析
当目标为 read 且 read_source=predict（或遗留顶层 predict）时，系统 SHALL 通过独立预测维解析（整段飞轮优先，其次预测维小 LLM）得到 predict_channel 与 time_answer，MUST NOT 仅依赖 OP 轨分类 LLM 作为唯一来源。两维非法时 SHALL 需确认或降级，MUST NOT 静默进入半残预测播报。

#### Scenario: 飞轮未命中则预测维 LLM
- **WHEN** 用户说「还有多久醒来」且预测飞轮未命中
- **THEN** 系统 SHALL 可调用预测维小 LLM 补齐 channel 与 time_answer
- **AND** 成功采用后 SHALL 以整段原文回写预测飞轮

#### Scenario: 禁止回落上一次用时
- **WHEN** 预测播报失败或无匹配 ETA/imminent
- **THEN** 系统 MUST NOT 念「上一次…用时」类查史话术作为预测答
