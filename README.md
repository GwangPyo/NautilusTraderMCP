# nautilus-trader MCP server

## What this is

An MCP (Model Context Protocol) server that gives an LLM (Claude Code, Codex CLI,
etc.) two ways to look things up in [nautilus_trader](https://github.com/nautechsystems/nautilus_trader)
while writing strategy code against it:

- **Code search** (`index.py`) -- structural search over the actual source
  (Python + Rust), by symbol name. Not fuzzy-text/embedding search: it finds the
  real class/function/struct and returns its docstring or full source.
- **Doc search** (`rags/`) -- semantic (embedding-based) search over the
  project's markdown docs (concepts, guides, tutorials), for "how do I..."
  questions that don't map to a single symbol name.

## How it works

- `index.py` spawns two real language servers as subprocesses and talks LSP
  (JSON-RPC over stdio) to them directly -- `pylsp` for the Python source under
  `nautilus_trader/python/nautilus_trader`, `rust-analyzer` for the Rust source
  under `nautilus_trader/crates`. `documentSymbol` finds top-level
  classes/functions/structs/impls; `hover` gets the docstring (Python only --
  see Known limitations). Results are cached to `.code_index_cache.json` since
  building it costs ~25s (mostly rust-analyzer over ~2600 files).
- `rags/rag_build.py` chunks every file under `docs/` and builds a
  `dspy.retrievers.Embeddings` index (Gemini embeddings), saved to `rags/`
  (`config.json` + `corpus_embeddings.npy`) plus a `shape.json` that records the
  original folder structure so `rags/search.py` can filter to a subfolder.
- `mcp_server.py` wires both into 5 MCP tools: `search_code`, `get_code_doc`,
  `get_code_source`, `search_docs`, `show_doc_keys`.

## Setup

```sh
git clone https://github.com/GwangPyo/NautilusTraderMCP.git
cd NautilusTraderMCP
cp .env.example .env   # fill in GEMINI_API_KEY (and OPENAI/ANTHROPIC if you use load_model)
./install.sh           # conda env "mcp" + deps, nautilus_trader clone, code index, doc index
```

`install.sh` is idempotent: re-running it skips the nautilus_trader clone, the
`docs/` copy, and the (paid) doc-embedding build if they already exist. Set
`ENV_NAME=<name>` to use a different conda env name (used for testing so it
doesn't touch the real `mcp` env).

An env manager isn't required -- `uv venv && uv pip install -e .` works too;
`install.sh` just standardizes on conda for a reproducible one-command setup.

## Register with a client

```sh
./add_claude.sh   # claude mcp add
./add_codex.sh    # codex mcp add
```

Both just point the client at `<conda mcp env>/bin/python3 mcp_server.py` over stdio.

## Known limitations / TODO

- [ ] `.code_index_cache.json` and `rags/{config.json,corpus_embeddings.npy,shape.json}`
      have no invalidation -- if `nautilus_trader/` or `docs/` change, you have
      to delete the cache files by hand and re-run to pick it up.
- [ ] No automated tests -- everything so far has been verified by hand
      (fresh conda env, fresh uv env, real MCP client over stdio).
- [ ] `nautilus_trader/` is cloned from `main` (unpinned) -- can drift over
      time; nothing currently checks it against a known-good commit/tag.
