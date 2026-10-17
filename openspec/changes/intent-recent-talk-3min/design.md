## Context

意图近况存在 `intent_recent_talk.py`。`WINDOW_SEC = 600` 同时用于两处：`load_recent` 按每轮 `at` 丢掉超时轮次，`append_turn` 用 `ex=WINDOW_SEC` 刷新整条 Redis 键。漏答自由回答经 `prompt_block` 把剩下的来回拼进提示词，文案写的是「近十分钟对话」。`prompts/system.py` 的漏答系统提示也写了「近十分钟」。

诊所陪伴会话和预测快照各自另有过期时间。预测快照也是 600 秒，但不是这段对话。

## Goals / Non-Goals

**Goals:**

- 意图近况只保留最近 3 分钟。
- 读过滤和键过期使用同一个数。
- 给模型看的窗口文案改成「近三分钟」。

**Non-Goals:**

- 不改约 800 字的提示词预算，不改单侧截断。
- 不改诊所陪伴会话。
- 不改预测算法快照 TTL。
- 不迁移或删除已经写在 Redis 里的旧键。

## Decisions

1. **只改 `WINDOW_SEC`。** 从 `600` 改为 `180`。读和写已经共用它，不必再写第二处秒数。

2. **旧键靠读取过滤。** 键里可能还留着 10 分钟 TTL。`load_recent` 按 `now - at > WINDOW_SEC` 丢掉旧轮，超过 3 分钟的来回不会进提示词。下一轮 `append_turn` 会把键过期刷新成 180 秒。

3. **文案跟窗口一起改。** `agent_miss_soft_reply.py` 的用户消息和 `prompts/system.py` 漏答系统提示里的「近十分钟」改为「近三分钟」。

## Risks / Trade-offs

- [间隔超过 3 分钟的下一句漏答看不到上一轮] → 接受；这就是缩短窗口的目的。
- [旧键在 Redis 里还能活到原来的 10 分钟] → 读取已按 3 分钟丢掉轮次，不会被注入。

## Migration Plan

- 改常量、模块注释和两处提示词文案。
- 回滚把 `WINDOW_SEC` 改回 `600`，文案改回「近十分钟」。

## Open Questions

- （无）
