#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8501}"

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:"${PORT}" || true)"
elif command -v ss >/dev/null 2>&1; then
  PIDS="$(ss -ltnp "sport = :${PORT}" 2>/dev/null | awk -F'pid=' '/pid=/{print $2}' | awk -F',' '{print $1}' | sort -u)"
else
  echo "[stop_streamlit_port] Neither lsof nor ss is available to inspect port ${PORT}."
  exit 1
fi

if [[ -z "${PIDS}" ]]; then
  echo "[stop_streamlit_port] No process is listening on port ${PORT}."
  exit 0
fi

echo "[stop_streamlit_port] Stopping process(es) on port ${PORT}: ${PIDS}"
for pid in ${PIDS}; do
  kill -9 "${pid}" || true
done

echo "[stop_streamlit_port] Done."
