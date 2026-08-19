#!/usr/bin/env bash
# Removes a conda env created by install.sh (e.g. for tearing down a test env).
set -euo pipefail

ENV_NAME="${1:?usage: clean_conda.sh <env_name>}"

CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda deactivate 2>/dev/null || true
conda env remove -n "${ENV_NAME}" -y
