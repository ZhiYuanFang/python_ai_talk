## Context

`POST /v1/care-alert/analyze` 当前图路径为 `fetch_history → search_vectors → fetch_baby_profile → resolve_baby_age → generate_care_alerts`，system/user prompt 硬编码在 `care_alert_analyze.py`，并注入「相关知识摘录」。`POST /v1/care-alert/feedback` 通过 Redis `suggestionId → knowledge_ids` 对 `mother_baby_knowledge` 加减质量分（见 change `care-alert-knowledge-flywheel`）。

产品方向改为：care_alert **不依赖通识库**；用全局、可落盘的 prompt 飞轮吸收 ignore/follow_up；月龄与历史始终动态注入；冲突反馈用对比样例表达。部署上与现有 `./data/chroma_db` 一样，用 Docker bind/volume 保证重启不丢。

约束：代码中文注释；不自动生成测试；care_alert 模块自洽，不与 clinic 互引；HTTP 契约对外字段尽量不变（仍 `ignore|follow_up` + `ok`）。

## Goals / Non-Goals

**Goals:**

- 去掉 care_alert 路径上的向量通识检索与知识摘录 prompt 块。
- 全局一份 prompt：从挂载目录加载；缺失则 bootstrap 默认模板并写出。
- 默认模板 = 输出格式 + 月龄占位 + 历史占位；飞轮后增加「用户反馈对比样例」块。
- 落盘内容禁止写死当次月龄/历史；渲染时注入。
- feedback 更新账本 → 按阈值重写对比样例 → 原子写回本地文件。
- 对比样例处理同类相反反馈；样例块有硬长度上限。
- compose 增加 care_alert 数据卷；settings / env 可配置目录。

**Non-Goals:**

- 不做 per-device / 按月龄桶多文件 prompt。
- 不改 clinic/tip 通识质量飞轮与 `mother_baby_knowledge` 管理 API。
- 不强制 Go/Flutter 改 feedback 枚举或 analyze 响应 DTO 外形。
- 不引入新外部中间件（继续可用现有 Redis 做 suggestion 快照 TTL）。
- 不在本变更做多活共享盘的复杂共识（写路径加文件锁即可；水平扩展共享同一卷）。

## Decisions

### D1: 全局单文件 prompt + 旁路 ledger

```
/app/data/care_alert/          # CARE_ALERT_PROMPT_DIR
  prompt.json                  # 给模型的投影（有上限）
  ledger.jsonl                 # 反馈半结构化账本（可裁剪）
```

`prompt.json` 字段至少含：`version`、`output_format`、`contrastive_examples`（可空）、以及占位符清单或固定占位符名。运行时：`system = output_format + contrastive_examples`；`user = render(月龄, 历史, legend)`。

**Alternatives:** 纯 Markdown 单文件 — 解析弱；全塞 Redis — 与「挂载卷重启不丢」产品表述不一致。选本地 JSON + volume。

### D2: 动态槽，永不落盘实例值

固定占位符（实现可用 `{{baby_age_months}}` / `{{history_block}}` / `{{event_id_legend}}`，或等价「仅 user 侧代码拼接、不进落盘文件」策略）：

- **推荐**：落盘只存静态块（output_format、contrastive_examples、可选 guidance）；月龄/历史/legend **始终由代码拼进 user message**，从根上避免飞轮把动态值写进文件。
- 若飞轮 LLM 重写整份 prompt：落盘前 MUST 校验不得出现具体「宝宝月龄：N 个月」实例行或近两日流水正文；占位或「由运行时注入」声明必须保留。

**Alternatives:** 把月龄写进 system 模板用 replace — 易被飞轮污染。选「静态落盘 + 代码拼 user」。

### D3: 去掉 search_vectors；kg_context 不进判定

图改为 `fetch_history → fetch_baby_profile → resolve_baby_age → generate_care_alerts`。请求中的 `kg_context` 不注入 prompt（可打日志观测）。准确优先改为：仅凭史信号；不足则 `items=[]`。

### D4: suggestion 快照替代 knowledge_ids

analyze 成功后：`suggestionId → {device_no, day, eventName, reason_types, score_band, summary_line短}`（Redis TTL，默认仍约 7 天）。feedback 用快照归因；无快照则只 ACK，不改 prompt。

### D5: 冲突策略 = 对比样例（结构化槽 → 渲染）

按 `(reason.type 或 eventName, 信号档:强/弱)` 聚合 follow_up / ignore 计数。渲染块分三类：✓ 宜提、✗ 不宜提、⚡ 同类相反（保留张力，不净票抹平）。证据不足（两侧均 < k）的槽不进 prompt。

重写触发：累计 N 条新反馈或定时（实现默认：每 N=20 条或进程内距上次重写超过配置间隔）。以**规则聚合 + 模板渲染**为主；可选 LLM 润色但必须过长度与「无动态实例值」校验。

### D6: 长度与账本裁剪

- `contrastive_examples` 硬顶（默认 ≤ 1200 汉字/字符，可配置）。
- 每槽最多 1 条 ✓ + 1 条 ✗；冲突进 ⚡。
- ledger 滚动保留最近 M 条或 T 天；超限丢最旧。
- 写 `prompt.json`：临时文件 + replace，并文件锁；可选 `.bak`。

### D7: Volume 与配置

- 默认路径：`/app/data/care_alert`（本地开发可相对 `data/care_alert`）。
- 基线 `docker-compose.yml` 增加：`./data/care_alert:/app/data/care_alert`。
- Env：`CARE_ALERT_PROMPT_DIR`（及可选 `CARE_ALERT_EXAMPLES_MAX_CHARS`、`CARE_ALERT_FLYWHEEL_REWRITE_EVERY`）；三层命名一致、无 `PYTHON_AI_TALK_` 前缀。

### D8: 与旧通识飞轮关系

care_alert feedback **不再**调用 `vector_store.update_quality_score`。clinic 等其它入口的 knowledge-flywheel 基线行为不变。未收版的 `care-alert-knowledge-flywheel` 方向由本变更在实现上覆盖；收版时以本 change 规格为准合并 care_alert 飞轮语义。

## Risks / Trade-offs

- [全局坏摘要影响全站] → 占位/长度校验失败则拒绝覆盖，保留旧文件；保留 `.bak` 可手动回滚。
- [多实例同时写] → 文件锁；部署上共享同一 volume；当前以单 writer 为主。
- [反馈稀疏时样例空洞] → 初始 `contrastive_examples` 为空可接受；低证据不写入。
- [无知识校准可能漏提/误提] → 接受产品取舍；靠史信号 + 对比样例迭代。
- [旧 suggestion 仍指向 knowledge 映射] → 上线后旧 key 忽略；feedback 仍 ok。
- [漏挂 volume] → 规格/部署清单 MUST 写明；文档与 compose 同步。

## Migration Plan

1. 增加目录与 compose volume、settings；先部署只读 bootstrap（空样例），analyze 已不走知识库。
2. 切换 feedback 写 ledger / 重写样例；停止通识加减分。
3. 回滚：恢复旧镜像 + 可保留卷上文件不动；或删除/替换 `prompt.json` 为 bootstrap。

## Open Questions

- 对比样例重写是否启用 LLM 润色：默认 **否**（规则模板）；若后续要开，需另开小开关，不阻塞本变更。
- 多副本是否已用共享盘：若否，文档注明飞轮写仅单实例安全，或运维挂 NFS/同 bind。
