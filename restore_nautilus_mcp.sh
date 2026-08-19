#!/usr/bin/env bash
# Recreates the "mcp" conda env after ~/miniconda3/{bin,envs} got wiped.
# nautilus_trader/, docs/, and rags/{config.json,corpus_embeddings.npy,shape.json}
# are still on disk -- only the conda env itself was lost -- so this just
# recreates the env and reinstalls deps (install.sh would also work, but
# would re-run the rust-analyzer check and prompt for the doc index it
# doesn't need to).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"

conda env list | grep -q "^mcp " || conda create -n mcp python=3.12 -y
conda activate mcp

pip install -e .

echo "mcp env restored."
