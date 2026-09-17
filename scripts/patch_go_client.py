import re

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

old_func = """// ClinicStream 调用 Python 服务进行流式诊疗
// ctx: 上下文
// req: 诊疗请求
// cb: 流式回调
// 返回：完整的思考过程、完整的回答内容、错误
func (c *PythonAIClient) ClinicStream(ctx context.Context, req *ClinicStreamRequest, cb *ClinicStreamCallback) (thinking, answer string, err error) {
	// 将请求体序列化为 JSON
	body, _ := json.Marshal(req)

	// 创建 HTTP POST 请求，要求流式响应
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/v1/clinic/stream", strings.NewReader(string(body)))
	if err != nil {
		return "", "", fmt.Errorf("创建诊疗流式请求失败: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return "", "", fmt.Errorf("调用 Python 诊疗流式服务失败: %w", err)
	}
	defer resp.Body.Close()

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return "", "", fmt.Errorf("Python 诊疗流式服务返回错误状态码 %d: %s", resp.StatusCode, string(respBody))
	}

	// 逐行解析 SSE 响应
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
			Type    string `json:"type"`    // 消息类型：thinking 或 answer
			Content string `json:"content"` // 内容片段
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
					return thinking, answer, cbErr
				}
			}
		case "answer":
			// 累积回答内容
			answer += event.Content
			if cb != nil && cb.OnAnswer != nil {
				if cbErr := cb.OnAnswer(event.Content); cbErr != nil {
					return thinking, answer, cbErr
				}
			}
		}
	}

	return thinking, answer, scanner.Err()
}"""

new_func = """// ClinicStreamResponse 诊疗流式响应结果
type ClinicStreamResponse struct {
	Thinking  string // 完整的思考过程
	Answer    string // 完整的回答内容
	AnswerID  string // 回答 ID（用于提交反馈）
}

// ClinicStream 调用 Python 服务进行流式诊疗
// ctx: 上下文
// req: 诊疗请求
// cb: 流式回调
// 返回：诊疗流式响应结果和错误
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

content = content.replace(old_func, new_func)

additional_code = ""  # tip/TipFeedback ????????

content = content + additional_code

with open(go_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Go client updated successfully!")
