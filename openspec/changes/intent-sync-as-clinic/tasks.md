## 1. 非流式路由改 clinic

- [x] 1.1 将 `analyze_intent` 改为调用 `call_clinic_agent`（预设 conversation/reply），用返回的 `intent_result` 构建 `IntentResponse`
- [x] 1.2 移除该 handler 内 pending / 父消歧 / `_run_cold_intent` 调用；更新文件头与函数中文注释说明非流式语义
- [x] 1.3 确认 `/intent/stream` 仍走原意图图逻辑未改
