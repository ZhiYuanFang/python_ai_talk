## Context

当前生产/测试镜像基于 `python:3.11-slim`，而本机开发已是 Python 3.12。容器内导入 clinic/tip prompt 模块时，f-string 表达式中的 `"\n".join(...)` 触发 `SyntaxError`，uvicorn 启动失败。

依赖栈（FastAPI、LangGraph、chromadb 0.4.*、sentence-transformers、CPU torch）在 3.12 上整体可用。builder 阶段已安装 `build-essential`，具备编译无 wheel 原生扩展的能力。项目为新建服务，无多版本并存或长期 3.11 锁定需求。

## Goals / Non-Goals

**Goals:**

- 运行时与声明统一为 Python 3.12
- Docker 构建在 3.12 下仍保持现有瘦镜像策略（CPU torch、同层卸载 onnxruntime）
- 服务可正常 import 并启动（消除 3.11 f-string 语法限制带来的崩溃）

**Non-Goals:**

- 不升级到 Python 3.13
- 不升级 chromadb 主版本（保持 `^0.4.24`）
- 不重构 prompt 拼装逻辑（f-string 写法可原样保留）
- 不处理 LangGraph `allowed_objects` deprecation warning（与本次无关）
- 不改变 HTTP API、业务图逻辑或向量集合 schema

## Decisions

### D1: 目标版本锁定为 3.12（非 3.13）

**决定**：基础镜像与约束使用 3.12；`pyproject.toml` 使用 `python = "^3.12"`（Poetry 语义为 `>=3.12,<4.0` 时过宽，改为 `>=3.12,<3.13` 更稳妥——若 Poetry 不支持该写法则用 `~3.12`）。

**备选**：升到 3.13 → 否决，ML 原生库（torch / chroma 周边）成熟度不如 3.12。

**备选**：继续 3.11，只改 f-string → 否决，无法消除本机/镜像版本漂移，且新项目无必要继续钉旧小版本。

### D2: 保留 chromadb 0.4.*，接受 hnswlib 源码编译

**决定**：不 bump chromadb。`chroma-hnswlib==0.7.3` 无 cp312 wheel 时，在 builder 中源码编译。

**备选**：升 chromadb 0.5+ 以获得预编译 wheel → 否决，此前已因 API（`include`/ids）决定留在 0.4.24，Python 升级与 Chroma 升级拆开。

### D3: Dockerfile 仅改版本路径，不改安装流水线

**决定**：两阶段 `FROM python:3.12-slim`；`COPY .../python3.12/site-packages`；pip 安装列表与 onnxruntime 卸载验证逻辑不变。

### D4: 文档与工程约束同步

**决定**：更新 `openspec/project.md` 技术栈为 Python 3.12；`docs/vector_db_guide.md` 等写死 3.11 的说明改为 3.12；black `target-version = ["py312"]`。

### D5: 本机 Windows 开发以 Docker 为准

**决定**：文档/设计中明确：依赖安装与运行以 Docker 为准。本机若直接 pip，可能因缺少 C++ Build Tools 无法编译 `chroma-hnswlib`，不作为阻塞项，也不在本 change 内搭建 Windows 本地编译环境。

## Risks / Trade-offs

- [chroma-hnswlib 0.7.3 在 3.12 无 wheel，编译失败] → builder 保留 gcc/g++；构建失败即回滚镜像标签，不推送
- [onnxruntime 卸载后 chromadb import 在 3.12 行为变化] → 同层验证脚本保留；失败则按现有回退逻辑重装 onnxruntime
- [Chroma persist 目录在换 Python 后异常] → 同版本 chromadb，格式不应变；冒烟时做一次向量读写；异常则清空 volume 重建（测试环境可接受）
- [本机 Windows 无法源码编译 hnswlib] → 以 Docker 为权威运行时；本地开发走 compose
- [镜像体积/构建时间略增（源码编译）] → 可接受；不改变瘦镜像策略目标

## Migration Plan

1. 合并本 change 后重建镜像（test → 冒烟 → prod）
2. 冒烟：health、关键 import、向量检索/Embedding 加载
3. 回滚：重新打回 `python:3.11-slim` 镜像并回退 pyproject 约束（业务代码无需回退，因 3.11 语法子集仍兼容已写代码——但若保留 `\n` in f-string 表达式，回滚到 3.11 会再次 SyntaxError；回滚时须同步改回那几处 join，或保持镜像在 3.12）

## Open Questions

- （无）目标版本、chromadb 不动、Docker 改动范围已在 explore 中确认
