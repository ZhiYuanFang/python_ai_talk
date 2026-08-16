## ADDED Requirements

### Requirement: 读意图支持 top_k
每个 `op=read` 子项 SHALL 可包含整数 `top_k`（缺省 **1**；实现 MUST 将大于上限的值钳制到上限，上限 MUST ≤ 5）。当用户语义为「前两次 / 最近两次」等时，分类 MUST 将对应子项 `top_k` 设为 2（或用户明确的次数，不超过上限）。「上一次 / 最近一次」MUST 为 `top_k=1`，并可与 `ignore_time_range=true` 同时使用。

#### Scenario: 前两次分类为 top_k=2
- **WHEN** 用户输入「前两次喂奶分别在什么时候」且分类成功
- **THEN** 对应 `op=read` 子项的 `top_k` MUST 为 2

#### Scenario: 上一次仍为 top_k=1
- **WHEN** 用户输入「上一次睡觉是什么时候」且分类成功
- **THEN** 对应 `op=read` 子项的 `top_k` MUST 为 1

### Requirement: 拉史按发生时间取前 k 条
正式点查拉史时，系统 SHALL 按事件发生时间（`start_time`）**倒序**取得至多 `top_k` 条记录用于播报。系统 MUST NOT 在 `top_k>1` 时仍只保留每事件名称的第一条/最近一条用于唯一播报句。Go filter（或客户端稳定排序过渡）MUST 保证时间序语义；目标态 filter MUST `ORDER BY start_time DESC`（或等价）。

#### Scenario: top_k=2 播报两条时间
- **WHEN** `top_k=2` 且 filter 返回至少两条同事件记录
- **THEN** 播报 content MUST 分别给出两次发生时间（或等价分条说明）
- **AND** MUST NOT 仅输出单次「上一次…」句式作为唯一结果

#### Scenario: 不足 k 条如实说明
- **WHEN** `top_k=2` 但仅查到 1 条记录
- **THEN** 播报 MUST 说明已找到的一次时间
- **AND** MUST 明示未找到第二次（或等价话术）

### Requirement: 点查模板支持多条列举
查记录模板播报在 `top_k>1` 时 SHALL 使用列举口吻（例如最近一次…；再上一次…），MUST NOT 调用历史答题 LLM 生成自由答史。

#### Scenario: 模板列举无 LLM 答史
- **WHEN** `top_k=2` 的点查成功取到两条记录
- **THEN** content MUST 由模板拼接
- **AND** MUST NOT 为该答史再调用生成式历史答题 LLM
