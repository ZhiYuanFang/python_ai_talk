## 1. 压缩 system（B）

- [x] 1.1 重写 `default_output_format`：合并判定/规则重复；近两日→近期；去掉只今天昨天
- [x] 1.2 `PROMPT_DOC_VERSION` 升至 3；更新 `_HISTORY_INSTANCE_RE` 兼容近期记录
- [x] 1.3 对齐仓库 `data/care_alert/prompt.json`（或依赖迁移覆盖）

## 2. 瘦 user（A）

- [x] 2.1 `build_care_alert_user_message` 去掉政策长段与 age_hint；仅实例数据 + 可选一行指针
