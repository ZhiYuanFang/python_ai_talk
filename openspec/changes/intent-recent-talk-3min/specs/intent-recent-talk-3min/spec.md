## ADDED Requirements

### Requirement: 意图近况只保留三分钟

意图侧 MUST 按设备保留最近 3 分钟内家长听到的来回。超过 3 分钟的轮次 MUST NOT 进入漏答提示词。写入时 Redis 键过期 MUST 为 180 秒。该近况 MUST 与诊疗陪伴会话分开，MUST NOT 改变预测算法快照的过期时间。注入提示词时 MUST 称这段为近三分钟对话，且只作背景。

#### Scenario: 三分钟内的来回仍可注入

- **WHEN** 同一设备上一轮回答发生在 3 分钟以内，本轮走漏答自由回答
- **THEN** 提示词中的近况段 MUST 含有该轮家长原话与回答
- **THEN** 文案 MUST 标明这是近三分钟对话，并且只作背景

#### Scenario: 超过三分钟的来回丢掉

- **WHEN** 同一设备上一轮回答早于 3 分钟
- **THEN** 本轮漏答提示词 MUST NOT 含有该轮

#### Scenario: 写入后键只再活三分钟

- **WHEN** 意图返回前记下本轮听到的句子
- **THEN** `intent:recent_talk:{device_no}` 的过期时间 MUST 刷新为 180 秒

#### Scenario: 预测快照过期不变

- **WHEN** 预测算法快照写入 Redis
- **THEN** 该快照的过期时间 MUST 仍为 600 秒
