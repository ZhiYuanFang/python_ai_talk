## 1. 路径与迁移

- [x] 1.1 `rule_gap_store`：权威路径改为 `{chroma_persist_dir}/rule_gaps/gaps.jsonl`；中文注释说明同卷语义
- [x] 1.2 初始化时检测旧路径 `../rule_gaps/gaps.jsonl`：新路径空则一次性迁入；失败仅日志；新路径已有内容则不覆盖

## 2. 文档

- [x] 2.1 `docs/deploy-guide.md`（或等价数据目录说明）注明规则缺口与 chroma 同卷：`rule_gaps/gaps.jsonl`；无需单独挂载

## 3. 验收

- [ ] 3.1 手工：写入 open 缺口 → 重建容器且保留 chroma 卷 → GET `/v1/admin/rule-gaps` 仍见该条
- [x] 3.2 手工：`CLEAR_FEEDING_INTENTS_ON_STARTUP=true` 启动后缺口文件未被清空
