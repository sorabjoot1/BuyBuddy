"""Product comparison tool: RAM, processor, storage and price, plus a use-case score."""
from __future__ import annotations

import re
from typing import Iterable

from ..schemas import Laptop
from ..utils import money, storage_label
from .calculator import discount_info

# Weights per use case (sum to 1.0): how much each attribute matters.
WEIGHTS: dict[str, dict[str, float]] = {
    "gaming":              {"cpu": 0.20, "gpu": 0.35, "ram": 0.15, "storage": 0.10, "value": 0.20},
    "programming":         {"cpu": 0.30, "gpu": 0.05, "ram": 0.25, "storage": 0.15, "value": 0.25},
    "office work":         {"cpu": 0.20, "gpu": 0.00, "ram": 0.20, "storage": 0.15, "value": 0.45},
    "university studies":  {"cpu": 0.20, "gpu": 0.00, "ram": 0.20, "storage": 0.15, "value": 0.45},
}


def processor_score(cpu: str) -> float:
    """Heuristic 0-10 score from a CPU name (tier + generation hints)."""
    s = (cpu or "").lower()
    score = 0.0
    if m := re.search(r"\bm([1-9])\b\s*(pro|max|ultra)?", s):
        score = 6 + int(m.group(1)) * 0.5
        score += {"pro": 1.0, "max": 1.8, "ultra": 2.5}.get(m.group(2) or "", 0)
    elif m := re.search(r"ultra\s*([3579])", s):
        score = {"3": 4, "5": 6, "7": 7.5, "9": 9}[m.group(1)]
    elif m := re.search(r"\bi([3579])[- ]", s) or re.search(r"core\s*i([3579])", s):
        score = {"3": 3.5, "5": 5.5, "7": 7.0, "9": 8.5}[m.group(1)]
        if g := re.search(r"i[3579][- ]?(\d{2})\d{2,3}", s):
            score += (int(g.group(1)) - 10) * 0.2
        elif g := re.search(r"i[3579][- ]?(\d)\d{3}", s):
            score += (int(g.group(1)) - 8) * 0.2
    elif m := re.search(r"ryzen\s*([3579])", s):
        score = {"3": 3.5, "5": 5.5, "7": 7.0, "9": 8.5}[m.group(1)]
        if g := re.search(r"ryzen\s*[3579]\s*(\d)\d{3}", s):
            score += (int(g.group(1)) - 5) * 0.25
        if re.search(r"\d{4}\w*(hx|hs|h)\b", s):
            score += 0.5
    elif "snapdragon x" in s:
        score = 6.5
    elif any(k in s for k in ("celeron", "pentium", "athlon")):
        score = 2.0
    elif s and s != "unknown":
        score = 4.0
    return max(0.0, min(10.0, score))


def gpu_score(gpu: str) -> float:
    s = (gpu or "").lower()
    if m := re.search(r"rtx\s*([2-5])0(\d)0", s):
        base = {"2": 5.0, "3": 6.0, "4": 7.0, "5": 8.0}[m.group(1)]
        return min(10.0, base + (int(m.group(2)) - 5) * 0.6 + 0.4)
    if "rtx" in s or "radeon rx" in s:
        return 6.5
    if "gtx" in s:
        return 5.0
    if any(k in s for k in ("mx", "arc")):
        return 3.0
    return 1.0  # integrated / unknown


def _norm(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(10.0, (value - low) / (high - low) * 10))


def compare_laptops(laptops: Iterable[Laptop], use_case: str, budget: float, currency: str = "USD") -> dict:
    """Compare laptops on RAM, processor, storage and price; rank them for the use case.

    Returns {"rows": [...], "best": {...per-attribute winners...}, "ranking": [...names...]}.
    """
    items = [l for l in laptops if l.price]
    if not items:
        return {"rows": [], "best": {}, "ranking": []}
    w = WEIGHTS.get(use_case, WEIGHTS["office work"])
    prices = [l.price for l in items]
    lo, hi = min(prices), max(prices)

    rows = []
    for l in items:
        disc = discount_info(l.original_price, l.price)
        cpu, gpu = processor_score(l.processor), gpu_score(l.gpu)
        ram, sto = _norm(l.ram_gb, 4, 32), _norm(l.storage_gb, 128, 2000)
        # Value: cheaper (within the set) is better; staying under budget is rewarded.
        value = 10.0 if hi == lo else (hi - l.price) / (hi - lo) * 10
        if l.price > budget:
            value *= 0.3
        score = w["cpu"] * cpu + w["gpu"] * gpu + w["ram"] * ram + w["storage"] * sto + w["value"] * value
        rows.append({
            "name": l.name, "price": l.price, "price_text": money(l.price, currency),
            "original_price": l.original_price, "discount_pct": disc["discount_pct"],
            "savings": disc["savings"], "processor": l.processor, "cpu_score": round(cpu, 1),
            "ram_gb": l.ram_gb, "storage_gb": l.storage_gb, "storage_text": storage_label(l.storage_gb),
            "gpu": l.gpu, "source_url": l.source_url,
            "within_budget": l.price <= budget, "score": round(score, 2),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)

    best = {
        "cheapest": min(rows, key=lambda r: r["price"])["name"],
        "most_ram": max(rows, key=lambda r: r["ram_gb"] or 0)["name"],
        "most_storage": max(rows, key=lambda r: r["storage_gb"] or 0)["name"],
        "fastest_processor": max(rows, key=lambda r: r["cpu_score"])["name"],
    }
    return {"rows": rows, "best": best, "ranking": [r["name"] for r in rows]}


def comparison_table(result: dict, currency: str = "USD") -> str:
    """Markdown table of a compare_laptops() result."""
    lines = [
        "| # | Laptop | Price | Discount | Processor | RAM | Storage | GPU | Score |",
        "|---|--------|-------|----------|-----------|-----|---------|-----|-------|",
    ]
    for i, r in enumerate(result["rows"], 1):
        disc = f"-{r['discount_pct']}% (save {money(r['savings'], currency)})" if r["discount_pct"] else "-"
        ram = f"{r['ram_gb']} GB" if r["ram_gb"] else "N/A"
        lines.append(
            f"| {i} | {r['name']} | {r['price_text']} | {disc} | {r['processor']} | {ram} | "
            f"{r['storage_text']} | {r['gpu']} | {r['score']} |"
        )
    return "\n".join(lines)
