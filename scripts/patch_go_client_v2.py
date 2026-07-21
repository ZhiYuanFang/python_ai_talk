go_file = r"d:\work\go_ai_talk\internal\services\voice\python_ai_client.go"

with open(go_file, "r", encoding="utf-8") as f:
    content = f.read()

old_callback = """// ClinicStreamCallback 诊疗流式回调
// 用于将流式响应分块传递给调用方
type ClinicStreamCallback struct {
	OnThinking func(delta string) error // 收到思考过程片段时的回调
	OnAnswer   func(delta string) error // 收到回答内容片段时的回调
}"""

new_callback = """// ClinicStreamCallback 诊疗流式回调
// 用于将流式响应分块传递给调用方
type ClinicStreamCallback struct {
	OnThinking func(delta string) error // 收到思考过程片段时的回调
	OnAnswer   func(delta string) error // 收到回答内容片段时的回调
	OnDone     func(answerID string) error // 收到完成事件时的回调（包含 answer_id 用于反馈）
}"""

content = content.replace(old_callback, new_callback)

old_func_start = "func (c *PythonAIClient) ClinicStream(ctx context.Context, req *ClinicStreamRequest, cb *ClinicStreamCallback) (thinking, answer string, err error) {"

if old_func_start in content:
    func_start_idx = content.find(old_func_start)
    brace_count = 0
    func_end_idx = func_start_idx
    for i in range(func_start_idx, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                func_end_idx = i + 1
                break

    old_func = content[func_start_idx:func_end_idx]

    new_func = """// ClinicStreamResponse 诊疗流式响应结果
type ClinicStreamResponse struct {
	Thinking  string // 完整的思考过程
	Answer    string // 完整的回答内容
	AnswerID  string // 回答 ID（用于提交反馈）
}

func (c *PythonAIClient) ClinicStream(ctx context.Context, req *ClinicStreamRequest, cb *ClinicStreamCallback) (*ClinicStreamResponse, error) {
	// 将请求体序列化为 JSON
	body, _ := json.Marshal(req)

	// 创建 HTTP POST 请求，要求流式响应
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/v1/clinic/stream", strings.NewReader(string(body)))
	if err != nil {
		return nil, fmt.Errorf("创建诊疗流式请求失败: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("调用 Python 诊疗流式服务失败: %w", err)
	}
	defer resp.Body.Close()

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Python 诊疗流式服务返回错误状态码 %d: %s", resp.StatusCode, string(respBody))
	}

	// 逐行解析 SSE 响应
	var thinking, answer, answerID string
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		// SSE 格式：每行以 "data: " 开头
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		// 提取 data 后面的 JSON 内容
		data := strings.TrimPrefix(line, "data: ")
		var event struct {
			Type     string `json:"type"`      // 消息类型：thinking、answer、done
			Content  string `json:"content"`   // 内容片段
			AnswerID string `json:"answer_id"` // 回答 ID（done 事件时返回）
		}
		if err := json.Unmarshal([]byte(data), &event); err != nil {
			continue // 跳过无法解析的行
		}
		// 根据类型分发到对应回调
		switch event.Type {
		case "thinking":
			// 累积思考过程
			thinking += event.Content
			if cb != nil && cb.OnThinking != nil {
				if cbErr := cb.OnThinking(event.Content); cbErr != nil {
					return &ClinicStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		case "answer":
			// 累积回答内容
			answer += event.Content
			if cb != nil && cb.OnAnswer != nil {
				if cbErr := cb.OnAnswer(event.Content); cbErr != nil {
					return &ClinicStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		case "done":
			// 记录回答 ID，用于后续反馈
			answerID = event.AnswerID
			if cb != nil && cb.OnDone != nil {
				if cbErr := cb.OnDone(event.AnswerID); cbErr != nil {
					return &ClinicStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		}
	}

	return &ClinicStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, scanner.Err()
}"""

    content = content[:func_start_idx] + new_func + content[func_end_idx:]

additional_code = """

// TipStreamRequest 小贴士流式请求体
// 与 Python 服务的 /v1/tip/stream 接口对齐
type TipStreamRequest struct {
	EventID        string         `json:"event_id"`         // 触发事件 ID
	EventName      string         `json:"event_name"`       // 触发事件名称
	DeviceNo       string         `json:"device_no"`        // 设备编号
	BabyAgeMonths  int            `json:"baby_age_months"`  // 宝宝月龄
	CurrentTime    string         `json:"current_time"`     // 当前时间（ISO 格式）
	Model          PythonModelCfg `json:"model"`            // 模型配置
}

// TipStreamCallback 小贴士流式回调
type TipStreamCallback struct {
	OnThinking func(delta string) error // 收到思考过程片段时的回调
	OnAnswer   func(delta string) error // 收到回答内容片段时的回调
	OnDone     func(answerID string) error // 收到完成事件时的回调（包含 answer_id 用于反馈）
}

// TipStreamResponse 小贴士流式响应结果
type TipStreamResponse struct {
	Thinking  string // 完整的思考过程
	Answer    string // 完整的回答内容
	AnswerID  string // 回答 ID（用于提交反馈）
}

// TipStream 调用 Python 服务进行流式小贴士生成
// ctx: 上下文
// req: 小贴士请求
// cb: 流式回调
// 返回：小贴士流式响应结果和错误
func (c *PythonAIClient) TipStream(ctx context.Context, req *TipStreamRequest, cb *TipStreamCallback) (*TipStreamResponse, error) {
	// 将请求体序列化为 JSON
	body, _ := json.Marshal(req)

	// 创建 HTTP POST 请求，要求流式响应
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/v1/tip/stream", strings.NewReader(string(body)))
	if err != nil {
		return nil, fmt.Errorf("创建小贴士流式请求失败: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("调用 Python 小贴士流式服务失败: %w", err)
	}
	defer resp.Body.Close()

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Python 小贴士流式服务返回错误状态码 %d: %s", resp.StatusCode, string(respBody))
	}

	// 逐行解析 SSE 响应
	var thinking, answer, answerID string
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		data := strings.TrimPrefix(line, "data: ")
		var event struct {
			Type     string `json:"type"`      // 消息类型：thinking、answer、done
			Content  string `json:"content"`   // 内容片段
			AnswerID string `json:"answer_id"` // 回答 ID（done 事件时返回）
		}
		if err := json.Unmarshal([]byte(data), &event); err != nil {
			continue
		}
		switch event.Type {
		case "thinking":
			thinking += event.Content
			if cb != nil && cb.OnThinking != nil {
				if cbErr := cb.OnThinking(event.Content); cbErr != nil {
					return &TipStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		case "answer":
			answer += event.Content
			if cb != nil && cb.OnAnswer != nil {
				if cbErr := cb.OnAnswer(event.Content); cbErr != nil {
					return &TipStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		case "done":
			answerID = event.AnswerID
			if cb != nil && cb.OnDone != nil {
				if cbErr := cb.OnDone(event.AnswerID); cbErr != nil {
					return &TipStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, cbErr
				}
			}
		}
	}

	return &TipStreamResponse{Thinking: thinking, Answer: answer, AnswerID: answerID}, scanner.Err()
}

// FeedbackRequest 反馈请求体
// 与 Python 服务的 /v1/clinic/feedback 和 /v1/tip/feedback 接口对齐
type FeedbackRequest struct {
	AnswerID string `json:"answer_id"` // 回答 ID（来自流式响应的 done 事件）
	Feedback int    `json:"feedback"`  // 反馈值：1=thumbs up, -1=thumbs down
}

// FeedbackResponse 反馈响应体
type FeedbackResponse struct {
	Code    int    `json:"code"`    // 状态码：0=成功
	Message string `json:"message"` // 提示信息
	Data    struct {
		AnswerID string `json:"answer_id"` // 回答 ID
		Feedback int    `json:"feedback"`  // 反馈值
	} `json:"data"`
}

// ClinicFeedback 提交诊疗反馈
// ctx: 上下文
// req: 反馈请求
// 返回：反馈响应和错误
func (c *PythonAIClient) ClinicFeedback(ctx context.Context, req *FeedbackRequest) (*FeedbackResponse, error) {
	return c.submitFeedback(ctx, "/v1/clinic/feedback", req)
}

// TipFeedback 提交小贴士反馈
// ctx: 上下文
// req: 反馈请求
// 返回：反馈响应和错误
func (c *PythonAIClient) TipFeedback(ctx context.Context, req *FeedbackRequest) (*FeedbackResponse, error) {
	return c.submitFeedback(ctx, "/v1/tip/feedback", req)
}

// submitFeedback 提交反馈的通用方法
func (c *PythonAIClient) submitFeedback(ctx context.Context, path string, req *FeedbackRequest) (*FeedbackResponse, error) {
	// 将请求体序列化为 JSON
	body, _ := json.Marshal(req)

	// 创建 HTTP POST 请求
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+path, strings.NewReader(string(body)))
	if err != nil {
		return nil, fmt.Errorf("创建反馈请求失败: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("调用 Python 反馈服务失败: %w", err)
	}
	defer resp.Body.Close()

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Python 反馈服务返回错误状态码 %d: %s", resp.StatusCode, string(respBody))
	}

	// 解析响应体
	var result FeedbackResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("解析反馈响应失败: %w", err)
	}

	glog.Debugf(ctx, "[Python AI] 反馈提交完成。path=%s answer_id=%s feedback=%d", path, req.AnswerID, req.Feedback)
	return &result, nil
}"""

content = content + additional_code

content = content.replace(
    "func pythonAIClientFromCfg() *PythonAIClient {",
    "func PythonAIClientFromCfg() *PythonAIClient {"
)

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Go client v2 updated successfully!")
