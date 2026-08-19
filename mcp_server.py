from mcp.server.mcpserver import MCPServer

from index import CodeIndex
from rags.search import RAGSearch

mcp = MCPServer("nautilus-trader")

code_index = CodeIndex()
rag_search = RAGSearch()


@mcp.tool()
def search_code(query: str, limit: int = 20) -> list[str]:
    """Search nautilus_trader source (Python + Rust) by symbol name.

    Returns keys in the form "lang:relative/path::Name" (e.g.
    "rust:trading/src/strategy/mod.rs::Strategy"). Pass a returned key, or just
    the bare name, to get_code_doc/get_code_source.
    """
    return code_index.search(query, limit=limit)


@mcp.tool()
def get_code_doc(key: str) -> str:
    """Get the docstring for a symbol found via search_code."""
    return code_index.get_doc(key)


@mcp.tool()
def get_code_source(key: str) -> str:
    """Get the full source (function/class/struct/impl/etc.) for a symbol found via search_code."""
    return code_index.get_source(key)


@mcp.tool()
def search_docs(search_keywords: str, keys: list[str] | None = None, top_k: int = 20):
    """Semantic search over the nautilus_trader documentation (concepts, guides, tutorials).

    Call show_doc_keys() first to see the folder/file structure if you want to
    narrow the search with `keys`.
    """
    return rag_search(search_keywords, keys=keys, top_k=top_k)


@mcp.tool()
def show_doc_keys() -> dict:
    """Show the nested folder/file structure of the indexed documentation, for use as `keys` in search_docs."""
    return rag_search.show_keys()


if __name__ == '__main__':
    mcp.run()
