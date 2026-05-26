#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_FILE="${SCRIPT_DIR}/.state"

cd "${REPO_ROOT}"

load_env_defaults() {
  local env_file="$1"
  local line key
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "${line}" || "${line}" == \#* || "${line}" != *=* ]] && continue
    key="${line%%=*}"
    key="${key%"${key##*[![:space:]]}"}"
    if [[ -z "${!key+x}" ]]; then
      export "${line}"
    fi
  done < "${env_file}"
}

if [[ -f "${REPO_ROOT}/.env" ]]; then
  load_env_defaults "${REPO_ROOT}/.env"
fi
if [[ -f "${STATE_FILE}" ]]; then
  # shellcheck source=/dev/null
  . "${STATE_FILE}"
fi

if [[ -z "${HIRENEST_PARTICIPANT_ID:-}" ]]; then
  echo "HIRENEST_PARTICIPANT_ID is missing. Run ./scripts/setup.sh first." >&2
  exit 2
fi
if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  echo "GOOGLE_CLOUD_PROJECT is required" >&2
  exit 2
fi

REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
PREFIX="[${HIRENEST_PARTICIPANT_ID}] "
LOG_DIR="${REPO_ROOT}/.agent-runtime-temp"
mkdir -p "${LOG_DIR}"

DRY_RUN=0
ASSUME_YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -y|--yes) ASSUME_YES=1; shift ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--dry-run] [-y|--yes]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

GCP_TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
if [[ -z "${GCP_TOKEN}" ]]; then
  echo "Could not obtain an access token via gcloud." >&2
  exit 2
fi

INVENTORY_FILE="${LOG_DIR}/cleanup_inventory.tsv"
GCP_TOKEN="${GCP_TOKEN}" \
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
REGION="${REGION}" \
PREFIX="${PREFIX}" \
python3 - > "${INVENTORY_FILE}" <<'PY'
import json, os, sys, urllib.request, urllib.error

project = os.environ["GOOGLE_CLOUD_PROJECT"]
region = os.environ["REGION"]
token = os.environ["GCP_TOKEN"]
prefix = os.environ["PREFIX"]

url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/reasoningEngines?pageSize=200"
rows = []
try:
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
        for engine in data.get("reasoningEngines", []):
            display_name = engine.get("displayName", "")
            if display_name.startswith(prefix):
                rows.append((display_name, engine["name"].rsplit("/", 1)[-1]))
        page_token = data.get("nextPageToken")
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/reasoningEngines?pageSize=200&pageToken={page_token}" if page_token else None
except urllib.error.HTTPError as err:
    sys.stderr.write(f"ListReasoningEngines failed: HTTP {err.code} {err.reason}\n")
    sys.stderr.write(err.read().decode("utf-8", "replace") + "\n")
    sys.exit(1)

for row in sorted(rows):
    print(f"{row[0]}\t{row[1]}")
PY

total=$(wc -l < "${INVENTORY_FILE}" | tr -d ' ')
if [[ "${total}" -eq 0 ]]; then
  echo "No Agent Runtime resources found for ${PREFIX}"
  exit 0
fi

echo "Agent Runtime resources to delete:"
awk -F'\t' '{ printf "  - %s (%s)\n", $1, $2 }' "${INVENTORY_FILE}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "Dry run only."
  exit 0
fi

if [[ "${ASSUME_YES}" -ne 1 ]]; then
  read -r -p "Type DELETE to delete these ${total} resource(s): " confirmation
  if [[ "${confirmation}" != "DELETE" ]]; then
    echo "Aborted." >&2
    exit 1
  fi
fi

while IFS=$'\t' read -r display_name engine_id; do
  echo "Deleting ${display_name} (${engine_id})"
  GCP_TOKEN="${GCP_TOKEN}" \
  PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  REGION="${REGION}" \
  ENGINE_ID="${engine_id}" \
  python3 - <<'PY'
import json, os, time, urllib.request, urllib.error

project = os.environ["PROJECT"]
region = os.environ["REGION"]
token = os.environ["GCP_TOKEN"]
engine_id = os.environ["ENGINE_ID"]
base = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}"

req = urllib.request.Request(
    f"{base}/reasoningEngines/{engine_id}?force=true",
    method="DELETE",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req) as response:
    operation = json.load(response)

operation_name = operation.get("name", "")
while operation_name:
    poll = urllib.request.Request(
        f"https://{region}-aiplatform.googleapis.com/v1/{operation_name}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(poll) as response:
        current = json.load(response)
    if current.get("done"):
        break
    time.sleep(5)
PY
done < "${INVENTORY_FILE}"

echo "Cleanup complete for ${PREFIX}"
