## ADDED Requirements

### Requirement: 三层环境变量命名完全一致
环境变量在 .env 文件、docker-compose 注入、python 应用读取三层中 SHALL 使用完全相同的变量名，不加任何服务前缀。

#### Scenario: redis URL 配置
- **WHEN** 在 env/.env.test 中定义 `REDIS_URL=redis://redis-test:6379/0`
- **THEN** docker-compose.yml 的 environment 段 SHALL 注入 `REDIS_URL: ${REDIS_URL:-}` 到容器
- **AND** python 应用通过 `os.getenv("REDIS_URL")` 或 `settings.redis_url` SHALL 正确读取到 `redis://redis-test:6379/0`

#### Scenario: DeepSeek API 密钥配置
- **WHEN** 在 env/.env.test 中定义 `DEEPSEEK_API_KEY=sk-xxx`
- **THEN** docker-compose.yml 的 environment 段 SHALL 注入 `DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}` 到容器
- **AND** python 应用通过 `settings.deepseek_api_key` SHALL 正确读取到 `sk-xxx`

### Requirement: 移除 PYTHON_AI_TALK_ 前缀
所有 .env 文件、docker-compose.yml 和兄弟仓 docker-compose.microservices.yml 中 SHALL 不得包含 `PYTHON_AI_TALK_` 前缀的环境变量。

#### Scenario: python 项目 .env 文件无前缀
- **WHEN** 运维人员查看 env/.env.test、env/.env.local、env/.env.prod
- **THEN** 文件中 SHALL NOT 出现 `PYTHON_AI_TALK_*` 形式的变量
- **AND** 所有变量名 SHALL 与 python 应用 settings.py 字段名（pydantic 转换后的大写形式）一致

#### Scenario: python 项目 docker-compose 无前缀
- **WHEN** 运维人员查看 docker-compose.yml 的 environment 段
- **THEN** 文件中 SHALL NOT 出现 `PYTHON_AI_TALK_*` 形式的变量
- **AND** environment 段 SHALL 直接引用无前缀变量，如 `REDIS_URL: ${REDIS_URL:-}`

#### Scenario: 兄弟仓 docker-compose 同步修改
- **WHEN** go_ai_talk 兄弟仓的 python-ai-talk 服务在 docker-compose.microservices.yml 中定义
- **THEN** 该服务段的 environment SHALL NOT 包含 `PYTHON_AI_TALK_*` 前缀变量
- **AND** SHALL 直接引用共享变量，如 `REDIS_URL: ${GF_REDIS_DEFAULT_ADDRESS:-redis://redis:6379/0}` 或 `DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}`

### Requirement: 共享密钥命名与兄弟仓一致
与兄弟仓 go_ai_talk 共享的密钥类环境变量 SHALL 使用无前缀的标准命名。

#### Scenario: DeepSeek 密钥跨项目共享
- **WHEN** python 项目和 go 项目都需要使用 DeepSeek API
- **THEN** 两份 .env 文件 SHALL 都使用 `DEEPSEEK_API_KEY` 作为变量名
- **AND** 变量值在测试环境和生产环境 SHALL 不同（分环境配置）

#### Scenario: GLM 密钥跨项目共享
- **WHEN** python 项目和 go 项目都需要使用智谱 GLM API
- **THEN** 两份 .env 文件 SHALL 都使用 `GLM_API_KEY` 作为变量名
- **AND** 变量值在测试环境和生产环境 SHALL 不同（分环境配置）

### Requirement: 兄弟仓 voice-service 的 PYTHON_AI_TALK_URL 保持不变
兄弟仓 go_ai_talk 中 voice-service 服务段注入的 `PYTHON_AI_TALK_URL` SHALL 保持不变，因为该变量是 voice-service（go 进程）读取的，指向 python 服务地址。

#### Scenario: go 进程调用 python 服务
- **WHEN** voice-service（go 进程）需要调用 python-ai-talk 服务的 HTTP API
- **THEN** voice-service 容器内 SHALL 有 `PYTHON_AI_TALK_URL=http://python-ai-talk:8000` 环境变量
- **AND** go 进程通过 `os.Getenv("PYTHON_AI_TALK_URL")` SHALL 正确读取到该地址

### Requirement: 环境变量清单文档化
docs/deploy-guide.md SHALL 包含完整的、无前缀的环境变量清单，并标注每个变量的用途、必填性、环境差异。

#### Scenario: 变量清单查阅
- **WHEN** 运维人员或开发者需要查阅环境变量配置
- **THEN** 文档 SHALL 提供完整变量清单表格
- **AND** 表格 SHALL 标注每个变量的本地/测试/生产示例值
- **AND** SHALL NOT 出现 `PYTHON_AI_TALK_*` 形式的变量名
