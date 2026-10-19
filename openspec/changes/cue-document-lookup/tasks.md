## 1. 按原文过滤

- [x] 1.1 九个飞轮 store 增加按 trim 后 document 精确过滤的读取，并附中文业务注释
- [x] 1.2 新增 `GET /v1/admin/cues/by-document`：空串 400；聚合九个维度；任一失败则整次 500
- [x] 1.3 响应含 `dimension`（op/intent/qty/time/remark/read_source/predict/history_speak/locate）、`collection`、`id`、`document`、`payload`
