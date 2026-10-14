## Context

意图终局失败经 `infer_miss_fail_kind` 识别后，由 `_finish_intent_response` → `maybe_record_agent_miss` 写入 JSONL 收件箱，用户直接看到硬模板。插话 barge 亦复用同一文案谓词。设备侧已有 `predict_algo:{device}` 快照（TTL 10min）与宝宝画像 HTTP；二者今日不参与 miss 话术。

## Goals / Non-Goals

**Goals:**

- 凡已判定为 miss 的终局回复：先落库（统计 / 主定位不变），再可选 LLM 润色对外 `content`。
- 润色提示：原话 + 规范失败语义；有则注入预测快照与宝宝基础信息；无缓存不重算、不编造快照。
- barge / 统计继续认规范 `fail_kind`（判定在润色前完成）。

**Non-Goals:**

- 把「数据量太少，无法预测」并入 miss。
- 为润色去拉 7 日史或跑预测算法。
- 改变 Hub miss-inbox 列表 API 契约（可仍只展示硬 `reply`）。
- 把 miss 改成「成功答出」轨或降低 fail_kind 覆盖面。

## Decisions

### D1：统一出口润色，先记后软

```
硬 content 产出
  → infer_miss_fail_kind(硬 content) → kind?
       无 → 原样返回
       有 → record(utterance, reply=硬文案, fail_kind)
            → LLM 润色 → 替换对外 content
            → barge 侧：用 kind / 润色前标记，勿仅靠软文案关键词
```

挂在 `_finish_intent_response`（async 化或并行 helper），避免每个硬返回点散落调用。

**Alternatives：** 各节点各自润色——否决（易漏记、顺序乱）。先软后记——否决（漏统计）。

### D2：注入块

| 块 | 规则 |
|----|------|
| 规范失败 | 硬模板 + `fail_kind` 中文说明 |
| 预测快照 | `predict_algo_cache.get(device)`；无/过期 → 不注入该块 |
| 宝宝信息 | `get_baby_profile`；失败/空 → 跳过 |
| 原话 | 必给 |

提示词常量落 `feeding/.../prompts/system.py`；禁止编造未注入的数字；SSE 路径 `stream(thinking_enabled=True)`。

### D3：inbox 存硬、用户见软

`agent_miss_store.record` 的 `reply` = 硬模板。软文案仅响应体。运营对照缺口不依赖 LLM 临场措辞。

### D4：barge 兼容

`should_concatenate_rerun` 在润色后若只看 soft content 会失效。实现须：润色前用硬文案判 miss，或在 response 上保留可检的 miss 标记 / 对 barge 传入硬文案副本。推荐：barge 判定读「规范 content」或 `fail_kind` 辅助字段（若不加字段，则 barge 在 finish 润色**之前**对占坑轮用硬文案判定——即 miss 拼接决策发生在图结束硬文案阶段，finish 只改最终对外；若 finish 在返回前润色，barge 的 `maybe_prepare_concat_rerun` 须先对硬副本判或先 record 再软）。落地顺序：**owner 循环内先用硬 content 调 `maybe_prepare_concat_rerun` / 或 finish 返回前：拷贝硬 → record → soft → 返回 soft，且 `maybe_prepare_concat_rerun` 使用硬拷贝。**

### D5：范围

本版对所有 `infer_miss_fail_kind` 非空的终局 miss 润色（含 event_unresolved / other_unsupported / predict_uncertain / segment_unclear）。预测快照对非预测类 miss 仅作可选背景，无则省略。

## Risks / Trade-offs

- [LLM 延迟叠加在 miss 路径] → 失败则回退硬模板；可后续加短超时。
- [软文案被误当成成功答] → 提示词约束仍说明「未能可靠完成意图」；不改 target_type 成功语义。
- [barge 漏拼] → D4 强制硬信号判定。
- [快照数字误导用户以为已预测成功] → 提示词：快照仅参考，不得假装已给出权威下次时间除非语义允许安慰性转述且标明不确定。

## Migration Plan

1. 实现 finish 钩子 + 提示词 + barge 硬判定。
2. 手工：无法识别 / 估不准 仍进 inbox；用户句更口语；无缓存时仍能软回。
3. 回滚：关掉润色即回硬返回。

## Open Questions

（无；统计不变、先记后软、可选缓存、全 miss 种类润色已拍。）
