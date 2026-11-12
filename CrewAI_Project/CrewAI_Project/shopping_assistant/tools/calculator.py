"""Calculator tool: safe arithmetic, discount and price comparison helpers."""
from __future__ import annotations

import ast
import operator as op
from typing import Optional

_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
    ast.USub: op.neg, ast.UAdd: op.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and abs(_eval(node.right)) > 100:
            raise ValueError("Exponent too large")
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculate(expression: str) -> float:
    """Safely evaluate an arithmetic expression such as '(1200 - 999) / 1200 * 100'."""
    try:
        tree = ast.parse(expression.replace(",", "").replace("%", "/100"), mode="eval")
        return float(_eval(tree.body))
    except ZeroDivisionError as exc:
        raise ValueError("Division by zero") from exc
    except (SyntaxError, TypeError) as exc:
        raise ValueError(f"Invalid expression: {expression!r}") from exc


def discount_info(original_price: Optional[float], price: Optional[float]) -> dict:
    """Return savings and discount percentage between an original and a current price."""
    if not original_price or not price or original_price <= price:
        return {"savings": 0.0, "discount_pct": 0.0}
    savings = calculate(f"{original_price} - {price}")
    pct = calculate(f"({original_price} - {price}) / {original_price} * 100")
    return {"savings": round(savings, 2), "discount_pct": round(pct, 1)}


def price_difference(price_a: float, price_b: float) -> dict:
    """Absolute and percentage difference of price_a relative to price_b."""
    diff = calculate(f"{price_a} - {price_b}")
    pct = calculate(f"({price_a} - {price_b}) / {price_b} * 100") if price_b else 0.0
    return {"difference": round(diff, 2), "percent": round(pct, 1)}
