import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import get_logger


logger = get_logger()
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
PRICE_HISTORY_FILE = DATA_DIR / "price_history.json"


@dataclass
class Product:
    """Represents a product to track."""
    id: str
    name: str
    url: str
    enabled: bool = True
    notes: str = ""

    def __post_init__(self):
        """Validate product data."""
        if not self.id:
            raise ValueError("Product ID cannot be empty")
        if not self.url or not self.url.startswith("https://www.amazon.com.au/"):
            raise ValueError(f"Invalid Amazon AU URL for product {self.id}: {self.url}")


@dataclass
class PriceRecord:
    """Represents a single price data point."""
    timestamp: str
    price: float
    currency: str
    available: bool
    screenshot: str

    @classmethod
    def from_dict(cls, data: dict) -> 'PriceRecord':
        """Create PriceRecord from dictionary."""
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "price": self.price,
            "currency": self.currency,
            "available": self.available,
            "screenshot": self.screenshot
        }


@dataclass
class ProductHistory:
    """Represents complete price history for a product."""
    name: str
    url: str
    price_history: List[PriceRecord]
    all_time_low: Optional[Dict[str, Any]]
    last_checked: str

    @classmethod
    def from_dict(cls, data: dict) -> 'ProductHistory':
        """Create ProductHistory from dictionary."""
        price_history = [PriceRecord.from_dict(record) for record in data.get("price_history", [])]
        return cls(
            name=data["name"],
            url=data["url"],
            price_history=price_history,
            all_time_low=data.get("all_time_low"),
            last_checked=data.get("last_checked", "")
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "price_history": [record.to_dict() for record in self.price_history],
            "all_time_low": self.all_time_low,
            "last_checked": self.last_checked
        }


def load_products() -> List[Product]:
    """Load products from products.json."""
    if not PRODUCTS_FILE.exists():
        raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")

    with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = []
    for product_data in data.get("products", []):
        try:
            product = Product(**product_data)
            products.append(product)
        except (TypeError, ValueError) as e:
            logger.warning(f"Skipping invalid product: {e}")
            continue

    return products


def load_price_history() -> Dict[str, ProductHistory]:
    """Load price history from price_history.json."""
    if not PRICE_HISTORY_FILE.exists():
        return {}

    with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    history = {}
    for product_id, product_data in data.items():
        try:
            history[product_id] = ProductHistory.from_dict(product_data)
        except (TypeError, KeyError) as e:
            logger.warning(f"Skipping invalid history for {product_id}: {e}")
            continue

    return history


def save_price_history(history: Dict[str, ProductHistory]) -> None:
    """Save price history to price_history.json with atomic write."""
    # Convert to dictionary format
    data = {
        product_id: product_history.to_dict()
        for product_id, product_history in history.items()
    }

    # Atomic write: write to temp file, then rename
    temp_file = PRICE_HISTORY_FILE.with_suffix('.tmp')
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_file.replace(PRICE_HISTORY_FILE)
    except Exception as e:
        # Clean up temp file if something goes wrong
        if temp_file.exists():
            temp_file.unlink()
        raise e


def validate_product_url(url: str) -> bool:
    """Validate that URL is a valid Amazon AU product page."""
    if not url:
        return False

    # Must be Amazon AU domain
    if not url.startswith("https://www.amazon.com.au/"):
        return False

    # Should contain product identifier (dp/ or gp/product/)
    if "/dp/" not in url and "/gp/product/" not in url:
        return False

    return True
