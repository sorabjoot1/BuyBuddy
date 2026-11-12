"""Web search tool (Tavily)."""
from __future__ import annotations

from ..config import require_env


def web_search(query: str, max_results: int = 8, depth: str = "basic") -> list[dict]:
    """Search the web and return a list of {title, url, content} dicts."""
    from tavily import TavilyClient  # imported lazily so tests don't need the key

    client = TavilyClient(api_key=require_env("TAVILY_API_KEY", "Tavily web search"))
    resp = client.search(query=query, max_results=max_results, search_depth=depth)
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in resp.get("results", [])
    ]


def format_results(results: list[dict], max_chars: int = 1500) -> str:
    """Render search results as plain text for an LLM prompt."""
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(f"[{i}] {r['title']}\nURL: {r['url']}\n{r['content'][:max_chars]}")
    return "\n\n".join(blocks)
