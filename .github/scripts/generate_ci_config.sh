#!/bin/bash
set -xeuo pipefail

if [[ $# -lt 2 ]]; then
  cat >&2 <<'USAGE'
Usage: generate_ci_config.sh <output_path> <base_config_yaml> [--minio] [--jupyterhub]
USAGE
  exit 1
fi

OUTPUT=$1
BASE_CONFIG=$2
shift 2
MINIO=false
JUPYTERHUB=false

for arg in "$@"; do
  case "$arg" in
    --minio)
      MINIO=true
      ;;
    --jupyterhub)
      JUPYTERHUB=true
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

cat "${OUTPUT}"
