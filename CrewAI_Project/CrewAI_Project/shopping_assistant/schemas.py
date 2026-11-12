"""Pydantic data models shared across the project."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

UseCase = Literal["gaming", "programming", "office work", "university studies"]
USE_CASES: tuple[str, ...] = ("gaming", "programming", "office work", "university studies")


class Requirements(BaseModel):
    budget: float = Field(gt=0, description="Maximum budget")
    currency: str = "USD"
    use_case: str
    notes: str = ""


class Laptop(BaseModel):
    """A laptop extracted from web search results."""

    name: str = Field(description="Brand and model name")
    price: Optional[float] = Field(None, description="Current price as a number (no symbols)")
    original_price: Optional[float] = Field(None, description="List/original price if discounted")
    processor: str = Field("Unknown", description="CPU model, e.g. 'Intel Core i7-13700H'")
    ram_gb: Optional[int] = Field(None, description="RAM in GB")
    storage_gb: Optional[int] = Field(None, description="Storage capacity in GB (1TB = 1000)")
    gpu: str = Field("Integrated", description="Graphics card")
    source_url: str = ""


class LaptopList(BaseModel):
    laptops: list[Laptop] = Field(default_factory=list)
