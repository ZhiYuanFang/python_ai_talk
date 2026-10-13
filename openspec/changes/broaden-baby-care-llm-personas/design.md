## Context

探索拍板 **C**：全 LLM 人设 + other 纠偏。范围限 feeding 意图链路文案，不改 clinic 等产品线、不改 `feeding` 包名。

## Goals / Non-Goals

**Goals:**

- 统一口径：人设用「宝宝照护记录」，并点名可含喂养、睡眠、换尿布、营养品、疫苗等。
- OP other 去掉「非喂养」；无关闲聊才 other。
- `system.py` 与 `dim_resolve` 内联人设一并改。

**Non-Goals:**

- 扩事件表 / 改 CRUD / 改播报模板 / 改模块路径。
- clinic / care-alert / growth 人设。
- 测试文件。

## Decisions

### D1：统一人设句式

`你是宝宝照护记录「{任务}」助手。`  
开篇或紧随一句：`领域含喂养、睡眠、换尿布、营养品、疫苗等可落库事件（以事件表为准）。`  
不必每个 prompt 重复长列表时，至少人设不再写「仅喂养」。

### D2：other 纠偏（仅 OP）

- 旧：`非喂养闲聊/无关 → other`
- 新：`与宝宝照护记录无关的闲聊/无关 → other（不要 conversation）`
- 语义例增：`换尿布了/吃了维生素/打疫苗了 → create`（不替代事件表对齐）

### D3：改动清单

| 文件 | 常量/位置 |
|------|-----------|
| `system.py` | SEGMENT_TYPE、HISTORY_SPEAK、EVENT、TIME、QTY、SHAPE、REMARK、SPLIT、PENDING |
| `system.py` | INTENT_CLASSIFICATION：可选加一句领域；非必须重写全文 |
| `dim_resolve.py` | 预测两维、定位策略 system 内联字符串 |

### D4：满血分类

模板已中性；若补领域说明，一句即可，避免与段多维主路径重复劳动。

## Risks / Trade-offs

- [模型仍偏喂养例] → OP 例补非喂养 create；事件名仍靠 EVENT 维  
- [other 过宽进 create] → other 仍要求「无关闲聊」；表外事件由 EVENT 空 id 处理  

## Migration Plan

1. 改文案发版。  
2. 手工：换尿布/疫苗/营养品口语进 create 轨而非 other。  
3. 回滚：恢复「母婴喂养」人设字符串。

## Open Questions

（无：C 与口径已拍板。）
