## MODIFIED Requirements

### Requirement: Session keyed by device_no
系统 SHALL 以 `device_no` 作为陪伴会话的唯一主键，在 Python 侧持久化 **clinic** 对话状态。系统 MUST NOT 再要求 tip 与 clinic 共享会话（tip Agent 已删除）。

#### Scenario: Clinic session isolated by device
- **WHEN** 两个不同的 `device_no` 分别产生 clinic 对话
- **THEN** 各自会话互不可见

#### Scenario: Tip no longer writes companion session
- **WHEN** 系统已删除 tip Agent
- **THEN** MUST NOT 再存在 tip 开场写入 companion 会话的主路径

### Requirement: Persist session in Redis with 7-day TTL
系统 SHALL 将会话存储在 Redis 中，TTL 为 7 天，并在成功写入会话后滑动续期。

#### Scenario: Session survives process restart within TTL
- **WHEN** 会话已写入且未超过 7 天无成功写入
- **THEN** Python 进程重启后仍可按 `device_no` 读回该会话

#### Scenario: Expired session starts fresh
- **WHEN** 会话超过 TTL 未获续期
- **THEN** 下一次 clinic 请求按空会话处理并创建新会话数据

### Requirement: Clinic appends real user and assistant turns
系统 SHALL 在 clinic 流式（或非流式）回答成功生成后，向该 `device_no` 会话追加一轮：user 为本次 `question`，assistant 为本次回答全文，并更新待判定建议元数据。

#### Scenario: Clinic appends turn
- **WHEN** 用户以某 `device_no` 调用 clinic 并成功得到回答
- **THEN** 会话追加本轮 user/assistant，且总轮数不超过配置上限

### Requirement: Inject recent turns into generation context
系统 SHALL 在 clinic 生成面向用户的回答时，将会话中近轮对话注入提示上下文；喂养历史数据需求判断 SHALL NOT 将聊天轮次当作喂养事件历史。

#### Scenario: Clinic prompt includes prior clinic turns
- **WHEN** clinic 为已有历史轮次的 `device_no` 生成回答
- **THEN** 供 LLM 使用的上下文包含近期 clinic 轮次（受轮数窗口限制）

## REMOVED Requirements

### Requirement: Tip opening writes a full turn
**Reason**: tip Agent 删除，不再写入合成开场轮。
**Migration**: 见 `retire-tip-agent`；Clinic 仅追加真实用户问句轮次。

### Requirement: Keep at most five turns
**Reason**: 轮数上限以现行配置为准，本变更用 clinic-only 语义重述；原「tip 与 clinic 共享五轮」场景废止。
**Migration**: 保留「最多 N 轮」实现配置；规格以 clinic 会话为准（见 MODIFIED 注入与追加要求）。
