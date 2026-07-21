## Why

Docker 镜像体积达 3GB，其中 site-packages 约 2GB。PyTorch 完整版（含 CUDA 库）占 ~800MB，但项目仅用 CPU 推理；onnxruntime 占 ~200MB 但从未被调用（使用自定义 BGE Embedding）。此外缺少 .dockerignore 导致 .git、scripts、openspec 等无关文件被打包进镜像。

## What Changes

- 安装 CPU-only PyTorch 替代默认完整版（省 ~400MB）
- 在同一 Dockerfile RUN 层中卸载 onnxruntime（省 ~200MB，需验证 ChromaDB import 兼容性）
- 添加 .dockerignore 排除 .git、scripts、frontend、openspec、docs 等无关文件（省 ~50MB）

## Capabilities

### New Capabilities
- `docker-image-optimization`: Docker 镜像体积优化，通过 CPU-only torch、移除未用依赖、添加 .dockerignore 减少镜像体积

### Modified Capabilities

## Impact

- Dockerfile: 修改 builder 阶段的依赖安装逻辑
- 新增 .dockerignore 文件
- 不影响运行时功能：BGE-small-zh-v1.5 模型保留，Embedding 质量不变
- 预期镜像体积从 ~3GB 降至 ~2.4GB
