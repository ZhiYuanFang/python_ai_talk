## Why

Docker healthcheck 每 10 秒探测一次 `/v1/health`，uvicorn access log 随之刷屏，淹没真实业务请求日志。健康检查路由本身不打业务日志，噪音来自访问日志层，需要在不关闭全部 access log 的前提下精准静音 health 探测。

## What Changes

- 为 `uvicorn.access` 增加路径过滤器，丢弃针对 `/v1/health`（及等价路径）的 access log
- 在应用启动时挂载该过滤器，使 `python -m app.main` 与 Docker `uvicorn` CMD 两条启动路径均生效
- 不修改 health 路由行为、响应体或 healthcheck 配置；不关闭其他接口的 access log

## Capabilities

### New Capabilities
- `access-log-filter`: 按路径过滤 uvicorn access log，使健康检查探测不写入访问日志，同时保留业务接口访问记录

### Modified Capabilities

## Impact

- 主要改动点：`app/main.py`（日志初始化 / 启动时注册 Filter）
- 可能新增小型 Filter 类或辅助模块（若希望与 `main.py` 解耦）
- 不影响 API 契约、Docker healthcheck、路由注册
- 无新依赖；无 BREAKING 变更
