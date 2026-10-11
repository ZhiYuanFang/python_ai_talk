## Why

规则缺口 JSONL 落在 `CHROMA_PERSIST_DIR/../rule_gaps/`，而 Docker 只挂载 `chroma_db` 卷，换镜像/重建容器会丢待处理缺口。运维需要缺口稳留到 Hub 手动标已处理为止。

## What Changes

- 将规则缺口文件路径改为 **`{CHROMA_PERSIST_DIR}/rule_gaps/gaps.jsonl`**，与现有 Chroma 卷同命运。
- 明确：服务重启、容器重建（在 chroma 卷保留时）MUST NOT 清空 open 缺口；仅人工 `dismissed`（或等价）视为处理完。
- 启动时若发现旧路径 `CHROMA_PERSIST_DIR/../rule_gaps/gaps.jsonl` 有内容且新路径为空，SHALL 一次性迁入新路径（避免升级丢存量）。
- 部署文档注明缺口与 chroma 同卷；**不**新增独立 volume（方案 A）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-rule-gap-inbox`：缺口持久化路径与卷语义；重启/重建不得丢 open；旧路径一次性迁移

## Impact

- 代码：`app/feeding/services/rule_gap_store.py`（路径与可选迁移）
- 部署：`docs/deploy-guide.md`（或等价）说明同卷路径；compose **无需**新挂载
- API / Hub：行为不变（仍 `/v1/admin/rule-gaps`）；换卷后旧容器层内未迁数据可能已丢，属既有缺陷，本变更只保未来与可迁存量
