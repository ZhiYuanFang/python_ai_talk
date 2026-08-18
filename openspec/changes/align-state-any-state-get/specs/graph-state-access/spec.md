## ADDED Requirements

### Requirement: 整包 State 入参类型为 Any
凡读取 LangGraph 图执行 State 整包的共享公开函数与图节点（含 clinic / tip / care_alert / shared 跨图辅助），其 `state`（或等价整包入参）类型注解 MUST 为 `Any`（或未来等价的结构子类型 Protocol）。MUST NOT 以 `Dict[str, Any]` 作为上述入口的唯一类型注解，以免与 Pydantic State 主路径脱节。

#### Scenario: shared 捷径门禁签名
- **WHEN** 查看 `is_block_fast_path`（或等价 Q&A 捷径强制跳过判定）的函数签名
- **THEN** 其 State 入参注解 SHALL 为 `Any`
- **AND** SHALL NOT 仅为 `Dict[str, Any]`

#### Scenario: clinic Q&A 检索节点签名
- **WHEN** 查看 `search_qa_fast_path`（或等价节点）的函数签名
- **THEN** 其 State 入参注解 SHALL 为 `Any`

### Requirement: 读 State 字段经 state_get
上述入口读取 State 字段时 MUST 使用 `app.shared.graphs.state_patch.state_get`（或同模块对外等价封装）。MUST NOT 假定 State 为 Mapping 而调用 `.get`，MUST NOT 以 `key in state` 作为 Pydantic State 上的主路径存在性判断。

#### Scenario: 强制跳过捷径读标志位
- **WHEN** `is_block_fast_path` 读取 `force_needs_history` / `skip_knowledge` / `block_fast_path` / 问句文本
- **THEN** SHALL 经 `state_get` 取得各字段
- **AND** 传入 Pydantic `ClinicState` 实例时 SHALL 能正确读到属性值（不得因缺少 `.get` 而失败）

#### Scenario: 史接地推导读字段
- **WHEN** `derive_history_grounded`（或等价）由 clinic 终态推导是否史接地
- **THEN** 对 `qa_hit` / `force_needs_history` / `needs_history` 的读取 SHALL 经 `state_get`

#### Scenario: care-alert 月龄预置
- **WHEN** `resolve_baby_age` 判断请求侧预置 `baby_age_months`
- **THEN** SHALL 经 `state_get` 读取该字段（值非 `None` 时作为兜底）
- **AND** MUST NOT 依赖 `"baby_age_months" in state` 作为主路径

### Requirement: 遗留线性步进合并兼容模型 State
若保留 `progressive_thinking`（或等价「线性步骤表 + 就地合并」遗留路径），其对 State 的合并 MUST 使用 `apply_state_patch`（或同等不擦除未提及字段的合并），MUST NOT 假定可对 State 调用 `dict.update`。

#### Scenario: 遗留步进合并补丁
- **WHEN** 遗留线性步进执行某节点并得到字段补丁 dict
- **THEN** 合并进当前 State SHALL 经 `apply_state_patch`（或同等语义）
- **AND** 当 State 为 Pydantic 模型时 SHALL NOT 因调用 `.update` 而失败
