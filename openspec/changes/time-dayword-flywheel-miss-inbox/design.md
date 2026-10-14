## Context

TIME 链现状：规则钟点 →（非 read）相对配方飞轮 → TIME LLM → 合法配方回写；几乎每次 LLM 都写 `rule_gap`。read 固定 `allow_flywheel=False`。日词整日窗 `parse_day_word_window` / `enum_to_unix` 已存在，但主要在 `speak_history` daily 缺窗时补，段 TIME 对「昨天+几次」仍先打 LLM → 假缺口、飞轮空。

探索拍板：日词规则前移；飞轮对各 CRUD 轨同等；热路径免 LLM；答不出独立 inbox，不与 time/rule_gap 混用。

## Goals / Non-Goals

**Goals:**

- 仅日词无钟点 → 本地填窗，跳过 TIME LLM 与 time 类 rule_gap。
- 相对时间：全轨读/写 `feeding_time_cues`；命中则免 LLM。
- 终局无法识别前落 miss inbox，Hub 查删。
- 热路径目标：数据增长后 TIME 维趋近零 LLM（非 100% 保证）。

**Non-Goals:**

- 不把日词强行灌进飞轮当唯一手段。
- 不改 EVENT 软候选、不合并 rule_gap 语义。
- 不承诺同义改写 100% 向量命中；不写测试文件。
- Hub 前端若在兄弟仓，本仓交付 Admin API + 字段约定即可。

## Decisions

### D1：TIME 分层（终态）

```
需要时间？
  ├─ 点查 ignore_time_range → 跳过窗解析
  ├─ 仅日词无钟点 → parse_day_word_window → unix；不 LLM；不写 time rule_gap
  ├─ 钟点/相对口语 → 本地槽位 → 全轨飞轮物化 → 仍 miss 才 LLM → 合法配方全轨回写
  └─ 失败 → 当次失败/追问；维级可记 rule_gap（非 miss inbox）
```

### D2：全轨飞轮

去掉 `allow_flywheel=False` 对 read 的一刀切。凡调用 `resolve_time` 且非「仅日词已解决」路径，默认 `allow_flywheel=True`（含 read/update/delete/create）。载荷仍仅为可校验相对配方；仅 Unix 不写库。

### D3：日词不强制写飞轮

整日窗由规则覆盖即可；避免「昨天拉了几次屎」整句污染相对钟点库。可选后续：短配方 `kind=interval day=yesterday` 灌种——首版不做。

### D4：miss inbox 独立

- 触发：对外终局失败回复前（至少含「无法识别对应的事件」、`OTHER_UNSUPPORTED`、软候选拒绝后仍无解、predict 估不准等可列清单；确认中/可续聊不记）。
- 字段建议：`utterance`、`reply`、`device_no`、`conversation_id`、`fail_kind`、`ts`；用户扩展字段若请求带则透传。
- 存储：类 `rule_gap` 的 JSONL（chroma 卷下独立目录）或等价；Admin：`GET/DELETE`（或 patch dismissed）。
- MUST NOT 写入 `rule_gaps` 或 `feeding_time_cues`。

### D5：与 speak_history 补窗关系

段上已填日词窗后，`speak_history` 补窗仍可作双保险；优先以段上 unix 为准，避免重复 LLM。

## Risks / Trade-offs

- [read 飞轮整句撞 create 句] → 文档不同则分叉；阈值沿用既有  
- [日词+钟点误判为仅日词] → 有钟点线索必须走槽位/飞轮/LLM，不得只吃整日窗  
- [miss 箱噪声] → 仅终局失败；去重短窗可按 utterance+device  
- [同义未命中仍 LLM] → 接受冷路径；灌种与阈值运维  

## Migration Plan

1. 段 TIME：日词优先 + 全轨飞轮。  
2. 新增 miss store + admin 路由；终局出口挂钩。  
3. 手工：昨天几次 → 无 TIME LLM/无 time 缺口；昨晚八点 create/read 可飞轮互通。  
4. 回滚：恢复 read `allow_flywheel=False`；去掉日词前移与 miss 挂钩。

## Open Questions

（无：分层、全轨飞轮、独立 inbox 已拍板。）
