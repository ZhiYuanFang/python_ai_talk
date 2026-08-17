## Context

飞轮约定：`system = output_format + contrastive_examples`；`user = 月龄/史/legend`。`min-one-with-age` 后又在 user 复述政策，与 `prompt.json` 双写。日历日变更后 user 已称「近期」，system 仍称「近两日」。

## Goals / Non-Goals

**Goals:**

- User 去政策复述（方案 A）
- System 合并重复条目并改「近期」（方案 B）
- 版本迁移覆盖 output_format；正则跟上

**Non-Goals:**

- 不改 min-one 业务规则（有史+legend ≥1 条）
- 不改 history_compact 聚合格式
- 不改飞轮账本结构
- 不编写测试

## Decisions

1. **职责**：政策唯一在 `default_output_format`；user 只拼实例字段。
2. **压缩原则**：态度 + 精简判定（有史≥1 / 空列表条件 / 月龄 / 禁通识 / eventId / 对比样例）+ JSON 骨架 + 输出细则（字段必填、毫秒、type 枚举、禁诊断）。判定与「规则」交叉的「至少 1 条」「禁诊断」只保留一处。
3. **文案**：一律「近期记录」；不再写「只参考今天与昨天」。
4. **`PROMPT_DOC_VERSION`**：2 → 3；`_migrate_if_needed` 继续覆盖 output_format、保留 contrastive_examples。
5. **正则**：`_HISTORY_INSTANCE_RE` 同时匹配「近两日记录」「近期记录」类实例行。
6. **user 可选尾句**：`请按系统侧判定依据与 JSON 输出格式作答。`（一行，不复述条款）。

**压缩后 system 结构草图：**

```
人设+态度
【判定】近期史信号；月龄必参与；禁通识；有史+对照表≥1（弱信号可轻提）；
  仅空史/无 id 才 []；eventId 来自对照表；对比样例非本宝宝、有史勿全不提
【输出】仅一个 JSON + schema（字段说明可略压）
【细则】排序/必填/口语追问/毫秒省略/type 优先/禁诊断
```

## Risks / Trade-offs

- [挂载卷旧 prompt 未升级] → version 迁移覆盖 output_format。
- [压缩过狠丢约束] → 保留 JSON 字段名与 min-one 两条硬规则；人工验收一次 analyze。

## Migration Plan

- 升版后首次 load 写回新 output_format；`.bak` 仍由现有写盘路径处理。
- 回滚：降 version / 恢复旧 output_format 文本。

## Open Questions

- （无）
