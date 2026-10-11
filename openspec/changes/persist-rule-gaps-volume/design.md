## Context

`RuleGapStore` 将缺口 append 到 JSONL，路径为 `os.path.join(chroma_persist_dir, "..", "rule_gaps", "gaps.jsonl")`。基线 compose 仅挂载 `./data/chroma_db → /app/data/chroma_db`，因此运行时实际文件在 `/app/data/rule_gaps/`（容器可写层），重建容器即丢。产品要求 open 缺口稳留到 Hub 手动 `dismissed`；生命周期与清空开关（如 `CLEAR_FEEDING_INTENTS_ON_STARTUP`）无关。

## Goals / Non-Goals

**Goals:**

- 缺口文件落在已挂载的 Chroma 持久目录内，换镜像/重建容器后 open 记录仍可读。
- 升级时尽量迁走旧路径存量（若新路径尚无文件）。
- 文档标明同卷语义；不改 admin API 契约。

**Non-Goals:**

- 不新增独立 Docker volume（方案 B 已否决）。
- 不上 MySQL/Redis；不自动把缺口转成规则或飞轮。
- 不实现物理删除 API、TTL、或启动清箱。
- 不修复「已丢在旧容器层」的历史数据。

## Decisions

### D1：路径 = `{CHROMA_PERSIST_DIR}/rule_gaps/gaps.jsonl`

相对 `settings.chroma_persist_dir` 子目录，不再 `..` 跳出卷。

| 方案 | 取舍 |
|------|------|
| A（本决策） | 零 compose；与意图库同卷同命运 |
| B 独立挂载 `data/rule_gaps` | 职责清晰，但多一处运维与环境分叉 |

### D2：启动一次性旧路径迁移

若 `normpath(chroma_persist_dir/../rule_gaps/gaps.jsonl)` 存在且非空，且新路径不存在或为空文件：复制/改写到新路径后可保留旧文件不动或改名 `.migrated`（实现选简单：`shutil.move` 或读旧写新再删旧）。失败只打日志，不阻断服务启动。

### D3：生命周期不变

- 写入：`status=open` append
- 处理：PATCH → `dismissed`；默认列表仍只看 open
- MUST NOT：因进程重启、容器重建、`CLEAR_FEEDING_INTENTS_ON_STARTUP` 删除或截断缺口文件

### D4：文档

`docs/deploy-guide.md`（或现有向量/数据目录小节）补一句：规则缺口 JSONL 位于 chroma 持久目录下 `rule_gaps/`，与意图向量同卷。

## Risks / Trade-offs

- [整卷删除 chroma_db] → 缺口一并没；可接受（与意图库同运维边界）
- [Chroma 内部文件与 JSONL 同目录] → 用子目录 `rule_gaps/` 隔离；勿写入 Chroma SQLite 同名冲突
- [双栈同机不同 project 各挂各的 `./data/chroma_db`] → 行为与现网一致，无额外串扰
- [旧路径有数据且新路径已有写入] → 不覆盖合并；只日志提示（避免双写撕裂）

## Migration Plan

1. 发版含新路径 + 启动迁移逻辑。
2. 首次启动：旧文件迁入 `{CHROMA_PERSIST_DIR}/rule_gaps/`。
3. 验证：写一条缺口 → recreate 容器（保留 volume）→ GET open 仍见该条。
4. 回滚：恢复旧代码后路径回到 `../rule_gaps`；若已 move，需运维把文件挪回旧位置（罕见）。

## Open Questions

（无；方案 A 与「稳留到手动处理」已在 explore 确认。）
