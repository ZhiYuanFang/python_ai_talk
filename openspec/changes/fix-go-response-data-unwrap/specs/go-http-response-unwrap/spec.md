## ADDED Requirements

### Requirement: 解包 GoFrame 标准响应的 data 载荷
Python 调用兄弟仓（GoFrame）HTTP API 时，SHALL 将响应体视为 `{ "code", "message", "data": <payload> }` 形态，业务字段 MUST 从 `data` 载荷读取，不得把响应根对象误当作业务 `data`。

#### Scenario: 标准包装下读取 list
- **WHEN** 兄弟仓返回 `{ "code": 0, "message": "", "data": { "list": [ ... ] } }`
- **THEN** 客户端 SHALL 得到非空业务列表（当 `data.list` 非空时）
- **AND** SHALL NOT 因在根对象上查找 `list` 而得到空列表

#### Scenario: 事件字典接口
- **WHEN** 调用 `get_event_dictionary()` 且接口按标准包装返回含事件的 `data.list`
- **THEN** 返回的 Python 列表长度 SHALL 等于 `data.list` 中的元素数量
- **AND** 元素 SHALL 继续做既有 camelCase → snake_case 字段映射（`id`→`event_id` 等）

#### Scenario: 历史列表与筛选接口
- **WHEN** 调用 `get_history_events()` 或 `get_filtered_history_events()` 且响应为标准包装且 `data.list` 有数据
- **THEN** 返回列表 SHALL 来自 `data.list`，而非根级 `list`

#### Scenario: 宝宝画像接口
- **WHEN** 调用 `get_baby_profile(device_no)` 且 HTTP 200，响应为 `{ "code": 0, "data": { "babyName", "birthday", "sex", ... } }`
- **THEN** 返回值 SHALL 为 `data` 对象（业务字段字典），SHALL NOT 把含 `code`/`message` 的根对象整段返回给调用方

#### Scenario: data 缺失时的安全回退
- **WHEN** 响应 JSON 根对象没有 `data` 键
- **THEN** 解包逻辑 MAY 将根对象视为载荷（兼容非标准响应）
- **AND** 列表提取在找不到 `list` 时 SHALL 返回空列表而非抛出与解包无关的异常
