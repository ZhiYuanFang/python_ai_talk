## Context

python_ai_talk 项目当前采用独立部署模式，由自己的 `docker-compose.yml`（`build context: .`）构建镜像并通过 `--env-file` 注入环境变量。

当前环境变量命名存在「三层错配」问题：

| 层级 | 当前命名 | 实际值 |
|------|----------|--------|
| .env.* 文件 | `PYTHON_AI_TALK_REDIS_URL` | redis-test:6379 |
| docker-compose.yml 注入 | `PYTHON_AI_TALK_REDIS_URL` | ${PYTHON_AI_TALK_REDIS_URL:-} |
| python 容器内进程读取 | `REDIS_URL`（pydantic 转换） | 拿不到（fallback 到默认值） |

**根因**：docker-compose 注入的变量名（`PYTHON_AI_TALK_REDIS_URL`）与 python 应用 `settings.py` 中 pydantic 字段名（`redis_url`）转换出的环境变量名（`REDIS_URL`）不一致，导致容器内 `os.getenv("REDIS_URL")` 拿到的是空字符串，只能依赖代码中的默认值，无法实现真正的多环境差异化配置。

**兄弟仓 go_ai_talk 的设计模式**：

go 兄弟仓采用「共享变量 + 服务内重映射」：在 `manifest/docker/env/.env.test` 中定义共享变量（如 `DEEPSEEK_API_KEY`、`GF_REDIS_DEFAULT_ADDRESS`），在 `docker-compose.microservices.yml` 的 `python-ai-talk` 服务段中重映射为 `PYTHON_AI_TALK_DEEPSEEK_API_KEY`、`PYTHON_AI_TALK_REDIS_URL` 等服务专用变量，再注入到 python 容器。

但 python 项目的 settings.py 字段已是无前缀（`deepseek_api_key`、`redis_url`），如要适配 go 的「重映射」模式需要重写 settings.py，增加复杂度。

**选型**：python 项目作为独立部署的微服务，应简化设计，回归「三层完全一致」的无前缀命名。

## Goals / Non-Goals

**Goals:**

1. 实现 .env 文件、docker-compose 注入、python 应用读取三层环境变量名完全一致
2. 移除所有不必要的 `PYTHON_AI_TALK_` 前缀
3. 与兄弟仓 go_ai_talk 共享密钥时仍可使用同一份密钥值（如 `DEEPSEEK_API_KEY`、`GLM_API_KEY`）
4. 保持 `app/config/settings.py` 现状不变
5. 同步修改兄弟仓 docker-compose 中 python-ai-talk 服务的注入逻辑

**Non-Goals:**

1. 不修改 `app/config/settings.py` 字段名
2. 不修改 python 应用代码逻辑
3. 不改变 docker-compose overlay 模式（仍使用 `--env-file` 注入）
4. 不涉及 CI/CD 流程调整

## Decisions

### D1: 三层完全一致命名

**决定**：环境变量在 .env 文件、docker-compose 注入、python 应用读取三层中名字完全相同，不加前缀。

**示例**：

```bash
# env/.env.test
REDIS_URL=redis://redis-test:6379/0
DEEPSEEK_API_KEY=sk-e5685...
```

```yaml
# docker-compose.yml environment 段
REDIS_URL: ${REDIS_URL:-}
DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
```

```python
# app/config/settings.py
redis_url: str = "redis://localhost:6379/0"
deepseek_api_key: str = ""
```

**理由**：
- 消除三层错配，配置管理直观
- 与 go 兄弟仓的共享变量保持一致（如 `DEEPSEEK_API_KEY`、`GLM_API_KEY`）
- python 应用无需任何代码改动

### D2: 移除 PYTHON_AI_TALK_ 前缀

**决定**：从所有 .env 文件和 docker-compose.yml 中移除 `PYTHON_AI_TALK_` 前缀。

**影响范围**：
- `env/.env.local`、`env/.env.test`、`env/.env.prod`
- `.env.example`
- `docker-compose.yml`
- 兄弟仓 `go_ai_talk/manifest/docker/docker-compose.microservices.yml` 中 `python-ai-talk` 服务段

**理由**：
- 容器内进程只关心变量名是否符合 settings.py 定义，不需要前缀
- 共享密钥（`DEEPSEEK_API_KEY`、`GLM_API_KEY`）天然无前缀
- 其他配置项（`REDIS_URL`、`HISTORY_SERVICE_URL`）也不需要前缀

### D3: 兄弟仓 docker-compose 同步修改

**决定**：同步修改 `go_ai_talk/manifest/docker/docker-compose.microservices.yml` 中 `python-ai-talk` 服务的 environment 段，去除 `PYTHON_AI_TALK_` 前缀。

**理由**：
- python 应用读取的是无前缀变量，go 侧必须注入无前缀变量才能被正确读取
- 保持 python 项目作为独立部署的微服务的简洁性
- 兄弟仓 voice-service 中的 `PYTHON_AI_TALK_URL`（go 进程读取）保持不变

## Risks / Trade-offs

### R1: 与 go 兄弟仓的 python-ai-talk 服务嵌入部署模式冲突

**风险**：如果未来想把 python 服务嵌入 go 兄弟仓部署（通过 go 的 docker-compose 一并启动），当前去前缀后的命名规范可能与 go 项目的「重映射」模式不一致。

**缓解措施**：
- 当前 python 项目明确为独立部署模式（`build context: .`）
- 如未来需要嵌入部署，可在 go 侧重映射层处理（`PYTHON_AI_TALK_REDIS_URL: ${REDIS_URL:-}`）
- 不影响当前阶段的独立部署目标

### R2: 兄弟仓 docker-compose 改动可能影响其他服务

**风险**：兄弟仓的 `python-ai-talk` 服务段（`go_ai_talk/manifest/docker/docker-compose.microservices.yml` 行 363-381）的环境变量如果被其他脚本或工具引用，修改后可能导致引用失败。

**缓解措施**：
- 当前 `python-ai-talk` 服务是新增的，尚未在生产环境使用
- 修改前应确认无其他脚本依赖这些环境变量名

### R3: 现有 .env 文件需手动迁移

**风险**：运维人员或开发者已有的本地 .env 文件需按新格式手动重写。

**缓解措施**：
- 在 `docs/deploy-guide.md` 中明确告知变量命名变更
- 提供完整的新格式 .env.example 作为参考
- 在 changelog 或公告中说明本次 breaking change

## Migration Plan

### 阶段 1：修改 python_ai_talk 项目

1. 修改 `env/.env.local`、`env/.env.test`、`env/.env.prod`，去掉 `PYTHON_AI_TALK_` 前缀
2. 修改 `.env.example`，去掉 `PYTHON_AI_TALK_` 前缀
3. 修改 `docker-compose.yml` environment 段，去掉 `PYTHON_AI_TALK_` 前缀
4. 更新 `docs/deploy-guide.md` 环境变量清单

### 阶段 2：修改兄弟仓 go_ai_talk

1. 修改 `manifest/docker/docker-compose.microservices.yml` 中 `python-ai-talk` 服务段
2. 去除 `PYTHON_AI_TALK_REDIS_URL` → `REDIS_URL`、`PYTHON_AI_TALK_DEEPSEEK_API_KEY` → `DEEPSEEK_API_KEY` 等
3. 保留 `GF_REDIS_DEFAULT_ADDRESS`、`DEEPSEEK_API_KEY` 等共享变量引用

### 阶段 3：验证

1. 启动 python 服务并验证环境变量是否正确注入
2. 验证 python 应用是否正确读取所有配置项
3. 验证与 go 兄弟仓的连通性

### 回滚策略

如遇问题，可回退到原命名（`PYTHON_AI_TALK_` 前缀），同时回退 python 应用代码或 settings.py（增加前缀支持）。

## Open Questions

1. **是否需要在 settings.py 中增加对 `PYTHON_AI_TALK_` 前缀的兼容？**
   - 当前选择：否（保持简洁）
   - 未来如需要：可在 pydantic model 中增加 `Field(alias="PYTHON_AI_TALK_REDIS_URL")` 兼容
