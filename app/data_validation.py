"""
Data Validation Utility for 7taps Analytics

This module provides comprehensive data validation functions to prevent false/placeholder
data from reaching the UI and ensure data integrity across all dashboard and analytics endpoints.
"""

import logging
from typing import Any, List, Dict, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass

def validate_database_value(value: Any, field_name: str, expected_type: str = "auto") -> Any:
    """
    Validate a single database value and ensure it's not a false/placeholder value.
    
    Args:
        value: The value to validate
        field_name: Name of the field for logging purposes
        expected_type: Expected data type ("auto", "int", "float", "str", "date")
    
    Returns:
        Validated value of appropriate type
    """
    if value is None:
        logger.warning(f"Database returned None for {field_name}")
        return get_default_value(expected_type)
    
    # Convert to string for validation
    value_str = str(value).strip().lower()
    
    # Check for false/placeholder values
    false_indicators = [
        'false', 'no data', 'null', 'undefined', 'none', 'n/a', '', 
        'nan', 'inf', '-inf', 'empty', 'missing', 'error'
    ]
    
    if value_str in false_indicators:
        logger.warning(f"Database returned false/placeholder value '{value}' for {field_name}")
        return get_default_value(expected_type)
    
    # Try to convert to appropriate type
    try:
        if expected_type == "int":
            return int(float(value)) if isinstance(value, (int, float)) else int(value)
        elif expected_type == "float":
            return float(value)
        elif expected_type == "str":
            return str(value) if value_str not in false_indicators else ""
        elif expected_type == "date":
            if hasattr(value, 'strftime'):
                return value
            elif isinstance(value, str):
                # Try to parse date string
                from datetime import datetime
                from app.utils.timestamp_utils import parse_timestamp
                return parse_timestamp(value)
            else:
                return get_default_value("date")
        else:  # auto
            if isinstance(value, (int, float)):
                return value
            elif value_str.replace('.', '').replace('-', '').isdigit():
                return float(value) if '.' in value_str else int(value)
            else:
                return str(value) if value_str not in false_indicators else ""
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Could not convert value '{value}' for {field_name}: {e}")
        return get_default_value(expected_type)

def get_default_value(data_type: str) -> Any:
    """Get appropriate default value for a data type."""
    defaults = {
        "int": 0,
        "float": 0.0,
        "str": "",
        "date": datetime.now(),
        "auto": 0
    }
    return defaults.get(data_type, 0)

def validate_chart_dataset(data: List[Dict], chart_type: str) -> List[Dict]:
    """
    Validate an entire chart dataset and remove any false/placeholder entries.
    
    Args:
        data: List of dictionaries containing chart data
        chart_type: Type of chart for logging purposes
    
    Returns:
        Validated list of dictionaries
    """
    if not data:
        logger.warning(f"No data returned for {chart_type} chart")
        return []
    
    validated_data = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"Invalid data item {i} in {chart_type}: not a dictionary")
            continue
            
        validated_item = {}
        for key, value in item.items():
            validated_value = validate_database_value(value, f"{chart_type}.{key}")
            validated_item[key] = validated_value
        validated_data.append(validated_item)
    
    return validated_data

def validate_metrics_data(metrics: List[Dict]) -> List[Dict]:
    """
    Validate metrics data and ensure all values are appropriate.
    
    Args:
        metrics: List of metric dictionaries
    
    Returns:
        Validated metrics list
    """
    validated_metrics = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
            
        validated_metric = {}
        for key, value in metric.items():
            if key == "value":
                validated_metric[key] = validate_database_value(value, f"metric.{key}", "auto")
            elif key in ["name", "type", "trend"]:
                validated_metric[key] = validate_database_value(value, f"metric.{key}", "str")
            else:
                validated_metric[key] = value
        validated_metrics.append(validated_metric)
    
    return validated_metrics

def validate_summary_data(summary: Dict) -> Dict:
    """
    Validate summary data and ensure all values are appropriate.
    
    Args:
        summary: Summary dictionary
    
    Returns:
        Validated summary dictionary
    """
    validated_summary = {}
    for key, value in summary.items():
        if key == "last_updated":
            validated_summary[key] = value  # Keep timestamp as is
        elif key in ["total_lessons", "total_activity_days"]:
            validated_summary[key] = validate_database_value(value, f"summary.{key}", "int")
        elif key == "avg_completion_rate":
            validated_summary[key] = validate_database_value(value, f"summary.{key}", "float")
        else:
            validated_summary[key] = value
    
    return validated_summary

def validate_analytics_response(data: Dict, response_type: str) -> Dict:
    """
    Validate analytics API response data.
    
    Args:
        data: Response data dictionary
        response_type: Type of analytics response
    
    Returns:
        Validated response data
    """
    if not isinstance(data, dict):
        logger.error(f"Invalid analytics response data for {response_type}")
        return {}
    
    validated_data = {}
    for key, value in data.items():
        if key == "labels":
            validated_data[key] = [validate_database_value(v, f"{response_type}.label", "str") for v in value] if isinstance(value, list) else []
        elif key == "datasets":
            validated_data[key] = validate_chart_dataset(value, f"{response_type}.dataset") if isinstance(value, list) else []
        elif key == "raw_data":
            validated_data[key] = validate_chart_dataset(value, f"{response_type}.raw_data") if isinstance(value, list) else []
        elif key in ["value", "total_count"]:
            validated_data[key] = validate_database_value(value, f"{response_type}.{key}", "auto")
        elif key in ["columns", "rows"]:
            validated_data[key] = value  # Keep complex structures as is
        else:
            validated_data[key] = value
    
    return validated_data

def check_for_false_indicators(data: Any, context: str = "") -> bool:
    """
    Check if data contains any false indicators.
    
    Args:
        data: Data to check
        context: Context for logging
    
    Returns:
        True if false indicators found, False otherwise
    """
    if isinstance(data, str):
        false_indicators = ['false', 'no data', 'null', 'undefined', 'none', 'n/a', '']
        if data.lower().strip() in false_indicators:
            logger.warning(f"False indicator found in {context}: '{data}'")
            return True
    elif isinstance(data, (list, tuple)):
        for item in data:
            if check_for_false_indicators(item, f"{context}.item"):
                return True
    elif isinstance(data, dict):
        for key, value in data.items():
            if check_for_false_indicators(value, f"{context}.{key}"):
                return True
    
    return False

def sanitize_for_json(data: Any) -> Any:
    """
    Sanitize data for JSON serialization.
    
    Args:
        data: Data to sanitize
    
    Returns:
        JSON-serializable data
    """
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, (list, tuple)):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    elif isinstance(data, (int, float, str, bool)) or data is None:
        return data
    else:
        return str(data)
