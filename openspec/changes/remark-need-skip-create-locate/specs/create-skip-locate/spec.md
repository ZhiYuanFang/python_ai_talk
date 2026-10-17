## ADDED Requirements

### Requirement: Create-only batches do not resolve locate

当本批待落库项里没有修改也没有删除时，系统 MUST NOT 调用改删定位。记一笔的开始时间 MUST 仍由句中已解析的钟点写入新记录。

#### Scenario: Morning clock creates a new row

- **WHEN** 用户说「早上8点吃了120配方奶」且本批只有记一笔
- **THEN** 系统 MUST NOT 调用改删定位
- **AND** 新记录的开始时间 MUST 为该句解析出的早上 8 点

### Requirement: Mixed batches still locate mutations

同一批同时含有记一笔和修改或删除时，系统 MUST 仍解析定位策略，且 MUST 只把该策略用于修改和删除。

#### Scenario: Create beside an update still locates the update

- **WHEN** 同一批既有记一笔又有修改
- **THEN** 系统 MUST 为修改解析定位策略
- **AND** 记一笔 MUST NOT 被改成覆盖最近一条旧记录
