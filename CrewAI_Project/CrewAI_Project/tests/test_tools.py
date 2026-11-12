import pytest

from shopping_assistant.schemas import Laptop
from shopping_assistant.tools import calculate, compare_laptops, discount_info
from shopping_assistant.tools.comparison import processor_score
from shopping_assistant.utils import parse_budget, parse_use_case, parse_yes_no


def test_calculator():
    assert calculate("(1200 - 999) / 1200 * 100") == pytest.approx(16.75)
    assert calculate("1,000 * 2") == 2000
    with pytest.raises(ValueError):
        calculate("__import__('os').system('x')")


def test_discount():
    assert discount_info(1200, 900) == {"savings": 300.0, "discount_pct": 25.0}
    assert discount_info(None, 900)["discount_pct"] == 0


def test_parsers():
    assert parse_budget("$1,200") == (1200, "USD")
    assert parse_budget("PKR 250k") == (250000, "PKR")
    assert parse_budget("abc") is None
    assert parse_use_case("2") == "programming"
    assert parse_use_case("I want to play games") == "gaming"
    assert parse_yes_no("Yes") is True and parse_yes_no("no") is False and parse_yes_no("maybe") is None


def test_processor_ordering():
    assert processor_score("Intel Core i7-13700H") > processor_score("Intel Core i5-1235U")
    assert processor_score("Apple M3 Pro") > processor_score("Apple M1")


def test_compare_ranks_by_use_case():
    lap = [
        Laptop(name="Gamer", price=1100, processor="Ryzen 7 7840HS", ram_gb=16, storage_gb=1000, gpu="RTX 4060"),
        Laptop(name="Office", price=700, processor="Intel Core i5-1335U", ram_gb=8, storage_gb=256),
        Laptop(name="Mid", price=900, processor="Intel Core i7-1360P", ram_gb=16, storage_gb=512, original_price=1000),
    ]
    g = compare_laptops(lap, "gaming", 1200)
    assert g["ranking"][0] == "Gamer"
    assert g["best"]["cheapest"] == "Office"
    assert next(r for r in g["rows"] if r["name"] == "Mid")["discount_pct"] == 10.0
