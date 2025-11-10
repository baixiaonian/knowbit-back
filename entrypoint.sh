#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 优先使用环境变量 APP_ENV，兼容通过命令行传入第一个参数
APP_ENV="${APP_ENV:-${1:-production}}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-2}"

# 激活虚拟环境（如果存在）
if [ -f "${SCRIPT_DIR}/bin/activate" ]; then
    # shellcheck disable=SC1090
    . "${SCRIPT_DIR}/bin/activate"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

start_dev() {
    log "启动开发环境（自动重载）..."
    exec uvicorn main:app \
        --host "${APP_HOST}" \
        --port "${APP_PORT}" \
        --reload
}

start_prod() {
    log "启动生产环境..."
    exec uvicorn main:app \
        --host "${APP_HOST}" \
        --port "${APP_PORT}" \
        --workers "${APP_WORKERS}"
}

case "${APP_ENV}" in
    dev|development)
        start_dev
        ;;
    prod|production|*)
        start_prod
        ;;
esac
