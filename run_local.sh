#!/usr/bin/env bash
# Run the Streamlit app locally on port 8050
set -euo pipefail

PORT=${1:-8050}

echo "Starting Streamlit app on port $PORT..."

streamlit run main.py --server.port "$PORT" --server.headless true
