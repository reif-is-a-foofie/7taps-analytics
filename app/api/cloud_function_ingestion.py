"""
Cloud Function for xAPI statement ingestion.
Receives xAPI statements via HTTP POST and publishes them to Pub/Sub for processing.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Google Cloud imports
from google.cloud import pubsub_v1
from google.api_core import exceptions as gcp_exceptions
from google.auth import default

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCP Configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'taps-data')
PUBSUB_TOPIC = os.environ.get('PUBSUB_TOPIC', 'xapi-ingestion-topic')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'taps-data-raw-xapi')

# Initialize Pub/Sub client lazily
publisher = None
topic_path = None

def get_pubsub_client():
    """Get or initialize Pub/Sub client."""
    global publisher, topic_path
    if publisher is None:
        try:
            credentials, project = default()
            publisher = pubsub_v1.PublisherClient(credentials=credentials)
            topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
            logger.info(f"Initialized Pub/Sub client for topic: {topic_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub client: {e}")
            raise
    return publisher, topic_path


def validate_xapi_statement(statement: Dict[str, Any]) -> bool:
    """Validate basic xAPI statement structure."""
    required_fields = ["actor", "verb", "object"]
    return all(field in statement for field in required_fields)


def publish_to_pubsub(statement: Dict[str, Any]) -> Dict[str, Any]:
    """Publish xAPI statement to Pub/Sub topic."""
    try:
        # Get Pub/Sub client (lazy initialization)
        publisher, topic_path = get_pubsub_client()
            
        message_data = json.dumps(statement).encode('utf-8')

        # Add metadata
        attributes = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "cloud_function",
            "statement_count": "1"
        }

        future = publisher.publish(
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
        raise Exception(f"Pub/Sub topic not found: {PUBSUB_TOPIC}")
    except Exception as e:
        logger.error(f"Failed to publish to Pub/Sub: {str(e)}")
        raise Exception(f"Pub/Sub publishing failed: {str(e)}")


def cloud_ingest_xapi(request) -> tuple[str, int]:
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
            'Access-Control-Allow-Methods': 'POST, PUT, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }

        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            return json.dumps({'status': 'ok'}), 200

        # Accept both POST and PUT requests
        if request.method not in ['POST', 'PUT']:
            return json.dumps({
                'error': 'Method not allowed',
                'message': 'Only POST and PUT requests are accepted',
                'supported_methods': ['POST', 'PUT']
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
            'message': f'Successfully ingested {len(statements)} xAPI statement(s) via {request.method}',
            'method': request.method,
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
        # Check if Pub/Sub client is initialized
        pubsub_status = {
            "publisher_initialized": publisher is not None,
            "topic_path": topic_path,
            "project_id": PROJECT_ID,
            "topic_name": PUBSUB_TOPIC
        }

        # Additional Cloud Function specific checks
        function_status = {
            "function_name": "cloud_ingest_xapi",
            "runtime": "python39",
            "last_check": datetime.utcnow().isoformat(),
            "pubsub_status": pubsub_status
        }

        # Determine overall health
        is_healthy = publisher is not None and topic_path is not None

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
    print(f"Project ID: {PROJECT_ID}")
    print(f"Topic: {PUBSUB_TOPIC}")
    print(f"Bucket: {STORAGE_BUCKET}")
    print(f"Publisher initialized: {publisher is not None}")
    print(f"Topic path: {topic_path}")