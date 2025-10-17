#!/usr/bin/env bash
#
# Auto-restart wrapper for facefusion.py
# Usage: ./run_with_restart.sh [facefusion_args...]
# Example: ./run_with_restart.sh run --open-browser
#

set -euo pipefail

# Configuration
MAX_RETRIES=0           # 0 = unlimited retries, set to number for max attempts
RETRY_DELAY=5           # seconds to wait before restarting
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/facefusion_$(date +%Y%m%d_%H%M%S).log"
PYTHON_CMD="python"
SCRIPT_PATH="facefusion.py"

# Create log directory
mkdir -p "${LOG_DIR}"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Function to cleanup on exit
cleanup() {
    log "Shutdown signal received, stopping facefusion..."
    if [[ -n "${FACEFUSION_PID:-}" ]]; then
        kill -TERM "${FACEFUSION_PID}" 2>/dev/null || true
        wait "${FACEFUSION_PID}" 2>/dev/null || true
    fi
    exit 0
}

# Trap signals for graceful shutdown
trap cleanup SIGTERM SIGINT

# Main loop
ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    
    if [[ ${MAX_RETRIES} -gt 0 && ${ATTEMPT} -gt ${MAX_RETRIES} ]]; then
        log "ERROR: Maximum retry attempts (${MAX_RETRIES}) reached. Exiting."
        exit 1
    fi
    
    log "Starting facefusion (attempt ${ATTEMPT})..."
    log "Command: ${PYTHON_CMD} ${SCRIPT_PATH} $*"
    log "Log file: ${LOG_FILE}"
    
    # Run facefusion in foreground, capture output
    set +e
    ${PYTHON_CMD} ${SCRIPT_PATH} "$@" 2>&1 | tee -a "${LOG_FILE}" &
    FACEFUSION_PID=$!
    set -e
    
    # Wait for the process to exit
    wait ${FACEFUSION_PID}
    EXIT_CODE=$?
    
    if [[ ${EXIT_CODE} -eq 0 ]]; then
        log "Facefusion exited cleanly (exit code 0). Shutting down."
        exit 0
    else
        log "WARNING: Facefusion crashed with exit code ${EXIT_CODE}"
        log "Restarting in ${RETRY_DELAY} seconds..."
        sleep ${RETRY_DELAY}
    fi
done
