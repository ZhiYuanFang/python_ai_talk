## Why

意图近况现在按 10 分钟保留家长原话和回答，漏答自由回答会把这段当背景。窗口偏长，更早的来回容易被当成当前语境。改为只记最近 3 分钟。

## What Changes

- `intent_recent_talk` 的窗口从 600 秒改为 180 秒。读的时候丢掉超过 3 分钟的轮次，写入时 Redis 键过期也是 180 秒。
- 漏答提示词里的「近十分钟对话」改为「近三分钟」。
- 字数上限约 800 字、只给漏答当背景、与诊所陪伴会话分开，这些保持原样。
- 预测算法快照的 10 分钟过期不改。

## Capabilities

### New Capabilities

- `intent-recent-talk-3min`: 意图侧按设备只保留最近 3 分钟的来回，供漏答背景使用

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未单独描述该窗口。进行中的 `miss-reply-recent-dialogue` 仍写 10 分钟；本变更另立增量，实现时以 3 分钟为准。

## Impact

- `app/feeding/services/intent_recent_talk.py` 的 `WINDOW_SEC` 与注释。
- `app/feeding/services/agent_miss_soft_reply.py` 拼进用户消息的窗口文案。
- `app/feeding/graphs/nodes/prompts/system.py` 漏答系统提示里的「近十分钟」。
- 键仍是 `intent:recent_talk:{device_no}`。已存在的旧键不必迁移：读取时按轮次时间戳过滤。
