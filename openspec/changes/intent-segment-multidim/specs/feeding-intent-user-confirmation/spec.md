## ADDED Requirements

### Requirement: number 叶 create 缺量须追问
当段级结果为 `create` 且目标叶子事件类型为 number（或等价需 quantity 的计量叶），且 quantity 为空时，系统 MUST 先向用户追问数量，MUST NOT 在数量未补齐时进入总确认或落库。

#### Scenario: 喝了配方奶无毫升
- **WHEN** 多维命中配方奶/瓶喂类 number 叶且未抽到 quantity
- **THEN** 系统 SHALL 返回数量追问
- **AND** SHALL NOT 直接生成「确认记录该事件」并落库

### Requirement: 多段确认策略 C
多段拼装完成后，系统 SHALL 采用混合确认：先处理阻塞澄清（父消歧、缺量追问）；其后若剩余段数较少且操作同质（如同为 create 叶子），SHALL 允许一次拼问确认；若段数达到实现所定长阈值或混有不同 `op`/`target_type`，SHALL 逐段确认。

#### Scenario: 短同质拼问
- **WHEN** 两段均为 create 叶子且槽位齐全
- **THEN** 系统 SHALL 可用一条拼接确认问句覆盖两段

#### Scenario: 混装逐段
- **WHEN** 拼装结果同时含 create 与 read
- **THEN** 系统 SHALL 逐段（或按 op 分组逐次）确认，MUST NOT 用单条 yes/no 同时确认写库与查史

### Requirement: 短拼问段数上限
实现 MUST 提供可配置或常量的短拼问最大段数（默认 **3**）；超过该上限时 SHALL 走逐段确认。

#### Scenario: 四段 create 逐段
- **WHEN** 四个 create 叶子段均槽位齐全且上限为 3
- **THEN** 系统 SHALL 逐段确认（或等价不一次拼满四段）
