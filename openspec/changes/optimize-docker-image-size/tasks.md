## 1. Dockerfile 优化

- [x] 1.1 修改 Dockerfile builder 阶段：在 poetry install 前先安装 CPU-only torch
- [x] 1.2 修改 Dockerfile builder 阶段：在同一个 RUN 层中卸载 onnxruntime 并验证 chromadb import
- [x] 1.3 修改 Dockerfile builder 阶段：清理 pip 缓存

## 2. .dockerignore

- [x] 2.1 创建 .dockerignore 文件，排除 .git、frontend、openspec、docs、__pycache__、*.pyc、.env、docker-compose*.yml

## 3. 验证

- [x] 3.1 确认 Dockerfile 语法正确（shell 逻辑 `||` 回退验证通过）
- [x] 3.2 确认 build_vector_db.py 未被 .dockerignore 排除（`!scripts/build_vector_db.py` 显式保留）
