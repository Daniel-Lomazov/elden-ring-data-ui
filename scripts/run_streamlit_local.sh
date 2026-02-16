#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8501}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[run_streamlit_local] Starting Streamlit (local-only defaults from .streamlit/config.toml)..."
echo "LOCAL_URL=http://localhost:${PORT}"
echo "Press Ctrl+C in this terminal to stop Streamlit."
echo "If process persists, run: ./scripts/stop_streamlit_port.sh ${PORT}"

python -m streamlit run app.py --server.port "$PORT"
