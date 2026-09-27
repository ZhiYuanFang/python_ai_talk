## 1. Shared 聚合模块

- [x] 1.1 将 `care_alert/.../history_compact.py` 迁入 `app/shared/`（命名去 care_alert 前缀，如 `feeding_history_compact.py`），保留中文注释与 `(history_text, legend)` API
- [x] 1.2 care_alert 侧改为 import 共享模块（删除或薄 re-export 后删除旧文件），行为不变

## 2. 多 Agent 消费对齐

- [x] 2.1 growth_trajectory `generate`（及 design 约定的 `plan_next`）改注入共享 `history_text`，去掉原事件 JSON 主史块；不动 prior_feedback / qa / 画像
- [x] 2.2 clinic `clinic_answer` 在 needs_history 路径改注入共享聚合文本；去掉 `build_daily_history_summary` 与 slim JSON 主史块
- [x] 2.3 intent `speak_history` 在 `history_mode=daily` 改用共享 `history_text`（不输出 legend）；point / 父塌缩路径不动

## 3. 清理与校验

- [x] 3.1 删除 `build_daily_history_summary` 定义；全仓确认无引用
- [x] 3.2 全仓确认无残留 `build_care_alert_history_prompt_blocks` 旧路径（除有意兼容别名）
- [x] 3.3 `openspec validate unify-feeding-history-compact --strict` 通过
