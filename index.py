import difflib
import json
import subprocess
import threading
from pathlib import Path

from pylsp_jsonrpc.endpoint import Endpoint
from pylsp_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter


# LSP SymbolKind values we care about (skip Variable/Constant/Field etc.)
_TOPLEVEL_KINDS = {
    2,   # Module
    5,   # Class
    10,  # Enum
    11,  # Interface (Rust trait)
    12,  # Function
    19,  # Object (rust-analyzer uses this for `impl` blocks)
    23,  # Struct
}


class _LspClient:
    """Talks raw LSP (JSON-RPC over stdio) to a language-server subprocess."""

    def __init__(self, cmd: list[str], root: Path, language_id: str):
        self.language_id = language_id
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        writer = JsonRpcStreamWriter(self.proc.stdin)
        reader = JsonRpcStreamReader(self.proc.stdout)
        self.endpoint = Endpoint(dispatcher={}, consumer=writer.write)
        threading.Thread(target=reader.listen, args=(self.endpoint.consume,), daemon=True).start()
        self.endpoint.request(
            "initialize", {"processId": None, "rootUri": root.resolve().as_uri(), "capabilities": {}}
        ).result(timeout=60)
        self.endpoint.notify("initialized", {})

    def document_symbols(self, path: Path, text: str) -> list[dict]:
        uri = path.resolve().as_uri()
        self.endpoint.notify(
            "textDocument/didOpen",
            {"textDocument": {"uri": uri, "languageId": self.language_id, "version": 1, "text": text}},
        )
        return self.endpoint.request(
            "textDocument/documentSymbol", {"textDocument": {"uri": uri}}
        ).result(timeout=30) or []

    def hover(self, path: Path, line: int, character: int) -> str:
        uri = path.resolve().as_uri()
        result = self.endpoint.request(
            "textDocument/hover",
            {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}},
        ).result(timeout=30)
        if not result:
            return ""
        contents = result.get("contents", "")
        return contents.get("value", "") if isinstance(contents, dict) else str(contents)

    def close(self) -> None:
        try:
            self.endpoint.request("shutdown").result(timeout=5)
            self.endpoint.notify("exit")
        finally:
            self.proc.terminate()


def _slice_range(text: str, rng: dict) -> str:
    lines = text.splitlines(keepends=True)
    start, end = rng["start"], rng["end"]
    if start["line"] == end["line"]:
        return lines[start["line"]][start["character"]:end["character"]]
    chunk = [lines[start["line"]][start["character"]:]]
    chunk += lines[start["line"] + 1:end["line"]]
    if end["line"] < len(lines):
        chunk.append(lines[end["line"]][:end["character"]])
    return "".join(chunk)


class CodeIndex:
    """Structural code index over nautilus_trader source: name -> (docstring, source).

    Both languages are indexed via a real language server spawned as a subprocess and
    driven over raw LSP/JSON-RPC (pylsp for Python, rust-analyzer for Rust), so
    names/docstrings/ranges come from actual symbol resolution rather than hand-rolled
    parsing. rust-analyzer runs without `cargo` here (not installed), so it only does
    single-file syntax analysis -- no cross-crate resolution -- but documentSymbol/hover
    for a file's own declarations works fine regardless.
    """

    PY_ROOT = Path(__file__).parent / "nautilus_trader" / "python" / "nautilus_trader"
    RS_ROOT = Path(__file__).parent / "nautilus_trader" / "crates"
    CACHE_PATH = Path(__file__).parent / ".code_index_cache.json"

    def __init__(self, py_root: str | Path | None = None, rs_root: str | Path | None = None):
        self.py_root = Path(py_root) if py_root else self.PY_ROOT
        self.rs_root = Path(rs_root) if rs_root else self.RS_ROOT
        self._index: dict[str, tuple[str, str]] | None = None  # "lang:path::name" -> (docstring, source)

    @staticmethod
    def _index_via_lsp(cmd: list[str], language_id: str, root: Path, glob: str) -> dict[str, tuple[str, str]]:
        index: dict[str, tuple[str, str]] = {}
        client = _LspClient(cmd, root, language_id)
        try:
            for path in root.rglob(glob):
                text = path.read_text(errors="ignore")
                for sym in client.document_symbols(path, text):
                    if sym.get("kind") not in _TOPLEVEL_KINDS:
                        continue
                    if sym.get("containerName"):  # top-level만 (메서드 등 중첩 심볼 제외)
                        continue
                    rng = sym["location"]["range"]
                    source = _slice_range(text, rng)
                    line_text = text.splitlines()[rng["start"]["line"]]
                    name_col = line_text.find(sym["name"], rng["start"]["character"])
                    hover_char = name_col if name_col != -1 else rng["start"]["character"]
                    doc = client.hover(path, rng["start"]["line"], hover_char)
                    key = f"{language_id}:{path.relative_to(root)}::{sym['name']}"
                    index[key] = (doc, source)
        finally:
            client.close()
        return index

    def _build_index(self) -> dict[str, tuple[str, str]]:
        if self._index is not None:
            return self._index
        if self.CACHE_PATH.exists():
            data = json.loads(self.CACHE_PATH.read_text())
            self._index = {k: tuple(v) for k, v in data.items()}
            return self._index
        self._index = {
            **self._index_via_lsp(["pylsp"], "python", self.py_root, "*.py"),
            **self._index_via_lsp(["rust-analyzer"], "rust", self.rs_root, "*.rs"),
        }
        self.CACHE_PATH.write_text(json.dumps(self._index))
        return self._index

    def search(self, query: str, limit: int = 20) -> list[str]:
        index = self._build_index()
        names = {k.split("::")[-1]: k for k in index}
        close = difflib.get_close_matches(query, names, n=limit, cutoff=0.3)
        return [names[n] for n in close]

    def _resolve(self, key: str) -> tuple[str, tuple[str, str]]:
        index = self._build_index()
        if key in index:
            return key, index[key]
        matches = [k for k in index if k.endswith("::" + key)]
        if len(matches) == 1:
            return matches[0], index[matches[0]]
        if matches:
            raise ValueError("multiple matches: " + ", ".join(sorted(matches)[:10]))
        raise ValueError(f"symbol '{key}' not found. call search() first.")

    def get_doc(self, key: str) -> str:
        try:
            _, (doc, _) = self._resolve(key)
        except ValueError as e:
            return str(e)
        return doc or "(no docstring)"

    def get_source(self, key: str) -> str:
        try:
            _, (_, source) = self._resolve(key)
        except ValueError as e:
            return str(e)
        return source


if __name__ == '__main__':
    idx = CodeIndex()
    print(idx.search("Strategy"))
