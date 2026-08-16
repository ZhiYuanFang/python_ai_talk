#!/usr/bin/env bash
# OpenClaw Gateway 启动入口：在 gateway 监听前为三业务 agent 种子 models.json，
# 并把 DEEPSEEK_API_KEY 写入各 agent 的 auth store，避免 recreate 后空 catalog / missing-provider-auth。
set -euo pipefail

SEED_MODELS="${OPENCLAW_SEED_MODELS:-/openclaw/seed/models.json}"
AGENTS_ROOT="${OPENCLAW_AGENTS_ROOT:-/root/.openclaw/agents}"
# 与 openclaw.json5 agents.list 对齐的业务 agent id
AGENT_IDS=(intent clinic care_alert)

# 判断 models.json 是否为「空 providers」毒丸（或缺文件 / 缺 flash）
# Args: 目标文件路径
# Returns: 0=需要覆盖种子，1=已有可用目录可跳过
needs_models_seed() {
  local target="$1"
  if [[ ! -f "$target" ]]; then
    return 0
  fi
  # 空 providers 对象：启动 ensure 写回的 22 字节毒丸
  if grep -qE '"providers"[[:space:]]*:[[:space:]]*\{[[:space:]]*\}' "$target"; then
    return 0
  fi
  # 无 flash 模型 id 则视为不可用，覆盖为仓库种子
  if ! grep -q 'deepseek-v4-flash' "$target"; then
    return 0
  fi
  return 1
}

# 为单个 agent 写入非空 DeepSeek catalog（仅 env 名 marker，无明文 key）
# Args: agent id（如 care_alert）
seed_models_json() {
  local agent_id="$1"
  local agent_dir="${AGENTS_ROOT}/${agent_id}/agent"
  local target="${agent_dir}/models.json"
  mkdir -p "$agent_dir"
  if needs_models_seed "$target"; then
    cp -f "$SEED_MODELS" "$target"
    echo "openclaw-bootstrap: seeded models.json for agent=${agent_id}" >&2
  else
    echo "openclaw-bootstrap: keep existing models.json for agent=${agent_id}" >&2
  fi
}

# 将进程内 DEEPSEEK_API_KEY 经 CLI 写入该 agent 的 sqlite auth store
# Args: agent id
# Side Effects: 调用 openclaw models auth；失败只告警不阻断 Gateway 启动（便于只测进门）
seed_deepseek_auth() {
  local agent_id="$1"
  local agent_dir="${AGENTS_ROOT}/${agent_id}/agent"
  mkdir -p "$agent_dir"
  # 2026.7.1-2：用 OPENCLAW_AGENT_DIR 定点；DeepSeek sk- 形用 paste-api-key（stdin，避免 argv 泄密）
  if printf '%s\n' "$DEEPSEEK_API_KEY" | \
    OPENCLAW_AGENT_DIR="$agent_dir" \
    openclaw models auth paste-api-key --provider deepseek; then
    echo "openclaw-bootstrap: deepseek auth ok for agent=${agent_id}" >&2
  else
    echo "openclaw-bootstrap: WARN paste-api-key failed for agent=${agent_id} (check CLI / existing profile)" >&2
  fi
}

if [[ ! -f "$SEED_MODELS" ]]; then
  echo "openclaw-bootstrap: ERROR missing seed ${SEED_MODELS}" >&2
  exit 1
fi

for id in "${AGENT_IDS[@]}"; do
  seed_models_json "$id"
done

if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  for id in "${AGENT_IDS[@]}"; do
    seed_deepseek_auth "$id"
  done
else
  echo "openclaw-bootstrap: WARN DEEPSEEK_API_KEY empty; skip auth seed (chat may missing-provider-auth)" >&2
fi

# 将 compose/CMD 传入的参数原样交给 gateway（默认 openclaw gateway ...）
exec "$@"
