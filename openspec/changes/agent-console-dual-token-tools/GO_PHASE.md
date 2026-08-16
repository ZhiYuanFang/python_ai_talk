# Go 二期接入清单（任务 7.x）

本仓 Python 门禁与控制台就绪后，在兄弟仓 `go_ai_talk` 执行：

1. 配置键拆分：
   - `OPENCLAW_GATEWAY_URL` → 指向 Python `/agent-gate`（或等价反代）
   - `OPENCLAW_GATEWAY_TOKEN` → **G**
   - `PANGBAO_API_TOKEN` → **A**（请求头 `x-pangbao-api-token`）
2. OpenClaw HTTP 客户端：Bearer 用 G；额外头传 A、`x-openclaw-model`、`x-openclaw-session-key`。
3. 验收：G 失效 → 401；无 A → history tools 失败；控制台配好胖宝 Go URL 后主路径通。

（本 change apply 不在 python_ai_talk 内直接改 Go 代码，除非工作区同时打开兄弟仓。）
