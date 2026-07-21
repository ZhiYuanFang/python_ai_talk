## Context

当前 Docker 镜像约 3GB，其中 site-packages 占 ~2GB。主要体积来源：
- PyTorch 完整版 ~800MB（含 CUDA 库 ~400MB，项目仅用 CPU 推理）
- onnxruntime ~200MB（ChromaDB 默认 EF 依赖，但项目使用自定义 BGE Embedding，从未调用）
- 无 .dockerignore，COPY . . 打包了 .git、scripts、openspec 等无关文件

## Goals / Non-Goals

**Goals:**
- 安装 CPU-only PyTorch，移除 CUDA 库
- 在同一 RUN 层卸载 onnxruntime，确保不进入 Docker 层
- 添加 .dockerignore 排除无关文件
- 预期减少 ~600MB 镜像体积

**Non-Goals:**
- 不更换 Embedding 模型（保留 BGE-small-zh-v1.5）
- 不更换向量数据库
- 不优化 Python 依赖列表（如 langchain 等）

## Decisions

### 1. CPU-only PyTorch
在 `poetry install` 前先通过 PyTorch CPU index 安装 torch，poetry 检测到已满足依赖会跳过安装完整版。

### 2. onnxruntime 同层卸载
在 builder 阶段的同一个 RUN 指令中，poetry install 后立即 `pip uninstall -y onnxruntime`。Docker 层是只追加的，同层内的安装和卸载会抵消，onnxruntime 不会进入任何层。

### 3. onnxruntime 兼容性验证
在卸载后于同一 RUN 层中执行 `python -c "import chromadb"` 验证。如果 ChromaDB 顶层 import 强制加载 onnxruntime，则构建会失败。此时回退为不卸载 onnxruntime（只保留 CPU torch 优化）。

### 4. .dockerignore
排除：.git、scripts、frontend、openspec、docs、__pycache__、*.pyc、.env、docker-compose*.yml

## Risks / Trade-offs

- [ChromaDB import 时强制加载 onnxruntime] → 验证脚本在同层执行，失败则构建中断，回退方案明确
- [CPU-only torch 性能差异] → 无风险，BGE-small-zh-v1.5 本身就是 CPU 推理模型
- [.dockerignore 排除 scripts 导致构建脚本不可用] → build_vector_db.py 在容器内由 startup_event 调用，需要保留 scripts/build_vector_db.py
