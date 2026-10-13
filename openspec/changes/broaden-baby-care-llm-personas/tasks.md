## 1. system.py 人设与 other

- [x] 1.1 统一改 SEGMENT_TYPE / HISTORY_SPEAK / EVENT / TIME / QTY / SHAPE / REMARK / SPLIT / PENDING 人设为宝宝照护记录
- [x] 1.2 OP：other 改为「与宝宝照护记录无关」；补换尿布/营养品/疫苗等 create 例
- [x] 1.3（可选）INTENT_CLASSIFICATION 补一句领域说明

## 2. 内联人设

- [x] 2.1 `dim_resolve` 预测两维、定位策略人设同步放宽
- [x] 2.2 审计 feeding 内其它「母婴喂养」LLM system 内联并改完

## 3. 验收

- [ ] 3.1 手工：换尿布了 / 打疫苗了 → 不定 other（宜 create）
- [ ] 3.2 手工：纯闲聊仍可 other
