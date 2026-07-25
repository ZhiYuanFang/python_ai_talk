## 1. 依赖与工程声明

- [x] 1.1 将 `pyproject.toml` 的 `python` 约束改为 `>=3.12,<3.13`（或 Poetry 等价写法）
- [x] 1.2 将 `[tool.black]` 的 `target-version` 改为 `["py312"]`

## 2. Docker 运行时

- [x] 2.1 将 `Dockerfile` builder 与 runtime 的 `FROM` 改为 `python:3.12-slim`
- [x] 2.2 将 `COPY .../python3.11/site-packages` 路径改为 `python3.12`
- [x] 2.3 确认 pip 安装列表、CPU torch index、onnxruntime 同层卸载与 `import chromadb` 验证逻辑保持不变

## 3. 文档同步

- [x] 3.1 更新 `openspec/project.md` 技术栈：语言为 Python 3.12
- [x] 3.2 更新 `docs/vector_db_guide.md`（及其他仍写死 3.11 的开发说明）为 3.12

## 4. 构建与冒烟验证

- [ ] 4.1 本地/CI 重建 Docker 镜像，确认 `chroma-hnswlib` 源码编译与依赖安装成功
- [ ] 4.2 确认 onnxruntime 卸载策略在 3.12 下仍按预期（卸载成功或按脚本回退重装）
- [ ] 4.3 启动容器，确认 `python --version` 为 3.12.x，uvicorn 无 f-string `SyntaxError`，`/v1/health` 通过
- [ ] 4.4 冒烟验证 Embedding/向量检索可正常工作（必要时重建测试环境 chroma volume）
