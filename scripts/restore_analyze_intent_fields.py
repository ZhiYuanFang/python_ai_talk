go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

old_struct = """type AnalyzeIntentResponse struct {
    TargetType string   `json:"target_type"` // 目标类型：feeding|history|suggest|conversation|exit
    Action     string   `json:"action"`      // 动作类型：start|end|one|search|suggestion|reply|exit
    EventName  string   `json:"event_name"`  // 匹配到的事件名称（喂养场景）
    Keywords   []string `json:"keywords"`    // 匹配到的关键词列表
    Content    string   `json:"content"`     // 对话场景的回答内容
    NeedConfirm    bool   `json:"need_confirm"`    // 是否需要用户确认（Python 图执行中断，等待用户 confirm/reject 后恢复）
    ConfirmMessage string `json:"confirm_message"` // 确认提示话术（由 Python 侧生成，引导用户回复确认或取消）
    ConversationID string `json:"conversation_id"` // 会话 ID（用于调用 /v1/analyze/intent/confirm 恢复图执行）
}"""

new_struct = """// IntentEvent 单个事件结构
// 用于描述多事件场景中的单个事件
type IntentEvent struct {
	Action    string `json:"action"`
	EventName string `json:"event_name"`
	EventId   string `json:"event_id"`
	Quantity  *int   `json:"quantity,omitempty"` // 从用户输入中提取的数量值
}

type AnalyzeIntentResponse struct {
    TargetType string       `json:"target_type"` // 目标类型：feeding|history|suggest|conversation|exit
    Action     string       `json:"action"`      // 动作类型：start|end|one|search|suggestion|reply|exit|multi
    EventName  string       `json:"event_name"`  // 匹配到的事件名称（喂养场景，单事件时使用）
    EventId    string       `json:"event_id"`    // 事件ID（单事件时使用）
    Quantity   *int         `json:"quantity,omitempty"`   // 从用户输入中提取的数量值（Python 前置提取）
    EventType  string       `json:"event_type,omitempty"`  // 事件类型：number|time|one（新事件时 Python 返回）
    EventUnit  string       `json:"event_unit,omitempty"`  // 事件单位：ml、次、分钟（新事件时 Python 返回）
    IsNewEvent bool         `json:"is_new_event,omitempty"` // 是否为新事件
    Keywords   []string     `json:"keywords"`    // 匹配到的关键词列表
    Content    string       `json:"content"`     // 对话场景的回答内容
    Events     []IntentEvent `json:"events"`     // 多事件列表（当 action 为 multi 时使用）
    NeedConfirm    bool     `json:"need_confirm"`    // 是否需要用户确认（Python 图执行中断，等待用户 confirm/reject 后恢复）
    ConfirmMessage string   `json:"confirm_message"` // 确认提示话术（由 Python 侧生成，引导用户回复确认或取消）
    ConversationID string   `json:"conversation_id"` // 会话 ID（用于调用 /v1/analyze/intent/confirm 恢复图执行）
}"""

content = content.replace(old_struct, new_struct)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("AnalyzeIntentResponse fields restored successfully!")
