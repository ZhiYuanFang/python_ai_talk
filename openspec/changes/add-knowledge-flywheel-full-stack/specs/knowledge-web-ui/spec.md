## ADDED Requirements

### Requirement: Vue 前端独立目录隔离
前端代码 SHALL 放置在独立的 `web/` 目录下，与 Python 服务端代码完全隔离。

#### Scenario: 前端目录结构
- **WHEN** 查看项目根目录
- **THEN** `web/` 目录独立存在，包含 `src/`、`public/`、`dist/` 等子目录

### Requirement: 知识管理后台页面
前端 SHALL 提供知识管理后台页面，支持文档上传、列表查看、编辑和删除。

#### Scenario: 上传知识文档
- **WHEN** 管理员在后台页面选择 MD 文件并点击上传
- **THEN** 文件被上传到服务器，页面显示上传成功提示

#### Scenario: 查看文档列表
- **WHEN** 管理员进入知识管理页面
- **THEN** 页面显示所有文档列表，支持分页和筛选

#### Scenario: 删除文档
- **WHEN** 管理员点击文档的删除按钮并确认
- **THEN** 文档被删除，页面刷新显示更新后的列表

### Requirement: 知识库统计仪表盘
前端 SHALL 提供仪表盘页面，展示知识库统计信息和反馈趋势。

#### Scenario: 查看统计数据
- **WHEN** 管理员进入仪表盘页面
- **THEN** 页面显示文档总数、向量总数、各分类统计

#### Scenario: 查看反馈趋势
- **WHEN** 管理员进入仪表盘页面
- **THEN** 页面显示反馈趋势图表（按时间维度）

### Requirement: 前端构建产物由 FastAPI 托管
前端构建产物 SHALL 放置在 `web/dist/` 目录，由 FastAPI 静态文件服务托管。

#### Scenario: 访问前端页面
- **WHEN** 用户访问 Python 服务的根路径
- **THEN** FastAPI 返回前端构建的静态文件
