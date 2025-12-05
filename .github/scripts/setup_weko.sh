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
    # Apply patch to allow HTTP redirect URIs when OAUTHLIB_INSECURE_TRANSPORT is set
    patch -d "${WEKO_ROOT}" -p1 < "${SCRIPT_DIR}/../patches/weko-oauth2-insecure-transport.patch"
    # Generate self-signed certificate for WEKO nginx with SAN for IP address
    mkdir -p "${WEKO_ROOT}/nginx/keys"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout "${WEKO_ROOT}/nginx/keys/server.key" \
      -out "${WEKO_ROOT}/nginx/keys/server.crt" \
      -subj "/CN=192.168.168.167" \
      -addext "subjectAltName=IP:192.168.168.167"
    ;;
  install)
    pushd "${WEKO_ROOT}"
    bash install.sh
    popd
    wait_for_url "http://192.168.168.167"
    wait_for_url "https://192.168.168.167"

    # Verify WEKO nginx is using our generated certificate
    echo "=== WEKO Certificate Verification ==="
    expected_fingerprint=$(openssl x509 -in "${WEKO_ROOT}/nginx/keys/server.crt" -noout -fingerprint -sha256)
    actual_fingerprint=$(echo | openssl s_client -connect 192.168.168.167:443 | openssl x509 -noout -fingerprint -sha256)
    echo "Expected: ${expected_fingerprint}"
    echo "Actual:   ${actual_fingerprint}"
    if [ "${expected_fingerprint}" = "${actual_fingerprint}" ]; then
      echo "Certificate verification: OK"
    else
      echo "Certificate verification: MISMATCH"
      exit 1
    fi
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
