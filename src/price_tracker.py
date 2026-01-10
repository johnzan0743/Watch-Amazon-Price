from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.timezone_utils import get_sydney_timestamp, sydney_now_minus, parse_timestamp
from src.logger import get_logger

from src.config import ProductHistory, PriceRecord, Product
from src.scraper import PriceData


logger = get_logger()


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

    def _deduplicate_by_day(self, records: List[PriceRecord]) -> List[PriceRecord]:
        """
        Deduplicate price records by keeping only the lowest price per day.

        Args:
            records: List of PriceRecord objects

        Returns:
            List of PriceRecord objects with one entry per day (the lowest price)
        """
        from collections import defaultdict

        # Group records by date
        records_by_date = defaultdict(list)
        for record in records:
            date = parse_timestamp(record.timestamp).date()
            records_by_date[date].append(record)

        # Pick the lowest price for each date
        deduplicated = []
        for date in sorted(records_by_date.keys(), reverse=True):
            day_records = records_by_date[date]
            # Find record with lowest price for this day
            lowest_record = min(day_records, key=lambda r: r.price)
            deduplicated.append(lowest_record)

        return deduplicated

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
            timestamp = get_sydney_timestamp()

        # If price is None or product unavailable, skip update
        if price_data.price is None or not price_data.available:
            logger.debug(f"Skipping price update for {product.id}: price={price_data.price}, available={price_data.available}")
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
            logger.info(f"Initialized price history for {product.id} with baseline price ${price_data.price}")
            return False  # First entry is not a "new" ATL

        # Get existing history
        product_history = self.history[product.id]

        # Update last checked
        product_history.last_checked = timestamp

        # Add new record to history (prepend to keep newest first)
        # Note: We keep ALL records, including multiple per day, to preserve
        # historical low prices. Deduplication happens during report generation.
        product_history.price_history.insert(0, new_record)

        # Check if this is a new all-time low
        current_atl = product_history.all_time_low["price"] if product_history.all_time_low else float('inf')
        is_new_atl = price_data.price < current_atl

        if is_new_atl:
            product_history.all_time_low = {
                "price": price_data.price,
                "timestamp": timestamp
            }
            logger.info(f"🎉 New all-time low for {product.id}: ${price_data.price} (was ${current_atl})")

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

        # Calculate 30-day average (deduplicated: one lowest price per day)
        thirty_days_ago = sydney_now_minus(days=30)
        recent_records = [
            record
            for record in product_history.price_history
            if record.available and parse_timestamp(record.timestamp) > thirty_days_ago
        ]
        deduplicated_30_day = self._deduplicate_by_day(recent_records)
        recent_prices = [record.price for record in deduplicated_30_day]
        avg_30_day = sum(recent_prices) / len(recent_prices) if recent_prices else None

        # Get last 7 days of price history (deduplicated: one lowest price per day)
        seven_days_ago = sydney_now_minus(days=7)
        records_7_day = [
            record
            for record in product_history.price_history
            if parse_timestamp(record.timestamp) > seven_days_ago
        ]
        price_history_7_day = self._deduplicate_by_day(records_7_day)[:7]

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
