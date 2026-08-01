## 1. llm_client 响应日志

- [x] 1.1 新增 `_log_response_content`（mode / provider / model + 正文，BEGIN/END 标记）
- [x] 1.2 `invoke` 成功后调用；`stream` 循环正常结束后对 `answer_buffer` 调用
- [x] 1.3 确认异常路径不误打 response；thinking 不强制打印
