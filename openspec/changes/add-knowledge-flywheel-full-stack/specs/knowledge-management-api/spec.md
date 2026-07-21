## ADDED Requirements

### Requirement: 管理员可以上传 MD 文件到知识库
系统 SHALL 提供 `/v1/knowledge/upload` 接口，支持管理员上传 MD 文件，文件上传后自动切分、Embedding 并写入向量库。

#### Scenario: 成功上传单个 MD 文件
- **WHEN** 管理员通过 POST 请求上传一个有效的 MD 文件
- **THEN** 系统返回 200 状态码，包含文档 ID 和向量数量

#### Scenario: 上传无效文件格式
- **WHEN** 管理员上传非 MD/TXT 格式的文件
- **THEN** 系统返回 400 状态码，提示文件格式错误

### Requirement: 管理员可以列出知识库文档
系统 SHALL 提供 `/v1/knowledge/list` 接口，支持分页和分类筛选。

#### Scenario: 列出所有文档（默认分页）
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/list`
- **THEN** 系统返回文档列表，默认每页 20 条

#### Scenario: 按分类筛选文档
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/list?category=喂养知识`
- **THEN** 系统仅返回喂养知识分类下的文档

### Requirement: 管理员可以获取文档详情
系统 SHALL 提供 `/v1/knowledge/{doc_id}` 接口，返回文档完整内容和元数据。

#### Scenario: 获取存在的文档
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/{doc_id}`，且文档存在
- **THEN** 系统返回文档内容和元数据

#### Scenario: 获取不存在的文档
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/{invalid_doc_id}`
- **THEN** 系统返回 404 状态码，提示文档不存在

### Requirement: 管理员可以更新文档内容
系统 SHALL 提供 PUT `/v1/knowledge/{doc_id}` 接口，更新文档内容并重建向量。

#### Scenario: 更新文档成功
- **WHEN** 管理员发起 PUT 请求更新文档内容
- **THEN** 系统返回 200 状态码，文档内容和向量已更新

### Requirement: 管理员可以删除文档
系统 SHALL 提供 DELETE `/v1/knowledge/{doc_id}` 接口，删除文档及其所有向量。

#### Scenario: 删除文档成功
- **WHEN** 管理员发起 DELETE 请求删除文档
- **THEN** 系统返回 200 状态码，文档和向量已删除

### Requirement: 获取知识库统计信息
系统 SHALL 提供 `/v1/knowledge/stats` 接口，返回文档数、向量数、分类分布等统计信息。

#### Scenario: 获取统计信息
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/stats`
- **THEN** 系统返回文档总数、向量总数、各分类文档数

### Requirement: 获取所有知识分类
系统 SHALL 提供 `/v1/knowledge/categories` 接口，返回所有知识分类列表。

#### Scenario: 获取分类列表
- **WHEN** 管理员发起 GET 请求到 `/v1/knowledge/categories`
- **THEN** 系统返回分类列表，包含分类名称和文档数
