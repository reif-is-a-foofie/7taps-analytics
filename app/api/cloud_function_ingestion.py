"""
Cloud Function for xAPI statement ingestion.
Receives xAPI statements via HTTP POST and publishes them to Pub/Sub for processing.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Google Cloud imports
from google.cloud import functions_v1
from google.api_core import exceptions as gcp_exceptions

# Local imports
from app.config.gcp_config import gcp_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_xapi_statement(statement: Dict[str, Any]) -> bool:
    """Validate basic xAPI statement structure."""
    required_fields = ["actor", "verb", "object"]
    return all(field in statement for field in required_fields)


def publish_to_pubsub(statement: Dict[str, Any]) -> Dict[str, Any]:
    """Publish xAPI statement to Pub/Sub topic."""
    try:
        topic_path = gcp_config.get_topic_path()
        message_data = json.dumps(statement).encode('utf-8')

        # Add metadata
        attributes = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "cloud_function",
            "statement_count": "1"
        }

        future = gcp_config.pubsub_publisher.publish(
            topic_path,
            message_data,
            **attributes
        )

        message_id = future.result()
        logger.info(f"Published message {message_id} to topic {topic_path}")

        return {
            "success": True,
            "message_id": message_id,
            "topic": topic_path
        }

    except gcp_exceptions.NotFound:
        logger.error(f"Pub/Sub topic {topic_path} not found")
        raise Exception(f"Pub/Sub topic not found: {gcp_config.pubsub_topic}")
    except Exception as e:
        logger.error(f"Failed to publish to Pub/Sub: {str(e)}")
        raise Exception(f"Pub/Sub publishing failed: {str(e)}")


def cloud_ingest_xapi(request: functions_v1.types.HttpRequest) -> tuple[str, int]:
    """
    Cloud Function HTTP endpoint for xAPI statement ingestion.

    Args:
        request: HTTP request object containing xAPI statement data

    Returns:
        Tuple of (response_json, status_code)
    """
    try:
        # Set CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }

        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            return json.dumps({'status': 'ok'}), 200

        # Only accept POST requests
        if request.method != 'POST':
            return json.dumps({
                'error': 'Method not allowed',
                'message': 'Only POST requests are accepted'
            }), 405

        # Get request data
        try:
            if hasattr(request, 'get_json'):
                data = request.get_json()
            else:
                # Handle raw request data
                request_data = request.data.decode('utf-8')
                data = json.loads(request_data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Invalid JSON in request: {str(e)}")
            return json.dumps({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }), 400

        # Handle single statement or batch
        statements = data if isinstance(data, list) else [data]

        # Validate statements
        invalid_statements = []
        for i, statement in enumerate(statements):
            if not validate_xapi_statement(statement):
                invalid_statements.append(i)

        if invalid_statements:
            return json.dumps({
                'error': 'Invalid xAPI statements',
                'message': f'Statements at indices {invalid_statements} are missing required fields',
                'required_fields': ['actor', 'verb', 'object']
            }), 400

        # Publish statements to Pub/Sub
        results = []
        for statement in statements:
            result = publish_to_pubsub(statement)
            results.append(result)

        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Successfully ingested {len(statements)} xAPI statement(s)',
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"Successfully processed {len(statements)} xAPI statements")
        return json.dumps(response_data), 200

    except Exception as e:
        logger.error(f"Cloud Function error: {str(e)}")
        return json.dumps({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


def get_cloud_function_status() -> tuple[str, int]:
    """
    Get the status of the Cloud Function and GCP configuration.

    Returns:
        Tuple of (response_json, status_code)
    """
    try:
        # Get GCP configuration status
        config_status = gcp_config.validate_config()

        # Additional Cloud Function specific checks
        function_status = {
            "function_name": "cloud_ingest_xapi",
            "runtime": "python39",
            "region": gcp_config.location,
            "last_check": datetime.utcnow().isoformat(),
            "config_status": config_status
        }

        # Determine overall health
        is_healthy = (
            config_status.get("credentials_valid", False) and
            len(config_status.get("errors", [])) == 0
        )

        response_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "function_status": function_status,
            "timestamp": datetime.utcnow().isoformat()
        }

        status_code = 200 if is_healthy else 503
        return json.dumps(response_data), status_code

    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# For local testing/development
if __name__ == "__main__":
    # Test the configuration
    print("Testing GCP configuration...")
    status = gcp_config.validate_config()
    print(json.dumps(status, indent=2))
