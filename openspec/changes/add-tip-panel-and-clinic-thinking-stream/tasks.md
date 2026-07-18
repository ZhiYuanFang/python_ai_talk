## 1. clinic_graph 流式思考改造（Python 侧）

- [x] 1.1 创建节点思考文案映射表 `app/graphs/nodes/thinking_messages.py`，定义节点名到中文思考文案的映射（judge_data_requirement→"正在分析需要哪些历史数据..."、fetch_history→"正在拉取最近的喂养记录..."、search_vectors→"正在检索知识库中的相关知识..."、fetch_baby_profile→"正在获取宝宝画像信息..."、llm_start→"正在生成回答..."），每条代码加中文业务逻辑注释
- [ ] 1.2 修改 `app/graphs/clinic_graph.py`，确保图支持 `astream()` 流式执行（LangGraph 原生支持，验证节点无阻塞式 IO 即可），加中文注释
- [x] 1.3 修改 `app/api/routes/clinic.py`，将 `clinic_graph.ainvoke()` 改为 `clinic_graph.astream()`，在收到每个节点 chunk 时推送 thinking 事件，节点全部完成后再调用 stream_response 流式输出 LLM 回答，保持 SSE 格式 `{"type":"thinking|answer","content":"..."}`，加中文注释

## 2. tip_graph 基础设施（Python 侧）

- [x] 2.1 创建 `app/graphs/states/tip_state.py`，定义 TipState 状态类，包含 event_info（事件ID/事件名）、device_no、model_config、current_time、baby_age_months、data_requirement、history_events、knowledge、baby_profile、response 等字段，加中文业务逻辑注释
- [x] 2.2 创建 `app/graphs/nodes/prompts/tip_answer.py`，定义 `build_tip_answer_system_prompt` 和 `build_tip_answer_user_message` 函数，引导 LLM 结合当前事件+时间+月龄+知识库+历史生成当下总结和下一步注意事项，加中文注释
- [x] 2.3 创建 `app/graphs/nodes/stream_tip_response.py`，实现 `stream_tip_response` 异步生成器节点，调用 LLM 流式接口，支持 thinking 模式，返回 thinking 和 answer chunk，加中文注释
- [x] 2.4 创建 `app/graphs/tip_graph.py`，构建 tip_graph 状态图：TipState → judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → stream_tip_response → END，复用共享节点，编译并导出 tip_graph 实例，加中文注释
- [x] 2.5 创建 `app/schemas/tip.py`，定义 TipRequest（event_id、event_name、device_no、baby_age_months、current_time、model）和 TipStreamResponse（type、content）模型，加中文注释
- [x] 2.6 创建 `app/api/routes/tip.py`，实现 `/v1/tip/stream` SSE 路由，接收 TipRequest，用 astream 执行 tip_graph 推送节点级 thinking 事件，然后调用 stream_tip_response 流式输出 thinking 和 answer 事件，加中文注释
- [x] 2.7 修改 `app/api/routes/__init__.py`，注册 tip 路由到统一 APIRouter，加中文注释

## 3. Go voice service tip_ai 额度（Go 侧）

- [x] 3.1 修改 `internal/services/contracts/ai_quota_contracts.go`，新增 `AIQuotaTipAI AIQuotaFeature = "tip_ai"` 常量，扩展 VoiceAIQuotaDefaultDTO 和 VoiceAIQuotaAppStatus 增加 TipAi 字段，加中文注释
- [x] 3.2 修改 `internal/services/voice/ai_quota_store.go`，在 `validateVoiceQuotaFeature` 中增加 tip_ai 校验，在 `EnsureVoiceAIQuotaDefaultRow` 中增加 tip_ai_monthly_limit 默认值（如 50），加中文注释
- [x] 3.3 修改 `internal/services/voice/ai_quota.go`，新增 `CheckTipAIQuota`、`CheckTipAIQuotaSnapshot`、`ConsumeTipAIQuota` 函数，参考 clinic_ai 的降级模式（Allowed→deepseek，Degraded→zhipu），加中文注释
- [x] 3.4 在 voice service 新增 internal HTTP API 处理器，支持 `/internal/quota/check?feature=tip_ai&wxId=xxx` 和 `/internal/quota/consume?feature=tip_ai&wxId=xxx`，复用 CheckTipAIQuotaSnapshot/ConsumeTipAIQuota，加中文注释
- [x] 3.5 修改 `internal/services/contracts/http_targets.go`，新增 `VoiceInternalQuotaCheckPath()` 和 `VoiceInternalQuotaConsumePath()` 方法，加中文注释

## 4. Go history service tip 功能（Go 侧）

- [x] 4.1 创建 `internal/model/entity/tip.go`，定义 Tip 实体结构（Id、DeviceNo、WxId、EventId、EventName、BabyAgeMonths、TipContent、ModelUsed、FeedbackResult、FeedbackContent、CreatedAt、FeedbackAt），加中文注释
- [x] 4.2 创建 `internal/dao/tip.go`，定义 tip 表 DAO，加中文注释
- [x] 4.3 创建 `internal/services/history/tip_feedback.go`，实现 `SaveTipFeedback` 函数，根据 tip_id 更新 feedback_result、feedback_at 字段，加中文注释
- [x] 4.4 修改 `internal/platform/cachekit/keys_history.go`，新增 `TipDebounceKey(deviceNo string) string` 函数，返回 `tip:debounce:{deviceNo}` 格式的 Redis key，加中文注释
- [x] 4.5 创建 `internal/services/history/tip.go`，实现核心逻辑：`GenerateTip`（去抖检查→额度检查→模型降级判断→调用 Python SSE→透传→异步存储）和 `delegateCheckTipQuota`/`delegateConsumeTipQuota`（delegate HTTP 调用 voice service），加中文注释
- [x] 4.6 修改 `internal/services/history/delegate_http.go`，新增 `delegateCheckTipQuota` 和 `delegateConsumeTipQuota` 函数，通过 internal HTTP 调用 voice service 的 quota check/consume API，加中文注释
- [x] 4.7 修改 `internal/controller/device_history.go`，新增 `TipGenerate` 和 `TipFeedback` 两个 handler 方法，注册 `/tip/generate`（SSE 透传）和 `/tip/feedback`（POST JSON）路由，加中文注释

## 5. Flutter 小贴士组件（Flutter 侧）

- [x] 5.1 创建 `lib/data/tip_models.dart`，定义 TipState 枚举（idle/streaming/done）、TipContent 模型（thinking、answer、tipId）、TipFeedback 枚举（none/up/down），加中文注释
- [x] 5.2 创建 `lib/data/tip_repository.dart`，实现 SSE 客户端 `TipRepository`，调用 Go `/tip/generate` 接口接收 SSE 流，解析 thinking/answer 事件，提供 `streamTip` 方法返回 Stream，加中文注释
- [x] 5.3 创建 `lib/providers/tip_provider.dart`，用 Riverpod `StateNotifier<TipContent>` 管理小贴士状态，初始为 idle（无内容隐藏），提供 `startStreaming` 和 `submitFeedback` 方法，加中文注释
- [x] 5.4 创建 `lib/ui/widgets/home_tip_panel.dart`，实现小贴士组件：ConsumerWidget 监听 tipProvider，idle 时返回 SizedBox.shrink()，streaming/done 时展示内容，maxHeight:200 + ScrollController 自动滚到底，复用 ClinicAnswerBody 样式（流式纯文本/完成 Markdown），右下角 👍/👎 按钮，点击后变灰+保留选中+隐藏未选+toast，加中文注释
- [x] 5.5 修改 `lib/ui/home_screen.dart`，在历史记录列表和今日汇总之间插入 HomeTipPanel 组件，加中文注释
- [x] 5.6 修改 `lib/data/remote_feed_repository.dart`，在 WS `onApplicationFrame` 回调中识别 type=create 的新增事件，触发 tipProvider.startStreaming（传入事件信息），加中文注释

## 6. 测试与验证

- [x] 6.1 Python 侧语法检查：`python -m py_compile` 验证所有新增和修改的 .py 文件语法正确
- [x] 6.2 Go 侧编译检查：`go build ./...` 验证所有新增和修改的 .go 文件编译通过
- [x] 6.3 clinic 流式思考验证：验证 `/v1/clinic/stream` 接口依次推送节点级 thinking 事件和 LLM answer 事件，SSE 格式正确
- [x] 6.4 tip_graph 流程验证：验证 `/v1/tip/stream` 接口执行 tip_graph 全流程，thinking 和 answer 事件正确推送
- [x] 6.5 额度降级验证：验证 tip_ai 额度充足时用 deepseek，额度用尽 Degraded 时用 zhipu，完全不足时返回错误
- [x] 6.6 去抖逻辑验证：验证 Redis SET NX EX 实现 1 小时去抖，首次触发成功，1 小时内重复触发被拦截
- [x] 6.7 Flutter 组件动态展示验证：验证 idle 时隐藏，streaming 时展示+自动滚动，done 时 Markdown 格式化，重启 app 后无展示
- [x] 6.8 反馈交互验证：验证 👍/👎 点击后变灰+保留选中+隐藏未选+toast，反馈请求正确发送到 Go 并存储到 tip 表
- [x] 6.9 端到端联调：验证完整链路 Flutter（WS 新增事件）→ Go（去抖+额度+透传）→ Python（tip_graph 生成）→ Go（存储）→ Flutter（展示+反馈）

## 7. 小贴士悬浮展示+关闭动画改造（Flutter 侧）

- [x] 7.1 修改 `lib/data/tip_models.dart`，TipDisplayState 枚举新增 `closing` 值（idle/streaming/done/closing），加中文注释
- [x] 7.2 修改 `lib/providers/tip_provider.dart`，新增 `dismiss()` 方法（状态切到 closing，供 UI 触发动画）和 `completeDismiss()` 方法（动画完成后清空内容回到 idle），加中文注释
- [x] 7.3 修改 `lib/ui/widgets/home_tip_panel.dart`，背景透明度 0.5→0.7；右上角新增 ✕ 关闭按钮；用 AnimatedSize 实现向上折叠动画（300ms, easeOut）；closing 态触发动画，动画完成后调用 completeDismiss()；done 态同时展示关闭按钮和反馈按钮，加中文注释
- [x] 7.4 修改 `lib/ui/home_screen.dart`，将 HomeTipPanel 从 Column 中移出，改用 Stack+Positioned 悬浮在历史记录区域上方（覆盖遮挡），加中文注释
- [x] 7.5 验证：悬浮展示 + 背景透明 0.7 + 关闭按钮 + 折叠动画 + 关闭后可再次触发
