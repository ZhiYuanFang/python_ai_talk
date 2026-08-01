## Context

已有 `_log_request_payload` 在 invoke/stream 调用前 INFO 打全量请求。产品确认档位 **A**：成功后打印回复文本全文即可；thinking 可不打。

## Goals / Non-Goals

**Goals:**

- invoke：成功后 INFO 打 `content` 全文
- stream：结束后 INFO 打累积回答正文一次
- 分隔标记便于检索，风格对齐 request 日志

**Non-Goals:**

- 不逐 chunk 打流式片段
- 不强制打 thinking
- 不做采样/截断开关（若日后刷屏再加配置）
- 不改业务节点零散日志

## Decisions

### 1. 抽 `_log_response_content(mode, model_config, content)`

- **选择**：与 `_log_request_payload` 并列；BEGIN/正文/END
- **理由**：invoke 与 stream 共用；检索前缀统一为 `LLM response`

### 2. Stream 在循环结束后打 `answer_buffer`

- **选择**：不打 thinking_buffer；空正文仍可打空或「(empty)」一行，避免静默
- **理由**：用户只要回复文本；空串也有助于发现空响应

### 3. 仅成功路径

- **选择**：异常仍走现有 error 日志，不打残缺 response
- **理由**：避免与失败堆栈混淆

## Risks / Trade-offs

- [INFO 刷屏 / 敏感内容] → 与 request 日志同风险；接受档位 A
- [超长回复撑爆日志系统] → 可后续加 max 长度；本 change 不截断

## Migration Plan

1. 部署后对任意 LLM 调用应出现 `--- LLM response` 标记
2. 回滚：去掉 `_log_response_content` 调用即可

## Open Questions

- 无（A 已确认）
