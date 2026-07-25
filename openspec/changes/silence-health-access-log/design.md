## Context

服务通过 Docker healthcheck 每 10 秒请求 `GET /v1/health`。uvicorn 默认将所有 HTTP 请求写入 `uvicorn.access` logger，导致控制台被健康检查刷屏。`health.py` 路由本身不产生业务日志；噪音完全来自 access log 层。应用有两条启动路径（`python -m app.main` 的 `uvicorn.run`，以及 Dockerfile `CMD ["uvicorn", ...]`），过滤逻辑需在应用进程内生效，覆盖两者。

## Goals / Non-Goals

**Goals:**

- 精准丢弃针对健康检查路径的 uvicorn access log
- 保留其余接口的 access log
- 本地与 Docker 启动路径行为一致
- 改动面小、无新依赖

**Non-Goals:**

- 不修改 `/v1/health` 响应契约或 Docker healthcheck 配置
- 不关闭全部 access log（`--no-access-log`）
- 不按 HTTP status 区分（成功与失败的 health 探测均静音）
- 不静音 `/docs`、`/openapi.json` 等其他探测路径（除非后续明确扩展）

## Decisions

### 决策 1：用 logging.Filter 过滤 `uvicorn.access`，而非改路由或关 access log

- **选择**：自定义 `logging.Filter`，挂到 `logging.getLogger("uvicorn.access")`，当 log message 包含健康检查路径时返回 `False`
- **理由**：不改 API、不丢业务 access log；与 uvicorn 内置机制兼容
- **备选**：
  - `--no-access-log`：过于粗暴，拒绝
  - 自定义 Middleware 重写 access 日志：成本高、重复造轮子，拒绝
  - 改 `health.py`：路由无法控制 uvicorn access logger，无效

### 决策 2：在 `app/main.py` 日志初始化处注册 Filter

- **选择**：在现有 `logging.basicConfig(...)` 附近（模块加载时）注册 Filter
- **理由**：`app.main` 无论被 `uvicorn.run("app.main:app")` 还是 `uvicorn app.main:app` 导入，模块级代码都会执行，两条启动路径均覆盖
- **备选**：仅在 `uvicorn.run(..., log_config=...)` 传入自定义 dictConfig —— Docker CMD 不会走该分支，拒绝作为唯一方案

### 决策 3：匹配路径为 `/v1/health`（含子串安全边界）

- **选择**：Filter 检查 access log 消息中是否包含 `/v1/health`（uvicorn 默认格式形如 `"GET /v1/health HTTP/1.1"`）
- **理由**：与当前路由前缀 `/v1` + `/health` 一致；实现简单稳定
- **备选**：解析完整 request line 做精确 path match —— 更严谨但对本场景收益有限；若后续出现假阳性再升级

### 决策 4：Filter 实现位置

- **选择**：优先在 `main.py` 内联小型 Filter 类（或同文件私有函数），保持改动集中
- **备选**：抽到 `app/shared/logging_filters.py` —— 仅当后续还有更多路径过滤需求时再抽

## Risks / Trade-offs

- [Health 失败也静音] → 健康检查失败时 access log 不会出现；依赖 Docker healthcheck 状态与应用业务 ERROR 日志排查。可接受，因 health 本身几乎无失败路径。
- [路径子串误匹配] → 若未来有路径包含 `/v1/health` 作为前缀（如 `/v1/healthz`），可能被误静音。当前无此类路由；匹配时可要求前后为引号/空格/HTTP 边界以降低风险。
- [Filter 注册时机] → 若在 uvicorn 创建 access logger 之前注册，一般仍生效（logger 单例）；若极端情况下失效，可改为 `startup` 钩子中再挂一次（幂等）。

## Migration Plan

1. 部署含 Filter 的新版本
2. 观察容器日志：healthcheck 周期内不再出现 `/v1/health` access 行；业务请求仍有 access log
3. 回滚：回退镜像即可，无数据迁移

## Open Questions

- 无。范围已定为仅静音 `/v1/health`，成功与失败均过滤。
