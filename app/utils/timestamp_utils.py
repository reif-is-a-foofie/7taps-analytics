"""
Centralized timestamp utilities for consistent, human-readable time formatting.
All timestamps are converted to Central Time for consistency.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

# Central Time offset (UTC-6 for CST, UTC-5 for CDT)
# For simplicity, we'll use UTC-6 (CST) year-round
CENTRAL_OFFSET = timedelta(hours=-6)
CENTRAL_TZ = timezone(CENTRAL_OFFSET)

def parse_timestamp(timestamp_input: Union[str, datetime, None]) -> datetime:
    """
    Parse various timestamp formats and return a datetime object.
    Handles None, empty strings, and invalid formats gracefully.
    """
    if timestamp_input is None:
        return datetime.now(timezone.utc)
    
    if isinstance(timestamp_input, datetime):
        return timestamp_input
    
    if isinstance(timestamp_input, str):
        timestamp_str = timestamp_input.strip()
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            # Handle ISO format with Z suffix
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            
            # Parse the timestamp
            dt = datetime.fromisoformat(timestamp_str)
            
            # Ensure it has timezone info
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_input}': {e}")
            return datetime.now(timezone.utc)
    
    return datetime.now(timezone.utc)

def to_central_time(dt: datetime) -> datetime:
    """Convert a datetime to Central Time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(CENTRAL_TZ)

def format_human_readable(timestamp_input: Union[str, datetime, None]) -> str:
    """
    Format timestamp as human-readable Central Time.
    Format: "Jan 15, 2025 2:30:45 PM CST"
    """
    dt = parse_timestamp(timestamp_input)
    central_dt = to_central_time(dt)
    
    return central_dt.strftime("%b %d, %Y %I:%M:%S %p CST")

def format_compact(timestamp_input: Union[str, datetime, None]) -> str:
    """
    Format timestamp as compact Central Time.
    Format: "2025-01-15 14:30:45 CST"
    """
    dt = parse_timestamp(timestamp_input)
    central_dt = to_central_time(dt)
    
    return central_dt.strftime("%Y-%m-%d %H:%M:%S CST")

def format_time_only(timestamp_input: Union[str, datetime, None]) -> str:
    """
    Format timestamp as time only in Central Time.
    Format: "2:30:45 PM CST"
    """
    dt = parse_timestamp(timestamp_input)
    central_dt = to_central_time(dt)
    
    return central_dt.strftime("%I:%M:%S %p CST")

def get_current_central_time() -> datetime:
    """Get current time in Central Time."""
    return datetime.now(timezone.utc).astimezone(CENTRAL_TZ)

def get_current_central_time_str() -> str:
    """Get current time as formatted string in Central Time."""
    return format_human_readable(datetime.now(timezone.utc))
