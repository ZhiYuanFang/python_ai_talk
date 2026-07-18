## Context

当前 `python_ai_talk` 的 `clinic_graph` 在 [clinic.py](file:///d:/work/python_ai_talk/app/api/routes/clinic.py) 中使用 `graph.ainvoke()` 同步执行全部数据准备节点（judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile），完成后才调用 `stream_response` 流式输出 LLM 回答。用户在数据准备阶段看不到任何反馈，体验上存在"卡顿感"。

同时，`go_ai_talk` 的 history service 已具备完整的事件新增 WebSocket 推送能力（`publishHistoryChange`），`flutter_ai_talk` 通过 `RemoteFeedRepository` 监听 WS 新增事件。但新增事件后缺乏即时智能反馈，用户无法获得针对当前事件的总结与下一步指导。

额度系统集中在 voice service（[ai_quota.go](file:///d:/work/go_ai_talk/internal/services/voice/ai_quota.go) + [ai_quota_store.go](file:///d:/work/go_ai_talk/internal/services/voice/ai_quota_store.go)），通过 Redis 按月按 wxId 计数，已有 `voice_ai`/`clinic_ai`/`polish` 三种 feature。history service 通过 delegate HTTP（[delegate_http.go](file:///d:/work/go_ai_talk/internal/services/history/delegate_http.go)）调用 voice service，已有 `DelegateTextChat` 先例。

微服务边界：仅 history service 可访问 `ai_voice_history` 数据库（通过 `HISTORY_DB_LINK` 配置）。

## Goals / Non-Goals

**Goals:**
- 将 clinic_graph 执行过程流式化，每个节点执行时推送 thinking 事件，提升诊疗场景 AI 思考透明度
- 新增小贴士功能：新增事件触发后，基于事件+月龄+知识库+历史生成即时小贴士，跨 Python/Go/Flutter 三端
- tip_ai 额度与现有额度统一管理，预留充值功能
- 1 小时去抖，按 deviceNo 控制，间隔可动态调整
- 小贴士组件动态展示，无内容隐藏，不缓存，重启 app 后无展示
- 用户反馈记录到 ai_voice_history.tip 表

**Non-Goals:**
- 不修改 clinic_graph 的数据准备节点逻辑（仅改执行方式为流式）
- 不实现充值功能（仅预留额度统一管理基础）
- 不做小贴士内容缓存（前端不缓存，后端不缓存生成结果）
- 不做小贴士历史查询接口（本次仅记录，不查询）
- 不做编辑/删除事件的小贴士触发
- 不做小贴士手动关闭功能（重启 app 即关闭）

## Decisions

### D1: clinic_graph 流式化用 graph.astream() 实现节点级 thinking

**决策**：将 `clinic_graph.ainvoke()` 改为 `graph.astream()`，利用 LangGraph 的流式执行模式，在每个节点开始执行时推送 thinking 事件。

**理由**：
- LangGraph 原生支持 `astream()`，会按节点产出 chunk，无需改动节点内部逻辑
- 节点名称到中文思考文案的映射表集中维护，便于国际化和管理
- 保持节点逻辑不变，仅改执行层，降低风险

**替代方案**：
- A. 在每个节点内部手动 yield thinking 事件：侵入性强，每个节点都要改，违反"一节点一文件"的现有架构
- B. 用回调函数注入：复杂度高，LangGraph 不原生支持

**节点思考文案映射**：
| 节点 | thinking 文案 |
|------|--------------|
| judge_data_requirement | 正在分析需要哪些历史数据... |
| fetch_history | 正在拉取最近的喂养记录... |
| search_vectors | 正在检索知识库中的相关知识... |
| fetch_baby_profile | 正在获取宝宝画像信息... |
| (LLM 开始) | 正在生成回答... |

### D2: Python 新增独立 tip_graph，复用共享节点

**决策**：新建 `app/graphs/tip_graph.py`，复用共享节点（judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile），新增独立的 `stream_tip_response` 节点和 `tip_answer` 提示词。

**理由**：
- 符合现有架构模式（intent_graph、clinic_graph 各自独立）
- 共享节点复用避免重复造轮子（项目约定）
- 小贴士提示词与诊疗提示词差异大，必须独立

**替代方案**：
- A. 复用 clinic_graph 换提示词：耦合度高，两个功能互相影响
- B. 在 intent_graph 加分支：职责不清，intent_graph 已有 5 种意图路由

**tip_graph 结构**：
```
TipState → judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → stream_tip_response → END
```

### D3: tip_ai 额度统一管理在 voice service，history 通过 delegate HTTP 调用

**决策**：tip_ai 额度逻辑放在 voice service（与 voice_ai/clinic_ai 统一），history service 通过 delegate HTTP 调用 voice service 的 internal API 检查和扣减额度。

**理由**：
- 用户明确要求"tip_ai 额度与其它额度统一管理，后续会增加充值功能提升全部额度上限"
- 现有 delegate HTTP 模式已有先例（`DelegateTextChat`）
- 充值功能只需改 voice service 一处，无需同步多个服务

**替代方案**：
- A. 额度逻辑放 history service：重复实现，充值功能需多处修改
- B. 抽取公共额度服务：过度设计，当前三种额度都在 voice service 管理即可

**实现**：
- voice service 新增 internal API：`/internal/quota/check?feature=tip_ai&wxId=xxx` 和 `/internal/quota/consume?feature=tip_ai&wxId=xxx`
- 复用现有 `CheckVoiceAIQuotaStore`/`ConsumeVoiceAIQuotaStore`，新增 `tip_ai` feature 校验
- `ai_quota_default` 表新增 `tip_ai_monthly_limit` 字段

### D4: 1 小时去抖用 Redis 按 deviceNo 控制

**决策**：在 history service 的 tip 生成入口，用 Redis SET NX EX 实现 1 小时去抖，key 格式 `tip:debounce:{deviceNo}`，TTL 3600 秒。

**理由**：
- Redis 已是 history service 的依赖
- SET NX EX 是原子操作，天然防并发
- TTL 方式便于后续动态调整间隔（改 TTL 即可）

**替代方案**：
- A. 数据库记录时间戳查询：有并发问题，且增加 DB 负载
- B. 内存 map：多实例不一致

### D5: 模型降级策略 - 额度足用 deepseek，不足降级 zhipu

**决策**：Go history service 调用 voice service 检查 tip_ai 额度，返回 `AIQuotaSnapshot`。若 `Allowed=true` 用 deepseek 模型；若 `Degraded=true`（额度用尽但允许降级）用 zhipu 模型；若都不满足则返回额度不足错误。

**理由**：
- 与 clinic_ai 的降级模式完全一致（参考 [ai_quota.go](file:///d:/work/go_ai_talk/internal/services/voice/ai_quota.go) 的 `CheckClinicAIQuotaSnapshot`）
- deepseek 质量高但额度有限，zhipu 作为兜底保证可用性
- `AIQuotaSnapshot.Degraded` 字段已为降级场景设计

### D6: Go history service 透传 SSE 到 Flutter

**决策**：Go history service 的 `/tip/generate` 接口接收 Flutter 请求，调用 Python `/v1/tip/stream` 获取 SSE 流，逐行透传给 Flutter。流式完成后，异步存储 tip 记录到 ai_voice_history.tip 表。

**理由**：
- Go 作为 BFF 层透传 SSE，Flutter 只需对接 Go（符合现有架构）
- 存储异步化，不阻塞 SSE 流式输出
- 流式过程中累积完整 tip_content，流结束后一次性存储

**替代方案**：
- A. Flutter 直接调 Python：绕过 Go，违反架构（Flutter 只对接 Gateway/Go）
- B. Go 先收集完整响应再返回：失去流式体验

### D7: tip 表结构设计

**决策**：在 `ai_voice_history` 库新建 `tip` 表，字段包含：id、device_no、wx_id、event_id、event_name、baby_age_months、tip_content、model_used、feedback_result、feedback_content、created_at、feedback_at。

**理由**：
- 用户明确要求存储：事件id、事件名、宝宝月龄、wx.id、tip内容、使用的模型、生成时间、反馈内容、反馈结果
- `feedback_content` 为可选文本反馈（本次仅 👍/👎，预留扩展）
- 仅 history service 可访问此库（微服务边界约束）

### D8: Flutter 小贴士组件悬浮展示+可关闭+折叠动画

**决策**：小贴士组件用 `Riverpod` 状态管理，状态为 `idle`(无内容隐藏) → `streaming`(展示+流式) → `done`(展示完整) → `closing`(折叠动画) → `idle`(隐藏)。组件以 `Stack+Positioned` 悬浮在历史记录区域上方（覆盖遮挡），背景色 alpha 0.7（能看到历史记录透出来）。右上角放 ✕ 关闭按钮，点击后触发向上折叠动画（AnimatedSize, 300ms, easeOut），动画完成后清空内容并隐藏组件。1 小时去抖过后新增事件可再次触发小贴士出现。无内容时返回 `SizedBox.shrink()` 不占位。app 重启后 provider 初始化为 `idle`，天然无展示。

**理由**：
- 用户要求"如果没有小贴士内容，则不展示小贴士组件，避免无效占位"
- 用户要求"前端不缓存小贴士内容，所以在app重启后小贴士应该处于无展示的状态"
- 用户要求"悬浮展示，圆角背景透明度0.7，右上角关闭按钮，点击动画折叠小贴士，最后删除小贴士里的内容并隐藏小贴士"
- 悬浮展示不挤占历史记录空间，体验更佳
- 可关闭+折叠动画提供更灵活的 UX，避免小贴士长期占用屏幕
- Riverpod 是项目现有状态管理方案（参考 [home_history_notifier.dart](file:///D:/work/flutter_ai_talk/app/lib/providers/home_history_notifier.dart)）

**替代方案**：
- A. Column 占位展示，不可关闭：挤占历史记录空间，UX 不佳（已废弃）
- B. 悬浮但不可关闭：小贴士长期占用屏幕，用户无法自主消除（已废弃）

### D9: 触发时机 - 监听历史 WS 新增事件

**决策**：Flutter 端在 `RemoteFeedRepository` 的 WS `onApplicationFrame` 回调中，识别新增事件（type=create），触发小贴士请求。

**理由**：
- 用户明确要求"仅指接收到历史ws事件且为新增事件时触发"
- WS 新增事件涵盖语音球和按钮添加事件两种场景
- 排除编辑（type=update）和删除（type=delete）事件

## Risks / Trade-offs

- **[风险] 每次新增事件触发 AI 调用增加 LLM 成本** → 1 小时去抖限制频率；tip_ai 额度限制月总量；zhipu 降级降低成本
- **[风险] SSE 透传链路长（Flutter→Go→Python），可能丢包或超时** → Go 侧设置合理超时（60s）；Python 侧 fallback 策略保证不中断；Flutter 侧超时后静默隐藏组件
- **[风险] tip_ai 额度扣减时机** → 参考 clinic_ai 模式：流式成功完成后扣减（`ConsumeTipAIQuota`），失败不扣
- **[风险] 去抖 key 过期后用户立即再触发** → 可接受，1 小时间隔已足够；后续可动态调整
- **[权衡] 小贴士不缓存** → 用户每次重启都无展示，但保证了内容新鲜度；去抖机制避免频繁生成
- **[权衡] 反馈按钮仅 👍/👎 无文本反馈** → 本次简化实现，feedback_content 字段预留扩展
- **[风险] clinic_graph 流式改造影响现有诊疗功能** → 仅改执行方式（ainvoke→astream），节点逻辑不变；thinking 事件不影响 answer 事件格式
