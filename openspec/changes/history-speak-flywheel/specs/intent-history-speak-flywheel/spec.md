## ADDED Requirements

### Requirement: 查史播报须有独立关键字飞轮
系统 SHALL 使用独立于 `feeding_intents` 与 `feeding_type_cues` 的 Chroma 集合（如 `feeding_history_speak_cues`）存储短关键字到查史播报策略：`point_pick`（`latest`|`prefer_completed`）与 `open_speak`（`elapsed`|`in_progress`）。系统 MUST NOT 将该集合用于整包 multi-events 回放，MUST NOT 与类型/事件飞轮混存同一匹配空间。

#### Scenario: 关键字命中带齐两维
- **WHEN** 用户 history 点查句命中查史播报飞轮且 payload 两维均合法
- **THEN** 系统 SHALL 采用该 `point_pick` 与 `open_speak` 且 MUST NOT 为此再调用查史播报小 LLM

### Requirement: 缺维须调用查史播报小 LLM
当 history 点查路径上飞轮未命中，或命中但 `point_pick`/`open_speak` 缺省或非法时，系统 SHALL 调用查史播报小 LLM（提示词常量在 `prompts/system.py`），经 SSE 真流式并透出中文 reasoning，输出合法两维及可选 `keywords[]`。系统 MUST NOT 在缺维时静默默认 `prefer_completed`。调用 MUST NOT 写入 `rule_gap`。

#### Scenario: 未命中飞轮走 LLM
- **WHEN** 点查句未命中查史播报飞轮
- **THEN** 系统 SHALL 调用查史播报小 LLM 解析两维
- **AND** MUST NOT 未经 LLM 直接套用优先已完成选行

#### Scenario: LLM 失败降级
- **WHEN** 查史播报小 LLM 失败或输出仍非法
- **THEN** 系统 SHALL 使用明确无法准确作答类降级话术
- **AND** MUST NOT 静默回落无条件优先已完成

### Requirement: 点查按两维选行与进行中话术
在 history 点查（非 daily）选答时，系统 SHALL 按 `point_pick` 从候选行选一条：`latest` 为开始时间最近（进行中可胜出）；`prefer_completed` 为优先最近已完成、否则最近进行中。当选中行无有效结束时间时，系统 SHALL 按 `open_speak` 播报：`elapsed` 为已持续时长（now−start）；`in_progress` 为正在进行中口径（MAY 拼接进行中 ETA）。选中行有有效结束时，计时类 SHALL 继续用 end−start 用时话术。

#### Scenario: 多久了选最近进行中并报已持续
- **WHEN** `point_pick=latest` 且 `open_speak=elapsed`，候选中最近一行为进行中睡眠、更早有已完成睡眠
- **THEN** `content` SHALL 基于该进行中行
- **AND** SHALL 表达已持续/已睡约时长（而非仅答更早完成记录的用时）

#### Scenario: 上次仍可优先已完成
- **WHEN** `point_pick=prefer_completed` 且存在已完成与进行中
- **THEN** `content` SHALL 基于最近已完成记录作答

### Requirement: 查史播报飞轮 Admin
系统 SHALL 提供管理端 HTTP API（如 `/v1/admin/history-speak-cache`）支持列表、bulk（同 document 跳过）、dedupe、删除。鉴权与意图/类型缓存 admin 同级。写入 MUST NOT 因缺口箱自动发生。

#### Scenario: bulk 写入策略关键字
- **WHEN** 管理端 bulk 写入 document「多久了」与合法两维
- **THEN** 后续同线索点查 SHALL 可热路径命中该策略
