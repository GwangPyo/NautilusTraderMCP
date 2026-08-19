#!/usr/bin/env bash
# Sets up everything mcp_server.py needs: conda env + deps, nautilus_trader source
# clone (docs + Rust crates, not pip-installed), the code index, and the doc RAG index.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

REPO_URL="https://github.com/nautechsystems/nautilus_trader.git"
ENV_NAME="${ENV_NAME:-mcp}"

# 1. conda env with the right Python
CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda env list | grep -q "^${ENV_NAME} " || conda create -n "${ENV_NAME}" python=3.12 -y
conda activate "${ENV_NAME}"

# 2. python deps (mcp, dspy, python-dotenv, python-lsp-server)
pip install -e .

# 3. nautilus_trader source (Rust crates + docs; not pip-installed, index.py/rag_build.py
#    read it directly as text)
[ -d nautilus_trader ] || git clone --depth 1 "${REPO_URL}" nautilus_trader

# 4. docs -> ragged_docs (rag_build.py chunks/embeds everything under ragged_docs/)
[ -d ragged_docs ] || cp -r nautilus_trader/docs ragged_docs

# 5. Rust LSP (rust-analyzer) -- python-lsp-server (pylsp) already came from step 2
if ! command -v rust-analyzer >/dev/null 2>&1; then
    if command -v rustup >/dev/null 2>&1; then
        rustup component add rust-analyzer
    else
        echo "WARNING: rust-analyzer not found and rustup isn't installed either." >&2
        echo "         Install it manually (https://rust-analyzer.github.io/manual.html#installation)" >&2
        echo "         -- Rust symbols in index.py won't work until it's on PATH." >&2
    fi
fi

# 6. code index (Python via pylsp, Rust via rust-analyzer) -> .code_index_cache.json
python3 -c "from index import CodeIndex; n = len(CodeIndex()._build_index()); print(f'code index: {n} symbols')"

# 7. doc RAG index -- calls the Gemini embedding API once, so skip if already built
if [ ! -f rags/config.json ]; then
    python3 rags/rag_build.py
fi

echo "Setup complete. Register the server with: ./add_claude.sh and/or ./add_codex.sh"
