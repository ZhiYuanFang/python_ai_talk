/**
 * Pangbao OpenClaw tools 插件
 *
 * 业务说明：
 * - 全部业务 tools 打 Python toolsBaseUrl（含 history 读写 + 飞轮 + 出卡）
 * - 请求头转发 x-pangbao-api-token（A Token）；由 Python 查租户 URL 并塑形
 * - 已废弃 historyBaseUrl 直打 Go
 */

import { Type, type Static } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const ConfigSchema = Type.Object({
  toolsBaseUrl: Type.Optional(
    Type.String({
      description: "Python /v1 基址，如 http://python-ai-talk:8000/v1",
    }),
  ),
});

type PluginConfig = Static<typeof ConfigSchema>;

const API_TOKEN_HEADER = "x-pangbao-api-token";

function envOr(cfg: string | undefined, envKey: string, fallback: string): string {
  const fromCfg = (cfg ?? "").trim();
  if (fromCfg) return fromCfg.replace(/\/$/, "");
  const fromEnv = (process.env[envKey] ?? "").trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return fallback.replace(/\/$/, "");
}

function toolsBase(config: PluginConfig): string {
  return envOr(config.toolsBaseUrl, "PANGBAO_TOOLS_BASE_URL", "http://127.0.0.1:8000/v1");
}

/** 从 OpenClaw 请求上下文尽力取出 A Token（spike：见 design 备注） */
function apiTokenFromCtx(ctx: Record<string, unknown>): string {
  const envTok = (process.env.PANGBAO_API_TOKEN ?? "").trim();
  if (envTok) return envTok;
  // Spike：OpenClaw 若把入站头挂到 ctx.headers 则可取；否则依赖进程环境 PANGBAO_API_TOKEN
  const headers = ctx.headers as Record<string, string> | undefined;
  if (headers?.[API_TOKEN_HEADER]) return headers[API_TOKEN_HEADER];
  if (headers?.["X-Pangbao-Api-Token"]) return headers["X-Pangbao-Api-Token"];
  return "";
}

async function httpJson(
  method: string,
  url: string,
  opts: { body?: unknown; apiToken?: string; signal?: AbortSignal },
): Promise<unknown> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.apiToken) headers[API_TOKEN_HEADER] = opts.apiToken;
  const res = await fetch(url, {
    method,
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });
  const text = await res.text();
  let parsed: unknown = text;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    /* 保留原文 */
  }
  if (!res.ok) {
    return { ok: false, status: res.status, body: parsed };
  }
  return parsed;
}

export default defineToolPlugin({
  id: "pangbao-tools",
  name: "Pangbao Tools",
  description: "Python shaped history + flywheel + care emit_cards",
  configSchema: ConfigSchema,
  tools: (tool) => [
    tool({
      name: "history_create",
      label: "History Create",
      description: "新增历史（经 Python 塑形短回执）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        eventId: Type.Number(),
        eventName: Type.Optional(Type.String()),
        eventUnit: Type.Optional(Type.String()),
        eventNumber: Type.Optional(Type.Number()),
        startTime: Type.Optional(Type.Number()),
        endTime: Type.Optional(Type.Number()),
        remark: Type.Optional(Type.String()),
        action: Type.Optional(Type.String()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/create`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_update",
      label: "History Update",
      description: "修改历史（经 Python）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        id: Type.Number(),
        eventNumber: Type.Optional(Type.Number()),
        startTime: Type.Optional(Type.Number()),
        endTime: Type.Optional(Type.Number()),
        remark: Type.Optional(Type.String()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/update`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_delete",
      label: "History Delete",
      description: "删除历史（经 Python）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        id: Type.Number(),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/delete`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_end_latest",
      label: "History End Latest",
      description: "结束最近未闭合（经 Python）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        eventId: Type.Optional(Type.Number()),
        endTime: Type.Optional(Type.Number()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/end_latest`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_filter",
      label: "History Filter",
      description: "筛选历史（Python 瘦结果）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        eventIds: Type.Optional(Type.String()),
        startTime: Type.Optional(Type.Number()),
        endTime: Type.Optional(Type.Number()),
        limit: Type.Optional(Type.Number()),
        remark: Type.Optional(Type.String()),
        ignoreTimeRange: Type.Optional(Type.Boolean()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/filter`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_list",
      label: "History List",
      description: "分页历史（Python 瘦结果）",
      parameters: Type.Object({
        deviceNo: Type.String(),
        page: Type.Optional(Type.Number()),
        pageSize: Type.Optional(Type.Number()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/list`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "history_options",
      label: "History Options",
      description: "事件选项（Python 精简）",
      parameters: Type.Object({}),
      async execute(_args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/history/options`, {
          body: {},
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "baby_profile",
      label: "Baby Profile",
      description: "宝宝画像（含月龄塑形）",
      parameters: Type.Object({
        deviceNo: Type.String(),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/baby/profile`, {
          body: args,
          apiToken: apiTokenFromCtx(ctx),
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "flywheel_intent_retrieve",
      label: "Flywheel Intent Retrieve",
      description: "检索 Intent 飞轮",
      parameters: Type.Object({
        query: Type.String(),
        n_results: Type.Optional(Type.Number()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/flywheel/intent/retrieve`, {
          body: args,
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "flywheel_intent_record",
      label: "Flywheel Intent Record",
      description: "写入 Intent 飞轮",
      parameters: Type.Object({
        document: Type.String(),
        payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/flywheel/intent/record`, {
          body: args,
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "flywheel_clinic_retrieve",
      label: "Flywheel Clinic Retrieve",
      description: "检索 Clinic 飞轮",
      parameters: Type.Object({
        query: Type.String(),
        n_results: Type.Optional(Type.Number()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/flywheel/clinic/retrieve`, {
          body: { query: args.query, n_results: args.n_results ?? 1 },
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "flywheel_clinic_record",
      label: "Flywheel Clinic Record",
      description: "写入 Clinic 飞轮",
      parameters: Type.Object({
        standalone_question: Type.Optional(Type.String()),
        answer: Type.Optional(Type.String()),
        age_band: Type.Optional(Type.String()),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/flywheel/clinic/record`, {
          body: args,
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "clinic_judge_implicit_acceptance",
      label: "Clinic Judge",
      description: "隐式采纳判定",
      parameters: Type.Object({
        user_text: Type.String(),
        suggestion_text: Type.String(),
        model_config: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/clinic/judge_implicit_acceptance`, {
          body: args,
          signal: ctx.signal,
        });
      },
    }),
    tool({
      name: "emit_care_cards",
      label: "Emit Care Cards",
      description: "Care 出卡",
      parameters: Type.Object({
        device_no: Type.Optional(Type.String()),
        day: Type.Optional(Type.String()),
        items: Type.Array(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(args, config, ctx) {
        ctx.signal?.throwIfAborted();
        return httpJson("POST", `${toolsBase(config)}/tools/care/emit_cards`, {
          body: args,
          signal: ctx.signal,
        });
      },
    }),
  ],
});
