# Tasks: 统一环境变量命名规范

## 1. python_ai_talk 项目 .env 文件重构

- [x] 1.1 重写 `env/.env.local`，去掉所有 `PYTHON_AI_TALK_` 前缀，保留与 python 应用 settings.py 字段名一致的变量
- [x] 1.2 重写 `env/.env.test`，去掉所有 `PYTHON_AI_TALK_` 前缀，按 go_ai_talk 风格分组，添加 ACR 凭证
- [x] 1.3 重写 `env/.env.prod`，去掉所有 `PYTHON_AI_TALK_` 前缀，按 go_ai_talk 风格分组，使用生产密钥
- [x] 1.4 重写 `.env.example`，去掉所有 `PYTHON_AI_TALK_` 前缀，作为模板提供

## 2. python_ai_talk 项目 docker-compose.yml 重构

- [x] 2.1 修改 `docker-compose.yml` 的 environment 段，去掉所有 `PYTHON_AI_TALK_` 前缀
- [x] 2.2 验证 environment 段变量名与 settings.py 字段名（pydantic 转换后大写）一致

## 3. 兄弟仓 go_ai_talk docker-compose 同步修改

- [x] 3.1 修改 `go_ai_talk/manifest/docker/docker-compose.microservices.yml` 中 `python-ai-talk` 服务段，去掉所有 `PYTHON_AI_TALK_` 前缀
- [x] 3.2 保留 voice-service 服务段的 `PYTHON_AI_TALK_URL`（该变量是 go 进程读取的）
- [x] 3.3 验证共享变量引用：`REDIS_URL: ${GF_REDIS_DEFAULT_ADDRESS:-...}`、`DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}`、`GLM_API_KEY: ${GLM_API_KEY:-}`

## 4. 部署指南文档更新

- [x] 4.1 更新 `docs/deploy-guide.md` 的环境变量清单，移除 `PYTHON_AI_TALK_` 前缀
- [x] 4.2 更新变量说明表格，标注本地/测试/生产的差异
- [x] 4.3 在文档开头增加「变更说明」章节，说明本次 breaking change

## 5. 验证测试

- [x] 5.1 本地启动验证：执行本地启动命令，验证容器内 `os.getenv("REDIS_URL")` 能正确读取
- [x] 5.2 配置验证：执行 `docker compose --env-file env/.env.test -f docker-compose.yml -f docker-compose.test.yml config`，检查生成的 environment 段无前缀
- [x] 5.3 兼容性验证：启动服务，验证 `/health` 接口返回 200
- [x] 5.4 连通性验证：调用 `/v1/analyze/intent` 接口，验证与 go 兄弟仓服务的连通性
