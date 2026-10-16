## ADDED Requirements

### Requirement: 画像提示对齐生日接口字段

诊疗回答与覆盖缺口软回复在向模型说明宝宝信息时，MUST 使用生日接口字段 `babyName`、`birthday`、`sex`。系统 MUST NOT 读取 `gender` 作为性别。`sex` 为 `0` 时 MUST 写成女，为 `1` 时 MUST 写成男，其它值或缺失时 MUST 写成未知。`babyName` 非空时 MUST 写入名字；空串 MUST NOT 写成名字。月龄 MUST 由 `birthday` 用现有上海日历计算并写成「N 个月」；`birthday` 为 `0`、空或无法解析时月龄 MUST 为未知。系统 MUST NOT 把 `sex` 的原始数字作为画像提示交给模型。

#### Scenario: 女宝且有生日

- **WHEN** 画像 `sex` 为 `0`、`babyName` 为非空名字、`birthday` 为可解析的 Unix 秒
- **THEN** 提示词中的性别 MUST 为女
- **AND** MUST 包含该名字与计算出的月龄
- **AND** MUST NOT 出现 `sex=0`

#### Scenario: 男宝

- **WHEN** 画像 `sex` 为 `1`
- **THEN** 提示词中的性别 MUST 为男

#### Scenario: 性别或生日缺失

- **WHEN** `sex` 不是 `0` 或 `1`，或 `birthday` 为 `0`
- **THEN** 对应项 MUST 为未知
- **AND** 系统 MUST NOT 假设具体月龄或性别

### Requirement: 诊疗与软回复使用同一套说法

诊疗用户消息与覆盖缺口软回复 MUST 使用上述同一套名字、性别与月龄说法。软回复在没有宝宝画像时 MUST 明确没有基础信息。预测算法快照 MUST 仍只使用已有缓存；缓存不存在或过期时 MUST NOT 为该回复重新计算。

#### Scenario: 软回复不再只剩性别数字

- **WHEN** 失败软回复注入宝宝基础信息且画像含 `sex` 与 `birthday`
- **THEN** 用户消息 MUST 含译后的性别与月龄
- **AND** MUST NOT 只包含 `sex=0` 这类原始键值

#### Scenario: 无预测快照不重算

- **WHEN** 设备上没有未过期的预测算法快照
- **THEN** 软回复 MUST 标明没有预测算法快照
- **AND** MUST NOT 当场重算预测
