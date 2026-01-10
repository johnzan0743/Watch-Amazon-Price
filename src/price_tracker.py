from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.config import ProductHistory, PriceRecord, Product
from src.scraper import PriceData


@dataclass
class PriceStats:
    """Price statistics for a product."""
    current_price: float
    current_timestamp: str
    all_time_low: float
    all_time_low_timestamp: str
    previous_low: Optional[float]
    avg_30_day: Optional[float]
    price_history_7_day: List[PriceRecord]
    is_new_atl: bool
    savings_percentage: float


class PriceTracker:
    """Manages price history and detects all-time lows."""

    def __init__(self, history: Dict[str, ProductHistory]):
        self.history = history

    def update_price_history(
        self,
        product: Product,
        price_data: PriceData,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Update price history for a product.

        Returns True if this is a new all-time low.
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"

        # If price is None or product unavailable, skip update
        if price_data.price is None or not price_data.available:
            print(f"Skipping price update for {product.id}: price={price_data.price}, available={price_data.available}")
            return False

        # Create new price record
        new_record = PriceRecord(
            timestamp=timestamp,
            price=price_data.price,
            currency=price_data.currency,
            available=price_data.available,
            screenshot=price_data.screenshot_path
        )

        # Initialize history if this is the first entry
        if product.id not in self.history:
            self.history[product.id] = ProductHistory(
                name=product.name,
                url=product.url,
                price_history=[new_record],
                all_time_low={
                    "price": price_data.price,
                    "timestamp": timestamp
                },
                last_checked=timestamp
            )
            print(f"Initialized price history for {product.id} with baseline price ${price_data.price}")
            return False  # First entry is not a "new" ATL

        # Get existing history
        product_history = self.history[product.id]

        # Update last checked
        product_history.last_checked = timestamp

        # Add new record to history (prepend to keep newest first)
        product_history.price_history.insert(0, new_record)

        # Check if this is a new all-time low
        current_atl = product_history.all_time_low["price"] if product_history.all_time_low else float('inf')
        is_new_atl = price_data.price < current_atl

        if is_new_atl:
            product_history.all_time_low = {
                "price": price_data.price,
                "timestamp": timestamp
            }
            print(f"🎉 New all-time low for {product.id}: ${price_data.price} (was ${current_atl})")

        return is_new_atl

    def get_price_statistics(self, product_id: str) -> Optional[PriceStats]:
        """Calculate price statistics for a product."""
        if product_id not in self.history:
            return None

        product_history = self.history[product_id]

        if not product_history.price_history:
            return None

        # Get current (most recent) price
        current_record = product_history.price_history[0]

        # Get all-time low
        atl = product_history.all_time_low
        if not atl:
            return None

        # Calculate previous low (2nd lowest price)
        sorted_prices = sorted(
            [record.price for record in product_history.price_history if record.available],
            reverse=False
        )
        previous_low = sorted_prices[1] if len(sorted_prices) > 1 else atl["price"]

        # Calculate 30-day average
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_prices = [
            record.price
            for record in product_history.price_history
            if record.available and datetime.fromisoformat(record.timestamp.replace('Z', '+00:00')) > thirty_days_ago
        ]
        avg_30_day = sum(recent_prices) / len(recent_prices) if recent_prices else None

        # Get last 7 days of price history
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        price_history_7_day = [
            record
            for record in product_history.price_history
            if datetime.fromisoformat(record.timestamp.replace('Z', '+00:00')) > seven_days_ago
        ][:7]  # Limit to 7 entries

        # Calculate savings percentage
        savings_percentage = 0.0
        if previous_low and previous_low > 0:
            savings_percentage = ((previous_low - current_record.price) / previous_low) * 100

        # Check if current price equals ATL (is new ATL)
        is_new_atl = abs(current_record.price - atl["price"]) < 0.01

        return PriceStats(
            current_price=current_record.price,
            current_timestamp=current_record.timestamp,
            all_time_low=atl["price"],
            all_time_low_timestamp=atl["timestamp"],
            previous_low=previous_low,
            avg_30_day=avg_30_day,
            price_history_7_day=price_history_7_day,
            is_new_atl=is_new_atl,
            savings_percentage=max(0, savings_percentage)
        )

    def is_all_time_low(self, product_id: str, current_price: float) -> bool:
        """Check if the given price is an all-time low."""
        if product_id not in self.history:
            # First time seeing this product - current price is ATL by definition
            return False

        product_history = self.history[product_id]
        if not product_history.all_time_low:
            return False

        current_atl = product_history.all_time_low["price"]
        return current_price < current_atl

    def get_history(self) -> Dict[str, ProductHistory]:
        """Get the complete price history."""
        return self.history
