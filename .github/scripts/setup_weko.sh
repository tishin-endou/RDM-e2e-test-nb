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
    # Apply patch to fix chardet TypeError on ZIP filename handling
    patch -d "${WEKO_ROOT}" -p1 < "${SCRIPT_DIR}/../patches/weko-chardet-fix.patch"
    # Apply patch to delay file content extraction task to avoid ES version conflict
    patch -d "${WEKO_ROOT}" -p1 < "${SCRIPT_DIR}/../patches/weko-delay-file-content-task.patch"
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

    # Update SWORD mapping for item type 30002
    echo "=== Updating SWORD Mapping 30002 ==="
    mapping_json=$(cat "${SCRIPT_DIR}/../patches/sword_mapping_30002.json")
    docker compose -f "${compose_file}" exec -T web invenio shell -c "
from weko_records.api import JsonldMapping
import json
mapping = json.loads('''${mapping_json}''')
obj = JsonldMapping.get_mapping_by_id(30002)
obj.mapping = mapping
from invenio_db import db
db.session.commit()
print('Updated mapping 30002')
"

    # Grant contributor access to Sample Index
    echo "=== Granting Contributor Access to Sample Index ==="
    docker compose -f "${compose_file}" exec -T web invenio shell -c '
from weko_index_tree.models import Index
from weko_index_tree.utils import delete_index_trees_from_redis
from invenio_db import db
index = Index.query.filter_by(index_name_english="Sample Index").first()
if not index:
    raise Exception("Sample Index not found")
print(f"Before: contribute_role={index.contribute_role}, browsing_role={index.browsing_role}, public_state={index.public_state}")
index.contribute_role = "1,2,3,4,-98,-99"
index.browsing_role = "1,2,3,4,-98,-99"
index.public_state = True
db.session.commit()
# Clear Redis cache so API returns fresh data
for lang in ["en", "ja"]:
    delete_index_trees_from_redis(lang)
print(f"After: contribute_role={index.contribute_role}, browsing_role={index.browsing_role}, public_state={index.public_state}")
'

    # Grant index-tree-access permission to Contributor role
    echo "=== Granting index-tree-access to Contributor ==="
    docker compose -f "${compose_file}" exec -T web invenio shell -c '
from invenio_access.models import ActionRoles, Role
from invenio_db import db
role = Role.query.filter_by(name="Contributor").first()
if not role:
    raise Exception("Contributor role not found")
existing = ActionRoles.query.filter_by(action="index-tree-access", role_id=role.id).first()
if existing:
    print(f"index-tree-access already granted to Contributor (role_id={role.id})")
else:
    ar = ActionRoles(action="index-tree-access", role_id=role.id)
    db.session.add(ar)
    db.session.commit()
    print(f"Granted index-tree-access to Contributor (role_id={role.id})")
'

    # Validate SWORD mapping 30002
    echo "=== SWORD Mapping Validation (30002) ==="
    validation_result=$(docker compose -f "${compose_file}" exec -T web invenio shell -c '
from weko_records.api import JsonldMapping
from weko_search_ui.mapper import JsonLdMapper
import json
obj = JsonldMapping.get_mapping_by_id(30002)
errs = JsonLdMapper(obj.item_type_id, obj.mapping).validate()
result = {"mapping_id": obj.id, "item_type_id": obj.item_type_id, "name": obj.name, "valid": errs is None, "errors": errs or []}
print(json.dumps({"result": result, "invalid": 0 if errs is None else 1}, ensure_ascii=False))
')
    echo "${validation_result}"
    invalid_count=$(echo "${validation_result}" | python3 -c "import sys, json; print(json.load(sys.stdin)['invalid'])")
    if [[ "${invalid_count}" -gt 0 ]]; then
      echo "SWORD mapping validation failed: ${invalid_count} invalid mapping(s)" >&2
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
