# Configuration modules for 7taps Analytics

# Import configuration modules
from .gcp_config import GCPConfig
from .bigquery_schema import BigQuerySchema

# Create instances for easier access
gcp_config = GCPConfig()
bigquery_schema = BigQuerySchema()

__all__ = ['GCPConfig', 'BigQuerySchema', 'gcp_config', 'bigquery_schema']
