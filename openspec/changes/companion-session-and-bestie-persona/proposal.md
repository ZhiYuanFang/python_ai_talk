## Why

clinic / tip 仍以「儿科医生助手 / 育儿注意事项」面向家长，与产品目标「懂娃的闺蜜、口语接住情绪」不一致；同时 tip 开场与 clinic 续聊彼此无记忆，且前端已去掉建议采纳按钮，知识飞轮缺少新的隐式信号。需要在不拆 HTTP 入口的前提下，用 Python 会话串联 tip↔clinic，并在连续对话中推断上一条建议是否被接受。

## What Changes

- 将 tip / clinic（及 intent 内嵌的 suggest/conversation 回答）的对外人格改为：对妈妈/家长说话的「懂一点的闺蜜」，口语化；喂养知识与记录仅作背景，不做诊断/开药口吻
- 在 Python 侧用 Redis 维护按 `device_no` 的陪伴会话：tip 与 clinic 读写同一会话；最多保留最近 **5 轮**（user+assistant）；TTL **7 天**（有读写建议滑动续期）
- tip 添加事件开场仍走 `/v1/tip/stream`；用户可基于 tip 继续调 `/v1/clinic/stream` 续聊，并带上会话内近 5 轮上下文
- clinic 连续对话时，在生成新回复前对「上一条建议」（含 tip 开场）做 **接受 / 拒绝 / 说不清** 三态判定；接受/拒绝写入知识飞轮（对上一轮关联的 knowledge ids 调质量分），说不清或失败不改分；每条建议只飞轮一次
- 保留现有 `/v1/clinic/feedback`、`/v1/tip/feedback` 作为兼容通道；主路径改为隐式判定
- **不**删除 clinic / tip / knowledge / health 等 HTTP 接口；**不**重命名 `/clinic`、`/tip` 路径

## Capabilities

### New Capabilities

- `companion-session`: 按 `device_no` 的 Redis 陪伴会话（tip/clinic 共享、5 轮窗口、7 天 TTL、读写与截断规则）
- `implicit-suggestion-feedback`: 连续对话中对上一条建议的三态隐式判定并驱动知识飞轮
- `bestie-companion-persona`: tip / clinic / suggest 等面向用户的提示词与输出形态改为口语化闺蜜人格

### Modified Capabilities

- （无：`openspec/specs/` 下尚无已归档基线 capability）

## Impact

- **代码**：`app/api/routes/tip.py`、`clinic.py`；`app/tip` / `app/clinic` 提示词与流式生成；新增 `app/shared` 会话存储与采纳判定（遵守 feeding/clinic 不可互引）；可能触及 intent 内嵌 `generate_response` / `suggest_answer` 以统一人格
- **API**：请求/响应以 `device_no` 为会话键，可不强制新传 `conversation_id`；行为上 tip/clinic 变为有状态续聊；显式 feedback 仍可用
- **依赖**：复用现有 Redis（与 `RedisGate` 同集群/实例），新增会话 key 与 TTL 配置
- **跨仓**：Go/Flutter 契约路径可不变；续聊体验依赖同一 `device_no`；若 Go 仍调显式 feedback，可并存
- **非目标**：不删接口；不做按事件分房间的多会话；不改喂养 intent 主路径的 pending 澄清存储
