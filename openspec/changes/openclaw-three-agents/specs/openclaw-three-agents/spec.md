## ADDED Requirements

### Requirement: 三 Agent 可拆边界
系统 SHALL 仅保留三个智能体能力面：**Intent**（喂养意图 CRUD 与查记录）、**Clinic**（陪伴聊天）、**Care Alert**（护理留意卡片）。系统 MUST NOT 将上述三者合并为单一 Agent。对外售卖时三者 MUST 可独立启用；Intent MUST 可在无 Clinic/Care Alert 的情况下单独交付。

#### Scenario: Intent 单卖不含写外陪伴
- **WHEN** 仅启用 Intent Agent
- **THEN** 系统 MUST 提供确认分轮与历史写/读 tool
- **AND** MUST NOT 要求部署 Clinic 或 Care Alert 才能完成落库

### Requirement: Clinic 与 Care Alert 禁止写历史
Clinic Agent 与 Care Alert Agent MUST NOT 暴露或调用历史 create/update/delete/end 类业务 tool。Clinic SHALL 仅用于聊天读信息；Care Alert SHALL 仅产出卡片列表类结构化信息。

#### Scenario: Clinic 无写 tool
- **WHEN** 配置 Clinic Agent 的 tool 目录
- **THEN** 目录 MUST NOT 包含 history.create、history.update、history.delete、history.end

#### Scenario: Care Alert 输出卡片
- **WHEN** 调用 Care Alert 分析
- **THEN** 响应 MUST 为可映射客户端的卡片/items 列表语义
- **AND** MUST NOT 经该 Agent 写入喂养历史

### Requirement: 外侧持有 conversation_id
分轮会话标识 `conversation_id` SHALL 由调用方（外侧接入层）持有并在续轮请求中回传。Agent 运行时 SHALL 按该 id 恢复 pending/确认态。系统 MUST NOT 要求对方业务 history API 实现 pending 状态机。

#### Scenario: 确认续轮带回 cid
- **WHEN** Intent 首轮返回 need_confirm 与 conversation_id
- **AND** 调用方携带同一 conversation_id 与用户确认话术再次请求
- **THEN** 系统 MUST 能解析 pending 并继续执行（含写 tool）

### Requirement: 编排不以 LangGraph 为权威
系统 SHALL 使用 OpenClaw 就绪的 Agent 运行时（或等价 LLM+tool 循环）编排 Intent/Clinic/Care Alert。系统 MUST NOT 再以 LangGraph `StateGraph` 作为上述三能力的编排权威实现。

#### Scenario: 无 StateGraph 依赖意图主路径
- **WHEN** 执行 Intent 冷启动分析主路径
- **THEN** 实现 MUST NOT 调用 `langgraph.graph.StateGraph` 编译图作为编排入口
