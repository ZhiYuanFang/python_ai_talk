## Why

当前 python_ai_talk 项目独立部署模式下，环境变量命名存在「三层错配」问题。.env 文件定义 `PYTHON_AI_TALK_REDIS_URL`，docker-compose 注入 `PYTHON_AI_TALK_REDIS_URL`，但 python 应用代码读 `REDIS_URL`。三层名字不一致导致容器内进程实际读不到配置，只能依赖默认值 fallback，无法真正实现多环境差异化配置。

python 项目作为独立部署的微服务，应采用「三层完全一致」的无前缀命名规范，简化配置管理并消除错配风险。

## What Changes

- 移除 `env/.env.local`、`env/.env.test`、`env/.env.prod` 中所有变量的 `PYTHON_AI_TALK_` 前缀
- 移除 `docker-compose.yml` 中 environment 段所有变量的 `PYTHON_AI_TALK_` 前缀
- 移除 `.env.example` 中所有变量的 `PYTHON_AI_TALK_` 前缀
- 同步修改兄弟仓 go_ai_talk 的 `python-ai-talk` 服务环境变量注入
- 保持 `app/config/settings.py` 现有字段名（已是无前缀）
- 更新 `docs/deploy-guide.md` 环境变量清单

## Capabilities

### New Capabilities

- env-config: 规范 python_ai_talk 项目环境变量的命名规则，三层（.env、docker-compose、python 应用）统一无前缀命名

### Modified Capabilities

（无现有能力修改）

## Impact

**修改文件：**

python_ai_talk:
- env/.env.local
- env/.env.test
- env/.env.prod
- .env.example
- docker-compose.yml
- docs/deploy-guide.md

go_ai_talk 兄弟仓:
- manifest/docker/docker-compose.microservices.yml（python-ai-talk 服务段）

**未修改文件：**
- app/config/settings.py（已是无前缀字段）
- app/services/*.py（通过 settings 间接读取）

**部署影响：**
- 现有 .env.* 文件需按新格式重写
- python 容器需重启以应用新环境变量
- go 兄弟仓的 python-ai-talk 服务需重新部署
