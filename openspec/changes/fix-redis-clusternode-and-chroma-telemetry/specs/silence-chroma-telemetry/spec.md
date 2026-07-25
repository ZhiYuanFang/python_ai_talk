## ADDED Requirements

### Requirement: 静音 chromadb posthog telemetry ERROR
系统 SHALL 防止 `chromadb.telemetry.product.posthog` 在向量查询/更新时以 ERROR 级别刷屏（含 `capture() takes 1 positional argument but 3 were given`）。

#### Scenario: 启动后 logger 级别足够高
- **WHEN** 应用进程完成日志配置并开始处理请求
- **THEN** logger `chromadb.telemetry.product.posthog` 的有效级别 SHALL 为 CRITICAL 或更高（或等价地不输出 ERROR）
- **AND** 正常向量查询日志中 SHALL NOT 出现该 logger 的 ERROR 行

### Requirement: 使用正确的遥测环境变量
系统 SHALL 使用 chromadb 认可的 `ANONYMIZED_TELEMETRY` 表达禁用匿名遥测的意图，不得依赖无效的 `CHROMA_TELEMETRY` 作为唯一控制手段。

#### Scenario: 进程与 compose 对齐
- **WHEN** 服务通过 Docker Compose 或本地进程启动
- **THEN** 环境中 SHALL 设置 `ANONYMIZED_TELEMETRY=False`（或等价假值）
- **AND** 文档/compose 中若仍保留 `CHROMA_TELEMETRY`，不得将其当作有效 chromadb 开关依赖

### Requirement: 可选约束 posthog 主版本
依赖声明 SHALL 将 `posthog` 约束在与 chromadb 0.4.x 兼容的范围（`<6`），除非构建环境证明无法满足该约束。

#### Scenario: 安装后 posthog 主版本小于 6
- **WHEN** 按项目依赖安装运行时包
- **THEN** 已安装的 `posthog` 主版本 SHALL 小于 6
- **AND** chromadb telemetry 调用 SHALL NOT 因 `capture()` 参数个数错误而失败（即便 logger 已静音）
