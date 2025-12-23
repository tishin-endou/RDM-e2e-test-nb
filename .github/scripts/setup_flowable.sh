#!/bin/bash
set -xeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

COMMAND=${1:-}
FLOWABLE_ROOT=${2:-}
RDM_ROOT=${3:-}

if [[ -z "${COMMAND}" ]]; then
  echo "Usage: $0 <prepare|install|down> <flowable_root_dir> [rdm_root_dir]" >&2
  exit 1
fi

wait_for_url() {
  local url="$1"
  local attempts=30
  local delay=10
  for ((i=1; i<=attempts; i++)); do
    if curl -f "$url" >/dev/null 2>&1; then
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
    if [[ -z "${FLOWABLE_ROOT}" || -z "${RDM_ROOT}" ]]; then
      echo "Usage: $0 prepare <flowable_root_dir> <rdm_root_dir>" >&2
      exit 1
    fi

    # Ensure RDM workflow keys directory exists
    mkdir -p "${RDM_ROOT}/addons/workflow/tests/keys"

    # Generate RSA key pair for RDM service (used by RDM to sign tokens to gateway)
    openssl genrsa -out "${RDM_ROOT}/addons/workflow/tests/keys/rdm-service-v1.key" 2048
    openssl rsa -in "${RDM_ROOT}/addons/workflow/tests/keys/rdm-service-v1.key" -pubout \
      -out "${RDM_ROOT}/addons/workflow/tests/keys/rdm-service-v1.pub"

    # Generate RSA key pair for gateway (used by gateway to sign tokens back to RDM)
    openssl genrsa -out "${RDM_ROOT}/addons/workflow/tests/keys/gateway-dev-v1.key" 2048
    openssl rsa -in "${RDM_ROOT}/addons/workflow/tests/keys/gateway-dev-v1.key" -pubout \
      -out "${RDM_ROOT}/addons/workflow/tests/keys/gateway-dev-v1.pub"

    # Create workflow addon local.py for RDM
    mkdir -p "${RDM_ROOT}/addons/workflow/settings"
    cat > "${RDM_ROOT}/addons/workflow/settings/local.py" << 'EOF'
RDM_TO_WORKFLOW_GATEWAY_KEYS = [
    {
        'kid': 'rdm-service-v1',
        'alg': 'RS256',
        'public_key_path': '/code/addons/workflow/tests/keys/rdm-service-v1.pub',
        'private_key_path': '/code/addons/workflow/tests/keys/rdm-service-v1.key',
    },
]
EOF

    # Copy keys to gateway config
    cp "${RDM_ROOT}/addons/workflow/tests/keys/rdm-service-v1.key" "${FLOWABLE_ROOT}/config/rdm-service.key"
    cp "${RDM_ROOT}/addons/workflow/tests/keys/gateway-dev-v1.key" "${FLOWABLE_ROOT}/config/gateway-dev-v1.key"

    # Create keyset.json with the RDM public key for gateway
    RDM_PUBLIC_KEY=$(cat "${RDM_ROOT}/addons/workflow/tests/keys/rdm-service-v1.pub" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))")
    cat > "${FLOWABLE_ROOT}/config/keyset.json" << EOF
{
  "keys": [
    {
      "kid": "rdm-service-v1",
      "alg": "RS256",
      "public_key": ${RDM_PUBLIC_KEY}
    }
  ]
}
EOF

    # Generate Fernet encryption key
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    # Create .env file for gateway CI environment
    cat > "${FLOWABLE_ROOT}/.env" << EOF
# Flowable REST admin credentials
FLOWABLE_REST_APP_ADMIN_USER_ID=rest-admin
FLOWABLE_REST_APP_ADMIN_PASSWORD=rest-admin

# Gateway -> Flowable wiring
FLOWABLE_REST_BASE_URL=http://flowable:8080/flowable-rest

# RDM keyset configuration
RDM_KEYSET_PATH=/app/config/keyset.json

# Gateway internal wiring
GATEWAY_INTERNAL_URL=http://gateway:8088
RDM_ALLOWED_DOMAINS=http://192.168.168.167:5000
RDM_ALLOWED_API_DOMAINS=http://192.168.168.167:8000
RDM_ALLOWED_WATERBUTLER_URLS=http://192.168.168.167:7777

# Database connection
DATABASE_URL=postgresql://gateway:gateway@postgres:5432/gateway

# Gateway signing key
GATEWAY_SIGNING_KEY_ID=gateway-dev-v1
GATEWAY_SIGNING_PRIVATE_KEY_PATH=/app/config/gateway-dev-v1.key

# Encryption key for stored delegation tokens
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EOF
    echo "Flowable gateway configuration prepared"
    ;;
  install)
    if [[ -z "${FLOWABLE_ROOT}" || ! -d "${FLOWABLE_ROOT}" ]]; then
      echo "Flowable root directory not found: ${FLOWABLE_ROOT}" >&2
      exit 1
    fi

    pushd "${FLOWABLE_ROOT}"

    # Build and start the stack
    docker compose up -d --build

    popd

    # Wait for gateway to be ready
    wait_for_url "http://192.168.168.167:8088/healthz"

    # Initialize database
    pushd "${FLOWABLE_ROOT}"
    docker compose run --rm gateway python -m gateway.init_db
    popd

    echo "Flowable gateway installed"
    ;;
  down)
    if [[ -z "${FLOWABLE_ROOT}" || ! -d "${FLOWABLE_ROOT}" ]]; then
      echo "Flowable root directory not found, skipping cleanup"
      exit 0
    fi

    pushd "${FLOWABLE_ROOT}"
    docker compose down -v || true
    popd
    ;;
  *)
    echo "Unknown command: ${COMMAND}" >&2
    exit 1
    ;;
esac
