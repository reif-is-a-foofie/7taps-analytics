# Configuration modules for 7taps Analytics

# Import configuration modules
from .gcp_config import GCPConfig
from .bigquery_schema import BigQuerySchema, get_bigquery_schema

# Import settings and utility functions from the main config module
import importlib.util
import os
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
settings = config_module.settings

# Import utility functions
get_extension_key = config_module.get_extension_key
get_lesson_url = config_module.get_lesson_url
get_lesson_name = config_module.get_lesson_name
get_lesson_by_url = config_module.get_lesson_by_url
get_lesson_by_number = config_module.get_lesson_by_number

# Create instances for easier access (lazy-loaded)
_gcp_config = None
_bigquery_schema = None

def get_gcp_config() -> GCPConfig:
    """Get the global GCP config instance (lazy-loaded)."""
    global _gcp_config
    if _gcp_config is None:
        _gcp_config = GCPConfig()
    return _gcp_config

def get_bigquery_schema_instance() -> BigQuerySchema:
    """Get the global BigQuery schema instance (lazy-loaded)."""
    global _bigquery_schema
    if _bigquery_schema is None:
        _bigquery_schema = BigQuerySchema()
    return _bigquery_schema

# For backward compatibility: export instantiated singletons
gcp_config = get_gcp_config()
bigquery_schema = get_bigquery_schema_instance

__all__ = [
    'GCPConfig', 'BigQuerySchema', 'gcp_config', 'bigquery_schema', 
    'get_gcp_config', 'get_bigquery_schema_instance', 'settings',
    'get_extension_key', 'get_lesson_url', 'get_lesson_name',
    'get_lesson_by_url', 'get_lesson_by_number'
]
