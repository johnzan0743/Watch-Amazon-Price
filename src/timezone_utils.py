"""Timezone utilities for consistent Sydney, Australia time handling."""
from datetime import datetime, timedelta
import pytz


# Sydney timezone
SYDNEY_TZ = pytz.timezone('Australia/Sydney')


def get_sydney_now() -> datetime:
    """Get current datetime in Sydney, Australia timezone (timezone-aware)."""
    return datetime.now(SYDNEY_TZ)


def get_sydney_timestamp() -> str:
    """Get current timestamp in Sydney timezone as ISO 8601 string.
    
    Returns:
        ISO 8601 formatted timestamp string (e.g., "2026-01-10T14:30:00+11:00")
    """
    return get_sydney_now().isoformat()


def sydney_now_minus(days: int = 0) -> datetime:
    """Get Sydney time minus specified number of days (timezone-aware).
    
    Args:
        days: Number of days to subtract from current Sydney time
        
    Returns:
        Timezone-aware datetime object in Sydney timezone
    """
    return get_sydney_now() - timedelta(days=days)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to timezone-aware datetime in Sydney timezone.
    
    Args:
        timestamp_str: ISO formatted timestamp string (supports both UTC 'Z' suffix and explicit timezone)
        
    Returns:
        Timezone-aware datetime object converted to Sydney timezone
    """
    # Handle legacy UTC timestamps with 'Z' suffix
    if timestamp_str.endswith('Z'):
        utc_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        utc_time = datetime.fromisoformat(timestamp_str)
    
    # Convert to Sydney timezone
    return utc_time.astimezone(SYDNEY_TZ)
