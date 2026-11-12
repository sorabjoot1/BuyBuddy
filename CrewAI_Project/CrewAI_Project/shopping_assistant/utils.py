"""Input parsing / formatting helpers (pure functions, easy to unit-test)."""
from __future__ import annotations

import re
from typing import Optional

from .schemas import USE_CASES

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}
_CURRENCY_CODE = re.compile(r"\b(USD|EUR|GBP|PKR|INR|AED|CAD|AUD)\b", re.I)


def parse_budget(text: str, default_currency: str = "USD") -> Optional[tuple[float, str]]:
    """Parse '1200', '$1,200', 'PKR 250k', '1.5k usd' -> (amount, currency). None if invalid."""
    if not text:
        return None
    raw = text.strip()
    currency = default_currency.upper()
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in raw:
            currency = code
    m = _CURRENCY_CODE.search(raw)
    if m:
        currency = m.group(1).upper()
    num = re.search(r"(\d[\d,]*\.?\d*)\s*([kK])?", raw)
    if not num:
        return None
    try:
        amount = float(num.group(1).replace(",", ""))
    except ValueError:
        return None
    if num.group(2):
        amount *= 1000
    if amount <= 0:
        return None
    return amount, currency


def parse_use_case(text: str) -> Optional[str]:
    """Accept '1'-'4' or a (partial) name and return a canonical use case."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t.isdigit() and 1 <= int(t) <= len(USE_CASES):
        return USE_CASES[int(t) - 1]
    aliases = {
        "game": "gaming", "games": "gaming", "gaming": "gaming",
        "code": "programming", "coding": "programming", "programming": "programming",
        "dev": "programming", "development": "programming",
        "office": "office work", "office work": "office work", "work": "office work",
        "university": "university studies", "uni": "university studies", "study": "university studies",
        "studies": "university studies", "student": "university studies", "school": "university studies",
        "university studies": "university studies",
    }
    if t in aliases:
        return aliases[t]
    for key, val in aliases.items():
        if key in t:
            return val
    return None


def parse_yes_no(text: str) -> Optional[bool]:
    t = (text or "").strip().lower()
    if t in {"y", "yes", "yeah", "yep", "sure", "ok", "okay", "1"}:
        return True
    if t in {"n", "no", "nope", "nah", "done", "0"}:
        return False
    return None


def money(value: Optional[float], currency: str = "USD") -> str:
    return "N/A" if value is None else f"{currency} {value:,.0f}"


def storage_label(gb: Optional[int]) -> str:
    if gb is None:
        return "N/A"
    return f"{gb / 1000:g} TB" if gb >= 1000 else f"{gb} GB"
