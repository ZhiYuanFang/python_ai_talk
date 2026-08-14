## Context

多处对 LLM 输出做 `json.loads`（意图分类、澄清、护理留意、judge 节点），仅剥 \`\`\` 围栏。模型仍会插入 `//` 说明。用户要求：共享去注释 → 各解析点接入；先去注释再格式化/解析。

## Goals / Non-Goals

**Goals:**

- 共享、可复用的「去注释 + 解析」工具，引号内内容安全。
- 所有对 LLM 原文的 JSON 解析点统一走该工具（或明确薄封装）。
- 解析成功后可用标准 `json.dumps`/`loads` 规范化对象（「再格式化」= 干净结构，非美化半残文本）。

**Non-Goals:**

- 不新增同模 LLM 重试、不换模。
- 本期不做 `op`/`target_type` 强制对齐（可另开 change）。
- 不写测试文件；手工用带 `//` 的样例核对即可。
- 默认不引入 `json5` 包；自研扫描足够则优先自研。

## Decisions

### 1. 共享模块位置

- **选择**：`app/shared/llm_json.py`（或等价名），导出例如 `strip_llm_json_comments`、`loads_llm_json`。
- **理由**：feeding/clinic/care_alert/shared 节点均可依赖 shared；禁止 feeding↔clinic 互引。

### 2. 去注释算法

- **选择**：单遍扫描，跟踪双引号字符串与转义；在字符串外删除 `//` 行注释、`/* */` 块注释；可选删除字符串外以 `#` 开头的整行注释（若与业务冲突可只做 // 与 /* */）。
- **理由**：裸正则会破坏 `"http://..."`。
- **备选**：json5 库 → 增加依赖，本期不优先。

### 3. 管线顺序

- **选择**：`strip` 空白 → 去 markdown 围栏 → 去注释 →（可选）正则抠首个 `{...}` → `json.loads` → 返回 `dict`；调用方可再 `json.dumps` 打日志。
- **理由**：与现有围栏逻辑合并，避免重复。

### 4. 接入点清单

- **选择**：至少接入：
  - `classify_intent._parse_intent_result`
  - `clarification._parse_llm_clarify_json`
  - `generate_care_alerts._extract_json_object`
  - `judge_data_requirement` / `judge_needs_history` 中对 LLM 输出的 `json.loads`
- **理由**：用户要求「各解析点」；扫仓补漏同类入口。

### 5. 失败行为

- **选择**：去注释后仍非法 → 各调用方保持原降级（分类→conversation、澄清→None、care_alert→空等），仅改善「仅因注释失败」的情况。

## Risks / Trade-offs

- [误删字符串内注释标记] → 引号状态机；手工样例含 URL。
- [尾逗号等非注释语法] → 本工具不修；仍走既有失败路径。
- [漏接解析点] → tasks 要求 grep `json.loads` 扫一遍。

## Migration Plan

- 纯内部解析增强，无 API 迁移；可独立发布。

## Open Questions

- 无（`#` 注释：实现时默认支持字符串外 `#` 行注释；若某 prompt 依赖 `#` 在结构外作数据则再收窄）。
