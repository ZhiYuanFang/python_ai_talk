## ADDED Requirements

### Requirement: 新增事件触发小贴士生成
系统 SHALL 在 Flutter 端接收到历史 WebSocket 新增事件通知（type=create）时，自动触发小贴士生成请求。编辑事件（type=update）和删除事件（type=delete）SHALL NOT 触发小贴士。

#### Scenario: 按钮新增事件触发小贴士
- **WHEN** 用户通过事件按钮新增一条喂养记录，Flutter 端收到 WS 新增事件通知
- **THEN** 系统 SHALL 自动发起小贴士生成请求到 Go history service 的 `/tip/generate` 接口

#### Scenario: 语音球新增事件触发小贴士
- **WHEN** 用户通过语音球对话触发新增事件，Flutter 端收到 WS 新增事件通知
- **THEN** 系统 SHALL 自动发起小贴士生成请求到 Go history service 的 `/tip/generate` 接口

#### Scenario: 编辑事件不触发小贴士
- **WHEN** 用户编辑已有历史记录，Flutter 端收到 WS 更新事件通知（type=update）
- **THEN** 系统 SHALL NOT 发起小贴士生成请求

### Requirement: 1 小时去抖控制
Go history service SHALL 基于 Redis 按 `deviceNo` 控制小贴士触发频率，1 小时内仅触发一次。去抖间隔 SHALL 可通过配置动态调整。

#### Scenario: 首次触发成功
- **WHEN** 设备 deviceNo=A 首次请求小贴士生成
- **THEN** Go history service SHALL 在 Redis 中设置 key `tip:debounce:A`（TTL 3600 秒），并继续执行小贴士生成流程

#### Scenario: 1 小时内重复触发被拦截
- **WHEN** 设备 deviceNo=A 在 1 小时内再次请求小贴士生成
- **THEN** Go history service SHALL 返回去抖拦截响应，不执行小贴士生成流程

#### Scenario: 1 小时后去抖过期可再次触发
- **WHEN** 设备 deviceNo=A 的去抖 key 过期后再次请求小贴士生成
- **THEN** Go history service SHALL 重新设置去抖 key 并执行小贴士生成流程

### Requirement: tip_ai 额度统一管理
系统 SHALL 在 voice service 新增 `tip_ai` 额度类型，与 `voice_ai`/`clinic_ai` 统一管理。history service SHALL 通过 delegate HTTP 调用 voice service 检查和扣减 tip_ai 额度。

#### Scenario: 额度充足使用 deepseek 模型
- **WHEN** Go history service 检查 tip_ai 额度，返回 `Allowed=true`
- **THEN** 系统 SHALL 使用 deepseek 模型调用 Python 小贴士生成接口

#### Scenario: 额度用尽降级使用 zhipu 模型
- **WHEN** Go history service 检查 tip_ai 额度，返回 `Degraded=true`（额度用尽但允许降级）
- **THEN** 系统 SHALL 使用 zhipu 模型调用 Python 小贴士生成接口

#### Scenario: 额度完全不足拒绝请求
- **WHEN** Go history service 检查 tip_ai 额度，返回 `Allowed=false` 且 `Degraded=false`
- **THEN** 系统 SHALL 返回额度不足错误，不执行小贴士生成

#### Scenario: 流式成功完成后扣减额度
- **WHEN** Python 小贴士 SSE 流式输出成功完成
- **THEN** Go history service SHALL 调用 voice service 扣减 tip_ai 额度；流式失败时 SHALL NOT 扣减

### Requirement: Python tip_graph 生成小贴士
Python 服务 SHALL 新增 `tip_graph` 状态图，复用共享节点（judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile），新增独立的提示词和流式生成节点，通过 `/v1/tip/stream` SSE 接口返回思考过程和结果。

#### Scenario: tip_graph 编排小贴士生成流程
- **WHEN** Go history service 调用 Python `/v1/tip/stream` 接口，传入事件信息、设备编号、模型配置
- **THEN** Python SHALL 执行 tip_graph：judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → stream_tip_response，并流式返回 thinking 和 answer 事件

#### Scenario: 小贴士内容结合多维上下文
- **WHEN** tip_graph 的 stream_tip_response 节点生成小贴士
- **THEN** 生成的 SHALL 内容结合：当前触发事件 + 当前时间 + 宝宝月龄 + 知识库同月龄宝宝参考 + 近期喂养历史记录参考，输出针对当前事件的当下总结和下一步注意事项

### Requirement: Go history service 透传 SSE 并存储
Go history service SHALL 调用 Python `/v1/tip/stream` 获取 SSE 流，逐行透传给 Flutter。流式完成后 SHALL 异步存储 tip 记录到 `ai_voice_history.tip` 表。

#### Scenario: SSE 透传
- **WHEN** Flutter 请求 Go `/tip/generate` 接口
- **THEN** Go history service SHALL 调用 Python SSE 接口，将 thinking 和 answer 事件逐行透传给 Flutter，保持 SSE 格式不变

#### Scenario: 流式完成后存储 tip 记录
- **WHEN** Python SSE 流式输出完成（收到 [DONE]）
- **THEN** Go history service SHALL 将累积的完整 tip_content、event_id、event_name、baby_age_months、model_used、wx_id、created_at 存储到 ai_voice_history.tip 表

### Requirement: Flutter 小贴士组件悬浮展示与关闭
Flutter SHALL 以 Stack+Positioned 方式将小贴士组件悬浮在历史记录区域上方（覆盖遮挡），背景色 alpha 0.7（能看到历史记录透出来）。无内容时 SHALL NOT 展示组件（不占位）。小贴士内容 SHALL NOT 缓存，app 重启后 SHALL 处于无展示状态。右上角 SHALL 放关闭按钮（✕），点击后触发向上折叠动画（300ms），动画完成后清空内容并隐藏组件。

#### Scenario: 无内容时隐藏组件
- **WHEN** 小贴士状态为 idle（无内容）
- **THEN** Flutter SHALL 返回 `SizedBox.shrink()`，不占用任何空间

#### Scenario: 悬浮展示小贴士
- **WHEN** 小贴士状态为 streaming 或 done
- **THEN** Flutter SHALL 以 Stack+Positioned 方式悬浮在历史记录区域上方，背景色 alpha 0.7，最大高度 200，可滚动，自动滚动到底部显示最新内容

#### Scenario: app 重启后无展示
- **WHEN** 用户重启 app
- **THEN** 小贴士 provider SHALL 初始化为 idle 状态，不展示任何小贴士内容

#### Scenario: 点击关闭按钮触发折叠动画
- **WHEN** 用户点击小贴士右上角的 ✕ 关闭按钮
- **THEN** Flutter SHALL 触发向上折叠动画（AnimatedSize, 300ms, easeOut），高度从当前值收缩到 0，顶部不动

#### Scenario: 折叠动画完成后清空内容并隐藏
- **WHEN** 向上折叠动画完成
- **THEN** Flutter SHALL 清空小贴士内容（thinking/answer 置空），状态切回 idle，组件隐藏返回 SizedBox.shrink()

#### Scenario: 关闭后可再次触发
- **WHEN** 用户关闭小贴士后，1 小时去抖已过，再次新增事件
- **THEN** 小贴士 SHALL 再次出现，重新走 streaming → done 流程

### Requirement: 小贴士展示样式与诊疗一致
Flutter 小贴士组件的展示样式 SHALL 与诊疗界面中的单次回答一致，使用相同的 Markdown 渲染和流式文本展示逻辑。

#### Scenario: 流式阶段纯文本展示
- **WHEN** 小贴士正在流式接收（streaming 状态）
- **THEN** Flutter SHALL 以纯文本形式展示流式内容（与诊疗流式阶段一致）

#### Scenario: 完成后 Markdown 格式化
- **WHEN** 小贴士流式接收完成（done 状态）
- **THEN** Flutter SHALL 以 Markdown 格式化展示完整内容（复用 ClinicAnswerBody 组件逻辑）
