# confirm 接口适配需求文档

## 调研结论概述

| 兄弟仓 | 是否需要适配 | 适配复杂度 |
|--------|-------------|-----------|
| go_ai_talk | **需要** | 中等 |
| flutter_ai_talk | **需要** | 中等 |

---

## go_ai_talk 适配需求

### 当前问题

go_ai_talk 的 `AnalyzeIntentResponse` 结构体**缺少 `need_confirm`、`confirm_message`、`conversation_id` 字段**，导致 python 返回的确认信息被 JSON 解码时丢弃，用户确认环节被跳过。

### 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `internal/services/voice/python_ai_client.go` | 1. `AnalyzeIntentResponse` 增加 `NeedConfirm`、`ConfirmMessage`、`ConversationID` 字段；2. 新增 `ConfirmIntentRequest` 结构体和 `ConfirmIntent` 方法（POST `/v1/analyze/intent/confirm`） |
| `internal/services/voice/voice_chat_understanding.go` | 1. `deepSeekUnifiedIntent` 结构体增加 3 个新字段；2. `callDeepSeekUnifiedIntent` 映射新字段；3. 上游增加 `need_confirm` 分支：返回确认话术，持久化 `conversation_id` 到 Redis；4. 入口处检查待确认状态 |
| Redis key 配置文件 | 新增 `voice:confirm:pending:{deviceNo}` → `conversation_id`，TTL 60秒 |

### 适配流程

```
用户输入 → 检查 Redis 待确认状态
  ├─ 有待确认状态 → 调用 /v1/analyze/intent/confirm
  │   ├─ 用户确认 → 执行落库
  │   └─ 用户取消 → 返回取消提示
  └─ 无待确认状态 → 调用 /v1/analyze/intent
      └─ need_confirm=true → 返回确认话术，存入 Redis
```

---

## flutter_ai_talk 适配需求

### 当前问题

flutter_ai_talk **完全没有意图分析相关代码**，当前 AI 聊天仅通过 `sendCommand(text)` 获取单条文本回复，不处理 `need_confirm` 等字段。

### 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `app/lib/data/feed_repository.dart` | 新增 `analyzeIntent` 和 `confirmIntent` 方法签名 |
| `app/lib/data/remote_feed_repository.dart` | 实现 `analyzeIntent`（POST `/device/history/api/ai/intent`）和 `confirmIntent`（POST `/device/history/api/ai/confirm`） |
| 新建 `app/lib/data/intent_analyze_models.dart` | 定义 `IntentAnalyzeResult` 模型 |
| `app/lib/ui/home_screen.dart` | 在 `_send()` 前插入意图分析调用，`need_confirm=true` 时弹窗确认 |

### 适配流程

```
用户输入 → analyzeIntent(text)
  ├─ need_confirm=false → 直接执行目标动作
  └─ need_confirm=true → showGlassConfirmDialog
      ├─ 用户确认 → confirmIntent(token, accept:true) → 执行
      └─ 用户取消 → confirmIntent(token, accept:false) → 取消
```

---

## python 侧需要补充的内容

调研发现 python 侧 `IntentResponse` **缺少 `conversation_id` 字段**，Go 侧即使适配了也无从获得 `conversation_id` 来调用 confirm 接口。

**需要修改**：`app/feeding/schemas/intent.py` 的 `IntentResponse` 增加 `conversation_id` 字段，并在 `analyze_intent` 路由中赋值。

---

## 跨仓协同建议

1. **优先推动 python 侧补全 `conversation_id` 字段**
2. **go_ai_talk 采用最小侵入式改造**：只在主入口加 `need_confirm` 分支
3. **flutter_ai_talk 复用现有 `showGlassConfirmDialog` 组件**
4. **向后兼容**：python 侧 `need_confirm` 默认 false，未升级的客户端不受影响
