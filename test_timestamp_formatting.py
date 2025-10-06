#!/usr/bin/env python3
"""Test script to verify simplified timestamp formatting."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.timestamp_utils import (
    parse_timestamp, 
    format_human_readable, 
    format_compact, 
    format_time_only,
    get_current_central_time_str
)

def test_timestamp_formatting():
    """Test various timestamp formatting scenarios."""
    print("🧪 Testing simplified timestamp formatting...")
    
    # Test cases
    test_cases = [
        "2025-01-15T14:30:45Z",
        "2025-01-15T14:30:45+00:00", 
        "2025-01-15T14:30:45",
        None,
        "",
        "   ",
        "invalid-timestamp"
    ]
    
    print("\n📅 Human Readable Format (Central Time):")
    for i, test_input in enumerate(test_cases, 1):
        try:
            formatted = format_human_readable(test_input)
            print(f"  {i}. Input: {repr(test_input)} → Output: {formatted}")
        except Exception as e:
            print(f"  {i}. Input: {repr(test_input)} → Error: {e}")
    
    print("\n📅 Compact Format (Central Time):")
    for i, test_input in enumerate(test_cases, 1):
        try:
            formatted = format_compact(test_input)
            print(f"  {i}. Input: {repr(test_input)} → Output: {formatted}")
        except Exception as e:
            print(f"  {i}. Input: {repr(test_input)} → Error: {e}")
    
    print("\n📅 Time Only Format (Central Time):")
    for i, test_input in enumerate(test_cases, 1):
        try:
            formatted = format_time_only(test_input)
            print(f"  {i}. Input: {repr(test_input)} → Output: {formatted}")
        except Exception as e:
            print(f"  {i}. Input: {repr(test_input)} → Error: {e}")
    
    print(f"\n🕐 Current Central Time: {get_current_central_time_str()}")
    
    print("\n✅ Timestamp formatting test completed!")

if __name__ == "__main__":
    test_timestamp_formatting()
