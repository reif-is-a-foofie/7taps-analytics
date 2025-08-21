#!/usr/bin/env python3
"""
Test script to verify dashboard data validation is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data_validation import (
    validate_database_value, 
    validate_chart_dataset, 
    check_for_false_indicators,
    sanitize_for_json
)

def test_data_validation():
    """Test the data validation functions."""
    print("Testing data validation functions...")
    
    # Test validate_database_value
    print("\n1. Testing validate_database_value:")
    
    # Test with false indicators
    false_values = ['false', 'no data', 'null', 'undefined', 'none', 'n/a', '', 'nan']
    for value in false_values:
        result = validate_database_value(value, 'test_field', 'int')
        print(f"  '{value}' -> {result} (should be 0)")
        assert result == 0, f"Expected 0 for '{value}', got {result}"
    
    # Test with valid values
    valid_tests = [
        ('123', 'int', 123),
        ('45.67', 'float', 45.67),
        ('valid_string', 'str', 'valid_string'),
        (None, 'int', 0),
    ]
    
    for value, expected_type, expected_result in valid_tests:
        result = validate_database_value(value, 'test_field', expected_type)
        print(f"  {value} ({expected_type}) -> {result}")
        assert result == expected_result, f"Expected {expected_result}, got {result}"
    
    # Test validate_chart_dataset
    print("\n2. Testing validate_chart_dataset:")
    
    test_data = [
        {'name': 'Lesson 1', 'value': 'false', 'rate': 85.5},
        {'name': 'Lesson 2', 'value': 42, 'rate': 'no data'},
        {'name': 'Lesson 3', 'value': 67, 'rate': 92.3},
    ]
    
    validated_data = validate_chart_dataset(test_data, 'test_chart')
    print(f"  Original data: {test_data}")
    print(f"  Validated data: {validated_data}")
    
    # Test check_for_false_indicators
    print("\n3. Testing check_for_false_indicators:")
    
    test_cases = [
        ('valid data', False),
        ('false', True),
        ('no data', True),
        ('null', True),
        (['valid', 'false', 'data'], True),
        ({'key': 'value', 'bad': 'false'}, True),
        ({'key': 'value', 'good': 'data'}, False),
    ]
    
    for data, expected in test_cases:
        result = check_for_false_indicators(data, 'test_context')
        print(f"  {data} -> {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    # Test sanitize_for_json
    print("\n4. Testing sanitize_for_json:")
    
    from datetime import datetime
    test_json_data = {
        'string': 'test',
        'number': 42,
        'float': 3.14,
        'datetime': datetime.now(),
        'list': [1, 2, 3],
        'dict': {'nested': 'value'}
    }
    
    sanitized = sanitize_for_json(test_json_data)
    print(f"  Original: {test_json_data}")
    print(f"  Sanitized: {sanitized}")
    
    print("\n✅ All data validation tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_data_validation()
        print("\n🎉 Dashboard data validation is working correctly!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
