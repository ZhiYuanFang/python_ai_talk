/**
 * Pangbao OpenClaw tools 插件
 *
 * 业务说明：
 * - history_*：直打 Go REST（四写 + filter/list/options/profile），复用 top_k 语义由 Go 侧保证
 * - flywheel_* / clinic_judge / emit_care_cards：打 Python /v1/tools/*
 * - Clinic/Care agent ACL 在 openclaw.json5 中禁止写史 tool 名
 */
import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
const ConfigSchema = Type.Object({
    historyBaseUrl: Type.Optional(Type.String({ description: "Go 历史 API 基址，如 http://go-ai-talk:8001" })),
    historyToken: Type.Optional(Type.String({ description: "可选 Bearer，调 Go 内网接口" })),
    toolsBaseUrl: Type.Optional(Type.String({
        description: "Python 飞轮/出卡 tools 基址，如 http://python-ai-talk:8000/v1",
    })),
});
function envOr(cfg, envKey, fallback) {
    const fromCfg = (cfg ?? "").trim();
    if (fromCfg)
        return fromCfg.replace(/\/$/, "");
    const fromEnv = (process.env[envKey] ?? "").trim();
    if (fromEnv)
        return fromEnv.replace(/\/$/, "");
    return fallback.replace(/\/$/, "");
}
function historyBase(config) {
    return envOr(config.historyBaseUrl, "PANGBAO_HISTORY_BASE_URL", "http://127.0.0.1:8001");
}
function toolsBase(config) {
    return envOr(config.toolsBaseUrl, "PANGBAO_TOOLS_BASE_URL", "http://127.0.0.1:8000/v1");
}
function historyToken(config) {
    return (config.historyToken ?? process.env.PANGBAO_HISTORY_TOKEN ?? "").trim();
}
async function httpJson(method, url, opts) {
    const headers = { Accept: "application/json" };
    if (opts.body !== undefined)
        headers["Content-Type"] = "application/json";
    if (opts.token)
        headers.Authorization = `Bearer ${opts.token}`;
    const res = await fetch(url, {
        method,
        headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        signal: opts.signal,
    });
    const text = await res.text();
    let parsed = text;
    try {
        parsed = text ? JSON.parse(text) : null;
    }
    catch {
        /* 保留原文 */
    }
    if (!res.ok) {
        return { ok: false, status: res.status, body: parsed };
    }
    return parsed;
}
function qs(params) {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === "")
            continue;
        sp.set(k, String(v));
    }
    const s = sp.toString();
    return s ? `?${s}` : "";
}
export default defineToolPlugin({
    id: "pangbao-tools",
    name: "Pangbao Tools",
    description: "History REST + flywheel + care emit_cards for Pangbao agents",
    configSchema: ConfigSchema,
    tools: (tool) => [
        // —— Intent 写史（Clinic/Care ACL 不得 allow）——
        tool({
            name: "history_create",
            label: "History Create",
            description: "新增历史事件（Go POST /device/history/api/event/add）",
            parameters: Type.Object({
                deviceNo: Type.String(),
                eventId: Type.Number(),
                eventName: Type.Optional(Type.String()),
                eventUnit: Type.Optional(Type.String()),
                eventNumber: Type.Optional(Type.Number()),
                startTime: Type.Optional(Type.Number()),
                endTime: Type.Optional(Type.Number()),
                remark: Type.Optional(Type.String()),
                action: Type.Optional(Type.String({ description: "start|one|end" })),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${historyBase(config)}/device/history/api/event/add`, {
                    body: args,
                    token: historyToken(config),
                    signal: ctx.signal,
                });
            },
        }),
        tool({
            name: "history_update",
            label: "History Update",
            description: "修改历史事件（Go POST /device/history/api/event/update）",
            parameters: Type.Object({
                deviceNo: Type.String(),
                id: Type.Number(),
                eventId: Type.Optional(Type.Number()),
                eventName: Type.Optional(Type.String()),
                eventUnit: Type.Optional(Type.String()),
                eventNumber: Type.Optional(Type.Number()),
                startTime: Type.Optional(Type.Number()),
                endTime: Type.Optional(Type.Number()),
                remark: Type.Optional(Type.String()),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${historyBase(config)}/device/history/api/event/update`, {
                    body: args,
                    token: historyToken(config),
                    signal: ctx.signal,
                });
            },
        }),
        tool({
            name: "history_delete",
            label: "History Delete",
            description: "删除历史事件（Go POST /device/history/api/event/delete）",
            parameters: Type.Object({
                deviceNo: Type.String(),
                id: Type.Number(),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${historyBase(config)}/device/history/api/event/delete`, {
                    body: args,
                    token: historyToken(config),
                    signal: ctx.signal,
                });
            },
        }),
        tool({
            name: "history_end_latest",
            label: "History End Latest",
            description: "结束最近一条未闭合历史（Go POST /device/history/api/event/end-latest）",
            parameters: Type.Object({
                deviceNo: Type.String(),
                eventId: Type.Optional(Type.Number()),
                eventName: Type.Optional(Type.String()),
                endTime: Type.Optional(Type.Number()),
                remark: Type.Optional(Type.String()),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${historyBase(config)}/device/history/api/event/end-latest`, { body: args, token: historyToken(config), signal: ctx.signal });
            },
        }),
        // —— 只读历史 ——
        tool({
            name: "history_filter",
            label: "History Filter",
            description: "筛选历史（Go GET filter；limit 即 top_k 语义）",
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
                const url = `${historyBase(config)}/device/history/api/filter` +
                    qs({
                        deviceNo: args.deviceNo,
                        eventIds: args.eventIds,
                        startTime: args.startTime,
                        endTime: args.endTime,
                        limit: args.limit,
                        remark: args.remark,
                        ignoreTimeRange: args.ignoreTimeRange,
                    });
                return httpJson("GET", url, { token: historyToken(config), signal: ctx.signal });
            },
        }),
        tool({
            name: "history_list",
            label: "History List",
            description: "分页历史列表（Go GET list）",
            parameters: Type.Object({
                deviceNo: Type.String(),
                page: Type.Optional(Type.Number()),
                pageSize: Type.Optional(Type.Number()),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                const url = `${historyBase(config)}/device/history/api/list` +
                    qs({
                        deviceNo: args.deviceNo,
                        page: args.page,
                        pageSize: args.pageSize,
                    });
                return httpJson("GET", url, { token: historyToken(config), signal: ctx.signal });
            },
        }),
        tool({
            name: "history_options",
            label: "History Options",
            description: "事件可选项（Go GET event/options）",
            parameters: Type.Object({}),
            async execute(_args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("GET", `${historyBase(config)}/device/history/api/event/options`, {
                    token: historyToken(config),
                    signal: ctx.signal,
                });
            },
        }),
        tool({
            name: "baby_profile",
            label: "Baby Profile",
            description: "宝宝画像/生日（Go GET birthday）",
            parameters: Type.Object({
                deviceNo: Type.String(),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                const url = `${historyBase(config)}/device/history/api/birthday` +
                    qs({ deviceNo: args.deviceNo });
                return httpJson("GET", url, { token: historyToken(config), signal: ctx.signal });
            },
        }),
        // —— 飞轮（无 Care）——
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
            description: "写入 Intent 飞轮（可移植载荷）",
            parameters: Type.Object({
                document: Type.String(),
                payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${toolsBase(config)}/tools/flywheel/intent/record`, {
                    body: { document: args.document, payload: args.payload ?? {} },
                    signal: ctx.signal,
                });
            },
        }),
        tool({
            name: "flywheel_clinic_retrieve",
            label: "Flywheel Clinic Retrieve",
            description: "检索 Clinic Q&A 飞轮（若后端未实现则返回空）",
            parameters: Type.Object({
                query: Type.String(),
                n_results: Type.Optional(Type.Number()),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                // 后端若无 retrieve 路由，仍返回可解析结构，避免打断 agent
                try {
                    return await httpJson("POST", `${toolsBase(config)}/tools/flywheel/clinic/retrieve`, { body: args, signal: ctx.signal });
                }
                catch {
                    return { hits: [], ok: false };
                }
            },
        }),
        tool({
            name: "flywheel_clinic_record",
            label: "Flywheel Clinic Record",
            description: "Clinic 隐式采纳后写飞轮",
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
            label: "Clinic Judge Implicit Acceptance",
            description: "判定用户话是否隐式采纳上轮建议（不经 Go）",
            parameters: Type.Object({
                user_text: Type.String(),
                suggestion_text: Type.String(),
                model_config: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${toolsBase(config)}/tools/clinic/judge_implicit_acceptance`, { body: args, signal: ctx.signal });
            },
        }),
        tool({
            name: "emit_care_cards",
            label: "Emit Care Cards",
            description: "Care Alert 结构化出卡；权威 items 供 Go 写入日缓存",
            parameters: Type.Object({
                device_no: Type.Optional(Type.String()),
                day: Type.Optional(Type.String()),
                items: Type.Array(Type.Record(Type.String(), Type.Unknown())),
            }),
            async execute(args, config, ctx) {
                ctx.signal?.throwIfAborted();
                return httpJson("POST", `${toolsBase(config)}/tools/care/emit_cards`, {
                    body: {
                        device_no: args.device_no ?? "",
                        day: args.day ?? "",
                        items: args.items ?? [],
                    },
                    signal: ctx.signal,
                });
            },
        }),
    ],
});
