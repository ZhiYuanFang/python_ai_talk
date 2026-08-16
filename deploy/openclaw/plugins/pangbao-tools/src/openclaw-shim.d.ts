/**
 * 编译期模块声明：宿主运行时由 OpenClaw 提供真实 SDK。
 */
declare module "openclaw/plugin-sdk/tool-plugin" {
  export function defineToolPlugin(def: unknown): unknown;
}
