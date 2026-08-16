/**
 * Pangbao OpenClaw tools 插件
 *
 * 业务说明：
 * - history_*：直打 Go REST（四写 + filter/list/options/profile），复用 top_k 语义由 Go 侧保证
 * - flywheel_* / clinic_judge / emit_care_cards：打 Python /v1/tools/*
 * - Clinic/Care agent ACL 在 openclaw.json5 中禁止写史 tool 名
 */
declare const _default: unknown;
export default _default;
