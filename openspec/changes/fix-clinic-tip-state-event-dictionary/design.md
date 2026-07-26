## Context

路由层已向 clinic/tip 初始 state 写入 `event_dictionary`（见 `fix-event-dictionary-wiring`），Go history `data.list` 解析亦已对齐。本地复现确认：LangGraph 对 TypedDict State 只保留已声明键，`ClinicState`/`TipState` 缺字段导致进图后字典被丢，`judge_data_requirement` 误报空。生产同时仍有 `validation_alias` 的 `UnsupportedFieldAttributeWarning`（赋值式 `Field(..., validation_alias=...)` 在部分 schema 生成路径无效）。

## Goals / Non-Goals

**Goals:**
- Clinic/Tip 图执行期间保留路由注入的 `event_dictionary`
- 字典非空时 judge 不再因 State 丢字段而降级默认需求
- 消除 clinic/tip/intent 入站的 device_no `UnsupportedFieldAttributeWarning`，且 snake/camel 双收仍可用

**Non-Goals:**
- 修改 Go 事件 options 响应格式或 HISTORY_SERVICE_URL
- 改动 event_cache / http_client 解包逻辑
- 修改 DeepSeek 模型名默认值
- 将事件字典失败从 fail-fast 改为静默降级（保持现状）

## Decisions

### 决策 1：在 TypedDict 补通道，而非改 LangGraph 配置

**选择**：`ClinicState` / `TipState` 增加 `event_dictionary: List[Dict[str, Any]]`，文档注释标明由路由注入。

**替代**：在 `judge_data_requirement` 内自行拉缓存 —— 隐藏依赖、与 Intent 路径不一致，排除。

**对齐**：字段名与 `IntentState.event_dictionary` 一致，便于 `call_clinic_agent` 透传。

### 决策 2：字段级 Annotated，禁止共享类型别名

**选择**：

```python
device_no: Annotated[
    str,
    Field(
        validation_alias=AliasChoices("device_no", "deviceNo"),
        description="...",
    ),
]
```

写在每个请求模型字段上；保留 `ConfigDict(populate_by_name=True)`。

**替代**：
- 恢复模块级 `DeviceNoField = Annotated[...]` —— 已验证触发同类警告，禁止
- 仅 `str = Field(..., validation_alias=...)` —— 生产仍警告，放弃
- 去掉 camel 双收 —— Go 已 snake，可做但过渡期保留双收更安全

### 决策 3：验证方式

**选择**：单元/脚本级：构造含非空 `event_dictionary` 的初始 state 跑 clinic（或最小图）到 judge，断言 state 仍非空；对三模型 `model_validate` + warnings 捕获无 `UnsupportedFieldAttributeWarning`。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 补字段后仍「为空」 | 区分日志：cache「兄弟仓返回空」vs judge「为空」；再查 history 实响应 |
| Annotated 在某 pydantic 小版本仍警告 | 以生产同版本（3.12 + 镜像内 pydantic）冒烟；必要时仅收 snake |
| tip 声明字段但偶发未注入 | 路由已注入；缺省 `total=False` 允许缺省，judge 仍可降级 |

## Migration Plan

1. 合并 TypedDict + schema 修改  
2. 重建 Python 镜像并部署  
3. 观察 clinic stream：无故「字典为空」消失（字典可用时）；无 validation_alias 警告  
4. 回滚：回退镜像  

## Open Questions

1. 部署后若 cache 仍拉到 `[]`，是否需要单独排查 history→device 数据（本 change 不包含）。
