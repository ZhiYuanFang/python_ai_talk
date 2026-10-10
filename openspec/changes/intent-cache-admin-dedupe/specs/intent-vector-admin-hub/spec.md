## ADDED Requirements

### Requirement: 意图向量列表展示序号
运维 Hub 意图向量管理页 SHALL 在表格第一列展示序号，便于运维确认当前列表条数与位置。序号 MUST 为当前请求分页下的连续编号（`offset + 行序`，从 1 起算）。页面 MUST 继续展示总条数（如「共 N 条」）。

#### Scenario: 首列可见序号
- **WHEN** 运维打开意图向量缓存页且列表非空
- **THEN** 表格第一列 SHALL 为序号
- **AND** 首行序号 SHALL 为 offset+1（默认首页为 1）

### Requirement: Hub 整理重复并弹窗展示删除结果
运维 Hub SHALL 提供「整理重复」操作，调用管理端整理接口（经 voice admin 代理）。完成后 MUST 以弹窗或等价模态展示被删除条目（至少 id 与 document）；若无删除 MUST 明确提示无重复。完成后 MUST 刷新列表。重复判定以服务端 document 原文全等为准，Hub MUST NOT 自行用相似度判重。

#### Scenario: 有重复时弹出删除列表
- **WHEN** 库中存在相同 document 的多条且运维点击整理重复
- **THEN** Hub SHALL 展示被删条目的 id 与 document
- **AND** 列表刷新后同文案至多保留一条对应行

#### Scenario: 无重复时提示
- **WHEN** 库中无相同 document 且运维点击整理重复
- **THEN** Hub SHALL 提示无重复（或 deleted 为空的等价说明）
- **AND** MUST NOT 误报已删除条目

### Requirement: Hub 批量上传展示新增与跳过
运维 Hub 提交批量种子后，MUST 展示新增条数，并在存在跳过时以弹窗或等价方式列出跳过的 document（拒绝文案相同）。Hub MUST NOT 将跳过展示为写入成功。

#### Scenario: 含重复文案的批量结果
- **WHEN** 批量 JSON 中含库中已有的相同 document 与全新 document
- **THEN** Hub SHALL 表明有新增成功项
- **AND** SHALL 列出被跳过的相同文案（不得仅显示「全部成功」而隐瞒跳过）
