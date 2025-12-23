#!/bin/bash
set -xeuo pipefail

if [[ $# -lt 2 ]]; then
  cat >&2 <<'USAGE'
Usage: generate_ci_config.sh <output_path> <base_config_yaml> [--minio] [--jupyterhub] [--weko] [--flowable]
USAGE
  exit 1
fi

OUTPUT=$1
BASE_CONFIG=$2
shift 2
MINIO=false
JUPYTERHUB=false
WEKO=false
FLOWABLE=false

for arg in "$@"; do
  case "$arg" in
    --minio)
      MINIO=true
      ;;
    --jupyterhub)
      JUPYTERHUB=true
      ;;
    --weko)
      WEKO=true
      ;;
    --flowable)
      FLOWABLE=true
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      exit 1
      ;;
  esac

done

cp "${BASE_CONFIG}" "${OUTPUT}"

if [[ "${MINIO}" == "true" ]]; then
  if [[ -z "${S3COMPAT_ACCESS_KEY_1:-}" || -z "${S3COMPAT_SECRET_KEY_1:-}" ]]; then
    echo "S3 compat credentials are not set" >&2
    exit 1
  fi

  cat >> "${OUTPUT}" <<EOF

storages_s3:
  - id: 's3compat'
    name: 'S3 Compatible Storage'
    skip_too_many_files_check: true

s3compat_access_key_1: '${S3COMPAT_ACCESS_KEY_1}'
s3compat_secret_access_key_1: '${S3COMPAT_SECRET_KEY_1}'
s3compat_default_region_1: '${S3COMPAT_REGION}'
s3compat_test_bucket_name_1: '${S3COMPAT_BUCKET_NAME_1}'

s3compat_access_key_2: '${S3COMPAT_ACCESS_KEY_2}'
s3compat_secret_access_key_2: '${S3COMPAT_SECRET_KEY_2}'
s3compat_default_region_2: '${S3COMPAT_REGION}'
s3compat_test_bucket_name_2: '${S3COMPAT_BUCKET_NAME_2}'

s3compat_type_name_1: '${S3COMPAT_SERVICE_NAME}'
s3compat_type_name_2: '${S3COMPAT_SERVICE_NAME}'
EOF
else
  cat >> "${OUTPUT}" <<'EOF'

storages_s3: []
EOF
fi

if [[ "${JUPYTERHUB}" == "true" ]]; then
  if [[ -z "${TLJH_URL:-}" || -z "${TLJH_USERNAME:-}" || -z "${TLJH_PASSWORD:-}" ]]; then
    echo "TLJH connection information is not set" >&2
    exit 1
  fi

  cat >> "${OUTPUT}" <<EOF

jupyterhub_enabled: true
tljh_url: '${TLJH_URL}'
tljh_username: '${TLJH_USERNAME}'
tljh_password: '${TLJH_PASSWORD}'
EOF
else
  cat >> "${OUTPUT}" <<'EOF'

jupyterhub_enabled: false
EOF
fi

if [[ "${WEKO}" == "true" ]]; then
  WEKO_URL_VALUE=${WEKO_URL:-http://localhost}
  WEKO_ADMIN_EMAIL_VALUE=${WEKO_ADMIN_EMAIL:-}
  WEKO_ADMIN_PASSWORD_VALUE=${WEKO_ADMIN_PASSWORD:-}
  WEKO_USER_EMAIL_VALUE=${WEKO_USER_EMAIL:-}
  WEKO_USER_PASSWORD_VALUE=${WEKO_USER_PASSWORD:-}
  WEKO_INSTITUTION_NAME_VALUE=${WEKO_INSTITUTION_NAME:-}
  WEKO_INDEX_NAME_VALUE=${WEKO_INDEX_NAME:-'Sample Index'}
  WEKO_DOCKER_COMPOSE_PATH_VALUE=${WEKO_DOCKER_COMPOSE_PATH:-}
  SWORD_MAPPING_ID_VALUE=${SWORD_MAPPING_ID:-30002}
  IGNORE_HTTPS_ERRORS_VALUE=${IGNORE_HTTPS_ERRORS:-false}

  cat >> "${OUTPUT}" <<EOF

# WEKO / JAIRO Cloud settings
weko_url: '${WEKO_URL_VALUE}'
weko_admin_email: '${WEKO_ADMIN_EMAIL_VALUE}'
weko_admin_password: '${WEKO_ADMIN_PASSWORD_VALUE}'
weko_user_email: '${WEKO_USER_EMAIL_VALUE}'
weko_user_password: '${WEKO_USER_PASSWORD_VALUE}'
weko_institution_name: '${WEKO_INSTITUTION_NAME_VALUE}'
weko_index_name: '${WEKO_INDEX_NAME_VALUE}'
weko_docker_compose_path: '${WEKO_DOCKER_COMPOSE_PATH_VALUE}'
sword_mapping_id: ${SWORD_MAPPING_ID_VALUE}
ignore_https_errors: ${IGNORE_HTTPS_ERRORS_VALUE}
EOF
fi

if [[ "${FLOWABLE}" == "true" ]]; then
  GATEWAY_BASE_URL_VALUE=${GATEWAY_BASE_URL:-http://192.168.168.167:8088/}
  WORKFLOW_BATCH_PROJECT_COUNT_VALUE=${WORKFLOW_BATCH_PROJECT_COUNT:-50}

  cat >> "${OUTPUT}" <<EOF

# Flowable Workflow settings
workflow_enabled: true
gateway_base_url: '${GATEWAY_BASE_URL_VALUE}'
workflow_batch_project_count: ${WORKFLOW_BATCH_PROJECT_COUNT_VALUE}
EOF
else
  cat >> "${OUTPUT}" <<'EOF'

workflow_enabled: false
EOF
fi

cat "${OUTPUT}"
