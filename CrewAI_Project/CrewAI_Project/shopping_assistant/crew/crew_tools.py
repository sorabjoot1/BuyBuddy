"""CrewAI tools (BaseTool subclasses) wrapping the plain-Python tools."""
from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config import Settings
from ..schemas import Laptop
from ..tools import (
    calculate,
    compare_laptops,
    comparison_table,
    discount_info,
    format_results,
    price_difference,
)
from ..tools import web_search as _web_search


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query, e.g. 'best gaming laptops under 1200 USD specs price'")


class WebSearchTool(BaseTool):
    name: str = "Web Search Tool"
    description: str = (
        "Search the web for laptops and their specifications (processor, RAM, storage, GPU, price). "
        "Returns titles, URLs and page excerpts."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        s = Settings.load()
        try:
            results = _web_search(query, max_results=s.max_search_results, depth=s.tavily_search_depth)
        except Exception as exc:
            return f"Search failed: {exc}"
        return format_results(results) or "No results found."


class CalculatorInput(BaseModel):
    expression: str = Field(default="", description="Arithmetic expression, e.g. '(1200 - 999) / 1200 * 100'")
    original_price: float | None = Field(default=None, description="Original price (for discount calc)")
    price: float | None = Field(default=None, description="Current price (for discount calc)")
    price_a: float | None = Field(default=None, description="Price A (for price comparison)")
    price_b: float | None = Field(default=None, description="Price B (for price comparison)")


class CalculatorTool(BaseTool):
    name: str = "Calculator Tool"
    description: str = (
        "Do math for shopping: (1) pass `expression` for arithmetic; (2) pass `original_price` and "
        "`price` to get savings and discount percentage; (3) pass `price_a` and `price_b` to compare "
        "two prices (difference and percent)."
    )
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str = "", original_price: float | None = None, price: float | None = None,
             price_a: float | None = None, price_b: float | None = None) -> str:
        try:
            if original_price is not None and price is not None:
                return json.dumps(discount_info(original_price, price))
            if price_a is not None and price_b is not None:
                return json.dumps(price_difference(price_a, price_b))
            if expression:
                return str(calculate(expression))
            return "Provide an expression, or original_price+price, or price_a+price_b."
        except ValueError as exc:
            return f"Calculation error: {exc}"


class ComparisonInput(BaseModel):
    laptops: list[Laptop] = Field(description="Laptops to compare (name, price, processor, ram_gb, storage_gb, ...)")
    use_case: str = Field(description="gaming | programming | office work | university studies")
    budget: float = Field(description="User's maximum budget")
    currency: str = Field(default="USD")


class ProductComparisonTool(BaseTool):
    name: str = "Product Comparison Tool"
    description: str = (
        "Compare laptops on RAM, processor, storage and price (with discounts) and rank them for the "
        "user's use case. Returns a Markdown table, the per-attribute winners and the ranking."
    )
    args_schema: Type[BaseModel] = ComparisonInput

    def _run(self, laptops: list, use_case: str, budget: float, currency: str = "USD") -> str:
        items = [l if isinstance(l, Laptop) else Laptop(**l) for l in laptops]
        result = compare_laptops(items, use_case, budget, currency)
        if not result["rows"]:
            return "No comparable laptops (a price is required for each)."
        return (
            comparison_table(result, currency)
            + "\n\nBest per attribute: " + json.dumps(result["best"])
            + "\nRanking for this use case (best first): " + " > ".join(result["ranking"])
        )
