#!/bin/bash
set -xeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

COMMAND=${1:-}
WEKO_ROOT=${2:-}

if [[ -z "${COMMAND}" || -z "${WEKO_ROOT}" ]]; then
  echo "Usage: $0 <prepare|install|down> <weko_root_dir>" >&2
  exit 1
fi

if [[ ! -d "${WEKO_ROOT}" ]]; then
  echo "WEKO root directory not found: ${WEKO_ROOT}" >&2
  exit 1
fi

compose_file="${WEKO_ROOT}/docker-compose2.yml"

wait_for_url() {
  local url="$1"
  local attempts=30
  local delay=10
  for ((i=1; i<=attempts; i++)); do
    if curl -k --fail "$url"; then
      echo "${url} is reachable"
      return 0
    fi
    echo "Attempt ${i}/${attempts} failed for ${url}" >&2
    sleep "$delay"
  done
  echo "Timed out waiting for ${url}" >&2
  return 1
}

case "$COMMAND" in
  prepare)
    python3 "${SCRIPT_DIR}/weko_adjust_ports.py" \
      --keep-port nginx:80:80 \
      --keep-port nginx:443:443 \
      "${compose_file}"
    # Replace WEKO's nginx files with our simplified version
    cp "${SCRIPT_DIR}/../../docker/weko-nginx/Dockerfile" "${WEKO_ROOT}/nginx/Dockerfile"
    cp "${SCRIPT_DIR}/../../docker/weko-nginx/weko.conf" "${WEKO_ROOT}/nginx/weko.conf"
    ;;
  install)
    pushd "${WEKO_ROOT}"
    bash install.sh
    popd
    wait_for_url "http://localhost"
    wait_for_url "https://localhost"
    ;;
  down)
    pushd "${WEKO_ROOT}"
    docker compose -f docker-compose2.yml down -v || true
    popd
    ;;
  *)
    echo "Unknown command: ${COMMAND}" >&2
    exit 1
    ;;
esac
