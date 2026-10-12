## ADDED Requirements

### Requirement: 数量层规则先于飞轮
分层飞轮中的数量层 MUST 在本地规则未能抽出 quantity 后再检索飞轮；MUST NOT 以飞轮结果覆盖已成功的规则抽出值（除非另行产品规定校验冲突，本期不做冲突改写）。

#### Scenario: 规则已抽出则不用飞轮改写
- **WHEN** 规则从「吃了120毫升」抽出 quantity=120
- **THEN** 系统 SHALL 采用 120
- **AND** MUST NOT 用飞轮中的其它 quantity 覆盖该值

### Requirement: 备注层纳入分层飞轮
系统 SHALL 将备注整段飞轮视为独立层（与 OP、事件、数量、R·source 等隔离）。该层仅服务写库相关轨（create/update 等），read 轨 MUST NOT 依赖或写入该层。

#### Scenario: 备注层与 OP 隔离
- **WHEN** 向备注飞轮写入或检索
- **THEN** document MUST 为段整句
- **AND** 不得写入 op_rail 或 read_source 作为该层权威载荷
