## Context

`care-alert-prompt-flywheel` 已实现：无通识检索；system 来自本地 `prompt.json`；user 运行时注入月龄与近两日史。当前口径仍是「准确优先、史不够可 `items=[]`」，user 文案写「不够清楚就返回空 items」，bootstrap `output_format` 写「宁可少出、不出 / 可为 []」。产品要求改为：**有近两日记录时至少一条**，且**必须结合宝宝月龄**。

「有近两日记录」操作定义：`history_events` 经紧凑化后非「（无）」，且存在可用的事件名↔id 对照表（legend 非空），才能可靠产出带 `eventId` 的 item。

## Goals / Non-Goals

**Goals:**

- 有近两日史 + 非空 legend 时，analyze 结果 `len(items) >= 1`。
- Prompt（bootstrap + user）明确要求结合月龄；月龄已知时 reasons/`ageMonths` 与文案须与该月龄一致；月龄未知不得编造具体月龄通识。
- LLM 仍空时有确定性兜底，保证契约。
- 与对比样例共存：弱信号改为「可轻提」，不因样例在有史时压成空列表。

**Non-Goals:**

- 无历史 / 无 legend 时不强制出项。
- 不恢复知识库。
- 不改 HTTP 字段外形。
- 不做「每天固定 N 条」或按设备个性化最低条数。

## Decisions

### D1: 中档保证——有史+legend 必须 ≥1

| 条件 | 期望 |
|------|------|
| 近两日史有内容且 legend 非空 | `items` 长度 ≥ 1 |
| 史空或 legend 空 | 允许 `[]`（无法合法 eventId） |

**Alternatives:** 仅改 prompt 不兜底 — 模型仍常空；无条件强制每天一条 — 无史必编造。选中档 + 兜底。

### D2: 月龄为硬约束通道

- user 消息已有「宝宝月龄：N / 未知」；system/bootstrap 增加：**选择留意点与措辞必须对照月龄**（例如同「间隔偏长」在新生儿与较大月龄阈值期望不同）；禁止输出与已知月龄矛盾的期望表述。
- 兜底合成 item 时：`reasons[].ageMonths` 填入已知月龄（未知则省略）；summary 不假装有精确月龄常模。

### D3: Prompt 双处同步

1. `prompt_store.default_output_format()`：删「可为 [] / 宁可不出」在有史场景的适用；改为有史至少一条 + 月龄条款。
2. `build_care_alert_user_message`：改 77–88 一带指引，去掉「不够就空」。
3. 已存在的挂载卷 `prompt.json`：启动或首次 analyze 时若检测到旧口径关键句，可用「版本 bump + 合并新 output_format」或文档要求删文件重 bootstrap；实现选 **version 字段升级时覆盖 output_format 默认块、保留 contrastive_examples**（避免飞轮样例丢失）。

### D4: 代码兜底（确定性）

在 `generate_care_alerts`（或 analyze 后处理）：

```
LLM items 规范化后为空
AND history 紧凑非空
AND legend 可解析出 ≥1 个 (name, id)
  → 选一条「最值得提」的事件（启发式：近两日次数/间隔异常或唯一事件）
  → 合成软提醒 item（低 score、expectationUsed=false、followUpPrompt 模板）
  → 带上 baby_age_months
```

启发式保持简单，不引入通识库。

### D5: 与飞轮对比样例

重写/渲染样例的说明可加一句：有近两日记录时不得建议「全部不提」；弱信号对应「轻提」。不强制改 ledger 结构。

## Risks / Trade-offs

- [弱信号硬出 → ignore 增多] → 兜底与 prompt 要求轻语气、低 score；飞轮学「轻提」而非「禁提」。
- [覆盖 output_format 丢掉人工改过的 system] → 仅在 version 迁移路径覆盖；保留 `.bak`。
- [兜底选错事件] → 启发式保守 + 文案标明「结合近两日记录的温和提醒」。
- [月龄未知仍出项] → 允许，但禁止捏造月龄常模数字。

## Migration Plan

1. 改 bootstrap 与 user 文案；实现 version 迁移保留样例。
2. 上线兜底；观察空列表率与 ignore 率。
3. 回滚：恢复旧镜像；可将 `prompt.json` 的 version/`output_format` 还原。

## Open Questions

- 无：有史必须 ≥1 与月龄硬约束已由产品确认；兜底启发式细节实现时可微调。
