## Why

Docker 运行时钉死在 `python:3.11-slim`，与本机开发环境（Python 3.12）不一致；3.11 下 f-string 表达式内不允许反斜杠，导致 `clinic_answer` 等 prompt 模块在容器内 `SyntaxError`，uvicorn 无法启动。项目尚新、无存量兼容债，现在对齐到 3.12 成本最低。

## What Changes

- **BREAKING**（部署侧）：Docker 基础镜像从 `python:3.11-slim` 升级为 `python:3.12-slim`，`site-packages` 复制路径同步改为 `python3.12`
- `pyproject.toml` 的 Python 约束收紧为 `^3.12`（或 `>=3.12,<3.13`），black `target-version` 改为 `py312`
- 更新 `openspec/project.md` 与相关文档中的 Python 版本表述（3.11 → 3.12）
- 不升级 chromadb / 不改业务 API；f-string 中 `{"\n".join(...)}` 在 3.12 下合法，可保留原写法

## Capabilities

### New Capabilities

- `python-runtime`: 约定服务运行时 Python 版本、Docker 基础镜像与依赖安装约束（含 Chroma 原生扩展在 3.12 上源码编译的可构建性）

### Modified Capabilities

- （无）当前 `openspec/specs/` 下无已归档能力需改需求

## Impact

- **Dockerfile**：两阶段 `FROM`、site-packages 路径
- **依赖声明**：`pyproject.toml`（python / black）
- **文档**：`openspec/project.md`、`docs/vector_db_guide.md` 等提及 3.11 处
- **构建风险**：`chromadb==0.4.*` 依赖的 `chroma-hnswlib==0.7.3` 无 cp312 预编译 wheel，需在已有 `build-essential` 的 builder 中源码编译；onnxruntime 同层卸载后仍须能 `import chromadb`
- **不受影响**：HTTP API 契约、业务逻辑、chromadb 主版本、兄弟仓 go_ai_talk 调用方式
