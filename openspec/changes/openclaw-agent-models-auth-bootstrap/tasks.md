## 1. 种子与 entrypoint

- [x] 1.1 新增可提交的 DeepSeek `models.json` 种子（如 `deploy/openclaw/seed/models.json`）：含 `deepseek` + `deepseek-v4-flash`，`apiKey` 仅为 `DEEPSEEK_API_KEY` marker，无明文 key
- [x] 1.2 新增 `docker-entrypoint.sh`（中文注释）：启动 gateway 前为 `intent`/`clinic`/`care_alert` 复制种子；覆盖缺失或空 `providers:{}`；`models.mode` 保持 merge（确认 json5 未改成 replace）
- [x] 1.3 在 entrypoint 中：若 `DEEPSEEK_API_KEY` 非空，对三 agent 用 `OPENCLAW_AGENT_DIR` + `paste-api-key`（或以镜像 `openclaw models auth --help` 锁定的等价命令）经 stdin 灌入 deepseek auth；空 key 则 stderr 警告

## 2. 镜像与 compose

- [x] 2.1 更新 `Dockerfile`：`COPY` 种子与 entrypoint，设置 `ENTRYPOINT`，`CMD` 保留 gateway 参数；脚本可执行
- [x] 2.2 更新 `docker-compose.openclaw.yml`：与 entrypoint/CMD 对齐（避免覆盖掉 bootstrap）；注释说明改 bootstrap 需 rebuild

## 3. 文档与验收说明

- [x] 3.1 更新根 `README.md`（或 deploy 说明）：recreate 自愈、种子+auth bootstrap、禁止明文 key、手工 curl 验收要点
- [x] 3.2 对照 spec 自检清单写入 README 或 change 备注：启动后 models.json 非空、auth list 有 deepseek、chat 不再 Unknown / missing-provider-auth
