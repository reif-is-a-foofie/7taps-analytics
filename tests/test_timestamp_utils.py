"""Tests for timestamp utilities - no GCP dependencies."""

import pytest
from datetime import datetime, timezone
from app.utils.timestamp_utils import (
    parse_timestamp,
    format_human_readable,
    format_compact,
    format_time_only,
    to_central_time
)


class TestTimestampUtils:
    """Test timestamp utility functions."""

    def test_parse_timestamp_valid_iso(self):
        """Test parsing valid ISO timestamp."""
        result = parse_timestamp("2025-01-15T14:30:45Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_valid_iso_with_offset(self):
        """Test parsing valid ISO timestamp with offset."""
        result = parse_timestamp("2025-01-15T14:30:45+00:00")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_none(self):
        """Test parsing None timestamp."""
        result = parse_timestamp(None)
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_empty_string(self):
        """Test parsing empty string timestamp."""
        result = parse_timestamp("")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_whitespace(self):
        """Test parsing whitespace-only timestamp."""
        result = parse_timestamp("   ")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp."""
        result = parse_timestamp("invalid-timestamp")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_timestamp_datetime_object(self):
        """Test parsing datetime object."""
        dt = datetime.now(timezone.utc)
        result = parse_timestamp(dt)
        assert result == dt

    def test_format_human_readable(self):
        """Test human readable formatting."""
        result = format_human_readable("2025-01-15T14:30:45Z")
        assert "Jan 15, 2025" in result
        assert "CST" in result
        assert "PM" in result or "AM" in result

    def test_format_compact(self):
        """Test compact formatting."""
        result = format_compact("2025-01-15T14:30:45Z")
        assert "2025-01-15" in result
        assert "CST" in result

    def test_format_time_only(self):
        """Test time-only formatting."""
        result = format_time_only("2025-01-15T14:30:45Z")
        assert "CST" in result
        assert "PM" in result or "AM" in result

    def test_to_central_time(self):
        """Test conversion to Central Time."""
        utc_dt = datetime(2025, 1, 15, 20, 30, 45, tzinfo=timezone.utc)
        central_dt = to_central_time(utc_dt)
        assert central_dt.hour == 14  # UTC-6
        assert central_dt.tzinfo.utcoffset(None).total_seconds() == -6 * 3600

    def test_none_type_handling(self):
        """Test that None values are handled gracefully."""
        # These should not raise NoneType errors
        assert format_human_readable(None) is not None
        assert format_compact(None) is not None
        assert format_time_only(None) is not None
        assert parse_timestamp(None) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
