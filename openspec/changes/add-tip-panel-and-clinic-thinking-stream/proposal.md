## Why

当前 `clinic_graph` 使用 `graph.ainvoke()` 同步执行全部节点后才流式输出 LLM 回答，用户在数据准备阶段无法感知 AI 正在做什么，体验上"卡顿感"明显；同时用户新增喂养事件后缺乏即时智能反馈，无法获得针对当前事件的总结与下一步指导，错失了最佳的育儿建议触达时机。

## What Changes

- **clinic_graph 流式思考改造**：将 `clinic_graph.ainvoke()` 改为 `graph.astream()`，每个节点开始/结束时推送 `thinking` 事件，让用户实时看到"正在分析需要哪些历史数据...""正在检索知识库..."等思考过程，最后再流式输出 LLM 回答。
- **新增小贴士功能（跨三端）**：
  - **触发**：Flutter 端接收到历史 WebSocket 新增事件通知时自动触发（涵盖语音球和按钮添加事件，排除编辑/删除事件）。
  - **去抖**：Go history service 侧基于 Redis 按 `deviceNo` 控制，1 小时内仅触发一次，间隔可后续动态调整。
  - **额度**：Go voice service 新增 `tip_ai` 额度类型，与 `voice_ai`/`clinic_ai` 统一管理，预留充值功能。额度足够用 deepseek 模型，不足时降级到 zhipu 模型。
  - **生成**：Go history service 调用 Python 新增的 `/v1/tip/stream` SSE 接口，结合当前事件 + 时间 + 宝宝月龄 + 知识库同月龄参考 + 近期喂养历史，流式输出思考过程和结果。
  - **展示**：Flutter 在历史记录列表和今日汇总之间动态展示小贴士组件（无内容则隐藏，不缓存，重启 app 后无展示），最大高度 200 可滚动并保持显示最新内容，右下角放 👍/👎 反馈按钮。
  - **反馈**：点击反馈按钮后按钮变灰并仅保留选中按钮 + toast 提示，请求 Go 新增的反馈 API，记录到 `ai_voice_history.tip` 表。
- **Python 新增 tip_graph**：独立的状态图，复用共享节点（judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile），新增独立的提示词和小贴士生成节点。
- **数据持久化**：在 `ai_voice_history` 数据库新增 `tip` 表，存储事件ID、事件名、宝宝月龄、wx.id、tip 内容、使用的模型、生成时间、反馈内容、反馈结果。仅 history 微服务可访问此库（遵守微服务边界）。

## Capabilities

### New Capabilities
- `clinic-thinking-stream`: clinic_graph 执行过程流式思考展示，将节点执行过程以 thinking 事件形式推送，提升诊疗场景的 AI 思考透明度
- `tip-generation`: 小贴士生成功能，跨 Python/Go/Flutter 三端，新增事件触发后基于事件+月龄+知识库+历史生成即时小贴士
- `tip-feedback`: 小贴士用户反馈功能，记录用户对小贴士的认同/不认同反馈到数据库

### Modified Capabilities
<!-- 本次变更不修改现有 spec 级别的需求 -->

## Impact

**Python 侧（python_ai_talk）**：
- 修改 `app/api/routes/clinic.py`：ainvoke 改为 astream，推送节点级 thinking 事件
- 修改 `app/graphs/clinic_graph.py`：支持流式执行
- 新增 `app/graphs/tip_graph.py`：小贴士状态图
- 新增 `app/graphs/states/tip_state.py`：小贴士状态定义
- 新增 `app/graphs/nodes/prompts/tip_answer.py`：小贴士提示词
- 新增 `app/graphs/nodes/stream_tip_response.py`：小贴士流式生成节点
- 新增 `app/api/routes/tip.py`：小贴士 SSE 路由
- 新增 `app/schemas/tip.py`：小贴士请求/响应模型
- 修改 `app/api/routes/__init__.py`：注册 tip 路由

**Go 侧（go_ai_talk）**：
- **history service**：
  - 新增 `internal/services/history/tip.go`：小贴士核心逻辑（去抖、调用 Python、透传 SSE、存储）
  - 新增 `internal/services/history/tip_feedback.go`：反馈存储逻辑
  - 修改 `internal/controller/device_history.go`：新增 `/tip/generate` 和 `/tip/feedback` 路由
  - 新增 `internal/dao/tip.go`：tip 表 DAO
  - 新增 `internal/model/entity/tip.go`：tip 实体
- **voice service**：
  - 修改 `internal/services/contracts/ai_quota_contracts.go`：新增 `AIQuotaTipAI` 额度类型
  - 修改 `internal/services/voice/ai_quota.go`：新增 `CheckTipAIQuota`/`ConsumeTipAIQuota` 方法
  - 修改 `internal/services/voice/ai_quota_store.go`：新增 tip_ai 额度默认值和校验
  - 新增 internal HTTP API：`/internal/quota/check` 和 `/internal/quota/consume` 支持 tip_ai
- **shared**：
  - 修改 `internal/services/contracts/http_targets.go`：新增 quota internal 路径
  - 修改 `internal/platform/cachekit/keys_history.go`：新增 tip 去抖缓存键

**Flutter 侧（flutter_ai_talk）**：
- 新增 `lib/ui/widgets/home_tip_panel.dart`：小贴士组件（SSE 接收、自动滚动、反馈按钮）
- 新增 `lib/data/tip_repository.dart`：小贴士数据层（SSE 客户端）
- 新增 `lib/providers/tip_provider.dart`：小贴士状态管理
- 修改 `lib/ui/home_screen.dart`：在历史记录和今日汇总之间集成小贴士组件
- 修改 `lib/data/remote_feed_repository.dart`：监听 WS 新增事件触发小贴士
- 新增 `lib/data/tip_models.dart`：小贴士数据模型

**数据库**：
- `ai_voice_history` 库新增 `tip` 表

**依赖**：
- Python 复用现有 LangGraph + LLM + 向量库基础设施
- Go 复用现有额度系统 + delegate HTTP 模式
- Flutter 复用现有 SSE/WS 基础设施
