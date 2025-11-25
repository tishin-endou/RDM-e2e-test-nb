# shellcheck shell=bash

wait_for_service() {
    local service_name="${SERVICE_NAME}"
    local check_command="${CHECK_COMMAND}"
    local timeout="${TIMEOUT:-300}"
    local interval="${INTERVAL:-10}"

    echo "Waiting for $service_name to be ready (timeout: ${timeout}s)..."
    echo "Using check command: ${check_command}"
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if eval "$check_command"; then
            echo "$service_name is ready!"
            return 0
        fi
        local exit_code=$?
        echo "Waiting for $service_name... (${elapsed}s elapsed) [exit code: ${exit_code}]"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo "Timeout waiting for $service_name"
    return 1
}
