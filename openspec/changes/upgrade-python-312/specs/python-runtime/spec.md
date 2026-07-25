## ADDED Requirements

### Requirement: 服务运行于 Python 3.12
Python AI Talk 服务的运行时与依赖声明 SHALL 使用 Python 3.12（不得低于 3.12，也不得将正式运行时目标设为 3.13+）。

#### Scenario: pyproject 约束为 3.12
- **WHEN** 查看 `pyproject.toml` 中的 Python 版本约束
- **THEN** 约束要求 Python 3.12.x（例如 `>=3.12,<3.13` 或等价写法），且 black `target-version` 包含 `py312`

#### Scenario: 项目约束文档同步
- **WHEN** 查看 `openspec/project.md` 技术栈说明
- **THEN** 语言版本表述为 Python 3.12（或明确锁定在 3.12.x）

### Requirement: Docker 基础镜像为 Python 3.12
生产与测试用的应用镜像 SHALL 基于官方 `python:3.12-slim`（或同主版本的 slim 变体），两阶段构建的 builder 与 runtime 阶段均须使用 3.12。

#### Scenario: Dockerfile 使用 3.12-slim
- **WHEN** 查看根目录 `Dockerfile`
- **THEN** builder 与最终阶段的 `FROM` 均为 `python:3.12-slim`（或等价的 3.12 slim 镜像）
- **AND** 从 builder 复制 `site-packages` 的路径指向 `python3.12`

#### Scenario: 容器内解释器版本
- **WHEN** 在构建完成的应用容器中执行 `python --version`
- **THEN** 输出版本为 Python 3.12.x

### Requirement: 3.12 下保留现有 Chroma 与瘦镜像构建策略
升级 Python 后，Docker 构建 SHALL 继续使用当前依赖主版本策略（含 `chromadb==0.4.*`），并保留 CPU-only torch 与同层卸载 onnxruntime（在 `import chromadb` 成功前提下）的构建流程。

#### Scenario: chromadb 0.4 可安装且可 import
- **WHEN** 在 `python:3.12-slim` builder 中按现有流水线安装依赖（允许源码编译 `chroma-hnswlib`）
- **THEN** 安装成功
- **AND** 在按策略卸载 onnxruntime 后（或回退保留后）执行 `python -c "import chromadb"` 成功

#### Scenario: 应用可启动
- **WHEN** 使用升级后的镜像启动 uvicorn（`app.main:app`）
- **THEN** 进程正常加载应用，不因 f-string 反斜杠语法限制产生 `SyntaxError`
- **AND** `/v1/health` 健康检查可通过
