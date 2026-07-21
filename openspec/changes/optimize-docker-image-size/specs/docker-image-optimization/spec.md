## ADDED Requirements

### Requirement: Docker 镜像使用 CPU-only PyTorch
Docker 镜像构建时 SHALL 使用 CPU-only PyTorch（从 https://download.pytorch.org/whl/cpu 安装），不得包含 CUDA 库。

#### Scenario: CPU-only torch 安装
- **WHEN** Docker 镜像构建时
- **THEN** torch 从 CPU 专用 index 安装，不包含 CUDA 运行时库

### Requirement: 移除未使用的 onnxruntime
Docker 镜像 SHALL 在同一 RUN 层中卸载 onnxruntime，前提是 `import chromadb` 能正常执行。如果 ChromaDB 顶层 import 强制加载 onnxruntime 导致验证失败，则保留 onnxruntime。

#### Scenario: onnxruntime 可安全移除
- **WHEN** 卸载 onnxruntime 后执行 `python -c "import chromadb"` 成功
- **THEN** onnxruntime 不进入最终镜像层

#### Scenario: onnxruntime 不可移除
- **WHEN** 卸载 onnxruntime 后执行 `python -c "import chromadb"` 失败
- **THEN** 保留 onnxruntime，仅实施 CPU-only torch 优化

### Requirement: .dockerignore 排除无关文件
Docker 构建上下文 SHALL 通过 .dockerignore 排除 .git、frontend、openspec、docs、__pycache__ 等无关文件，但保留 app、scripts/build_vector_db.py、data/knowledge 和 pyproject.toml。

#### Scenario: COPY . . 不包含无关文件
- **WHEN** Docker 构建执行 COPY . .
- **THEN** .git、frontend、openspec、docs 目录不被打包进镜像
