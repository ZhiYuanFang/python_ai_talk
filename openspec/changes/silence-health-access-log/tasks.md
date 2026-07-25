## 1. Access Log Filter

- [x] 1.1 在 `app/main.py` 实现 `logging.Filter`，当记录消息包含 `/v1/health` 时返回 `False`
- [x] 1.2 在模块级日志初始化处将 Filter 挂到 `logging.getLogger("uvicorn.access")`

## 2. Verification

- [x] 2.1 启动服务后请求 `/v1/health`，确认无对应 uvicorn access 行，且响应仍为 healthy
- [x] 2.2 请求任意非 health 业务接口，确认 access log 仍正常输出
