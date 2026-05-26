#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_FILE="${SCRIPT_DIR}/.state"

cd "${REPO_ROOT}"

sanitize_id() {
  printf "%s" "$1" | sed -E 's/[^A-Za-z0-9_-]+/_/g; s/^_+//; s/_+$//'
}

existing_id=""
if [[ -f "${STATE_FILE}" ]]; then
  # shellcheck source=/dev/null
  . "${STATE_FILE}"
  existing_id="${HIRENEST_PARTICIPANT_ID:-}"
fi

if [[ -n "${existing_id}" ]]; then
  read -r -p "connpass ID [${existing_id}]: " raw_id
  raw_id="${raw_id:-${existing_id}}"
else
  read -r -p "connpass ID: " raw_id
fi

participant_id="$(sanitize_id "${raw_id}")"
if [[ -z "${participant_id}" ]]; then
  echo "connpass ID is required" >&2
  exit 2
fi

project_id="${GOOGLE_CLOUD_PROJECT:-}"
if [[ -z "${project_id}" ]] && command -v gcloud >/dev/null 2>&1; then
  project_id="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "${project_id}" || "${project_id}" == "(unset)" ]]; then
  read -r -p "Google Cloud project ID: " project_id
fi
if [[ -z "${project_id}" || "${project_id}" == "(unset)" ]]; then
  echo "Google Cloud project ID is required" >&2
  exit 2
fi

printf "HIRENEST_PARTICIPANT_ID=%s\n" "${participant_id}" > "${STATE_FILE}"

cat > .env <<EOF
ADK_MODEL=gemini-2.5-flash
HIRENEST_PARTICIPANT_ID=${participant_id}

TICKET_HISTORY_A2A_URL=http://localhost:8101
KNOWLEDGE_BASE_A2A_URL=http://localhost:8102
ACCOUNT_CONTEXT_A2A_URL=http://localhost:8103
INCIDENT_STATUS_A2A_URL=http://localhost:8104
ESCALATION_POLICY_A2A_URL=http://localhost:8105
DIAGNOSTICS_A2A_URL=http://localhost:8107

GOOGLE_API_KEY=
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=${project_id}
GOOGLE_CLOUD_LOCATION=us-central1
HIRENEST_TRACE_TO_CLOUD=false

HIRENEST_AGENT_SEARCH_SERVING_CONFIG=

HIRENEST_DISCORD_DRY_RUN=false
HIRENEST_DISCORD_WEBHOOK_URL=

HIRENEST_DATA_DIR=
EOF

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

uv sync --extra dev

echo "Setup complete for [${participant_id}]."
