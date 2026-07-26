## ADDED Requirements

### Requirement: 空列表不写入长 TTL 缓存
当兄弟仓返回的事件字典为空列表时，`EventCache` SHALL NOT 将其作为成功结果写入默认长 TTL 缓存（24h），以免后续请求长期命中空缓存。

#### Scenario: 空结果不毒化缓存
- **WHEN** `http_client.get_event_dictionary()` 返回 `[]`
- **THEN** 缓存中 SHALL NOT 长期保存该空列表作为命中项
- **AND** 日志 SHALL 记录空结果警告（标明未缓存或仅短时策略）

### Requirement: 拉取失败可观测
当获取事件字典因 HTTP/网络错误失败时，系统 SHALL 记录含失败原因的错误日志，且 SHALL NOT 将失败伪造成已缓存的空字典成功路径。

#### Scenario: HTTP 失败不静默变空缓存
- **WHEN** 兄弟仓请求抛出 HTTP 错误
- **THEN** 错误 SHALL 向上传播或被明确记录
- **AND** SHALL NOT 写入「成功空列表」的长 TTL 缓存项
