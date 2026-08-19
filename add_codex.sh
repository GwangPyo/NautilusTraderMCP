#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON="$(conda info --base)/envs/mcp/bin/python3"
codex mcp add nautilus-trader -- "${PYTHON}" "$(pwd)/mcp_server.py"
