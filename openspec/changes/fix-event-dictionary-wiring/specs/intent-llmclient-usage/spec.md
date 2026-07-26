## ADDED Requirements

### Requirement: 使用单例 llm_client
`classify_intent` SHALL 使用模块级 `llm_client` 实例，并通过 `LLMModelConfig`（或等价结构）传入 provider/name/max_in_flight，不得调用 `LLMClient(provider=..., model_name=...)` 这种不被支持的构造方式。

#### Scenario: 分类不再因构造参数失败
- **WHEN** 向量匹配降级到 LLM 分类且模型配置合法
- **THEN** 节点 SHALL NOT 抛出 `LLMClient.__init__() got an unexpected keyword argument 'provider'`
- **AND** SHALL 调用 `llm_client.invoke`（或项目既有统一 invoke 签名）完成分类
