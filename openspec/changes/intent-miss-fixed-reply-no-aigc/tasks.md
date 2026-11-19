## 1. 固定话术

- [x] 1.1 增加常量「我只能回答信息记录相关问题」（中文注释标明 miss 对外非 AIGC）
- [x] 1.2 `intent` 路由：miss 硬文案落库后，对外 `content` 改为该常量；不再 `await soft_reply_for_miss` LLM

## 2. 清理

- [x] 2.1 停用/删除 `soft_reply_for_miss` 内 LLM、快照补算与 `AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT` 引用（或函数改为仅返回常量）
- [x] 2.2 确认确认/消歧路径仍跳过 miss 改写；inbox 仍用硬文案

## 3. 验收

- [x] 3.1 手工：触发无法识别/other 类 miss → 用户收到固定句；inbox 仍有硬文案记录
