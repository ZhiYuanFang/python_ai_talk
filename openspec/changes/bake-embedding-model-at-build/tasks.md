## 1. Dockerfile 与运行时离线

- [x] 1.1 确认 builder 阶段预下载 BGE 到 `data/models`，且 runtime 在 `COPY . .` 之后从 builder 复制该目录
- [x] 1.2 确认 runtime 设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，以及 `SENTENCE_TRANSFORMERS_HOME=/app/data/models`（缺失则补齐）
- [x] 1.3 确认 `.gitignore` / `.dockerignore` 仍排除 `data/models/`

## 2. Compose 与加载代码

- [x] 2.1 确认基线 `docker-compose.yml` 无 `./data/models` bind-mount，并保留禁止挂载的注释说明
- [x] 2.2 确认 `vector_store` 与 `event_vector_store` 加载 Embedding 时使用 `local_files_only=True` 与 `data/models` 缓存目录
- [x] 2.3 检查兄弟仓 / 其他 compose 是否仍挂载 models；若有则同步去掉或记录需外部修改项

## 3. 文档

- [x] 3.1 更新 `docs/deploy-guide.md`：Docker 路径下模型由构建打入镜像，勿挂空 `data/models`
- [x] 3.2 更新 `docs/vector_db_guide.md` 中与模型获取/目录相关的表述，与构建时下载策略一致

## 4. 验证

- [ ] 4.1 重建镜像，确认构建阶段模型下载成功且镜像内存在模型缓存
- [ ] 4.2 无 models volume 启动容器，确认无对 huggingface.co 的失败重试，Embedding 初始化成功，`/v1/health` 通过
