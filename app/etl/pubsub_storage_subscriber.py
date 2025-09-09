"""
Pub/Sub Storage Subscriber for xAPI data archival.
Consumes messages from Pub/Sub topic and stores raw xAPI statements in Cloud Storage.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Google Cloud imports
from google.cloud import pubsub_v1
from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage

# Local imports
from app.config.gcp_config import gcp_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PubSubStorageSubscriber:
    """Pub/Sub subscriber that archives xAPI statements to Cloud Storage."""

    def __init__(self):
        self.project_id = gcp_config.project_id
        self.topic_name = gcp_config.pubsub_topic
        self.bucket_name = gcp_config.storage_bucket
        self.subscription_name = f"{self.topic_name}-storage-subscriber"

        # Initialize clients
        self.subscriber = pubsub_v1.SubscriberClient(credentials=gcp_config.credentials)
        self.storage_client = gcp_config.storage_client

        # Storage bucket
        self.bucket = self.storage_client.bucket(self.bucket_name)

        # Metrics and status
        self.metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "storage_objects_created": 0,
            "last_message_time": None,
            "start_time": datetime.now(timezone.utc),
            "errors": []
        }

        # Control flags
        self.running = False
        self.subscription_path = None
        self.executor = ThreadPoolExecutor(max_workers=4)

    def ensure_subscription_exists(self) -> bool:
        """Ensure the subscription exists, create if it doesn't."""
        try:
            topic_path = gcp_config.get_topic_path()
            self.subscription_path = self.subscriber.subscription_path(
                self.project_id, self.subscription_name
            )

            # Try to get existing subscription
            try:
                self.subscriber.get_subscription(request={"subscription": self.subscription_path})
                logger.info(f"Subscription {self.subscription_name} already exists")
                return True
            except gcp_exceptions.NotFound:
                # Create new subscription
                request = {
                    "name": self.subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60,
                    "enable_message_ordering": False
                }
                self.subscriber.create_subscription(request)
                logger.info(f"Created subscription {self.subscription_name}")
                return True

        except Exception as e:
            error_msg = f"Failed to ensure subscription exists: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    def ensure_bucket_exists(self) -> bool:
        """Ensure the storage bucket exists."""
        try:
            if not self.bucket.exists():
                self.bucket.create()
                logger.info(f"Created bucket {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
            return True
        except Exception as e:
            error_msg = f"Failed to ensure bucket exists: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    def generate_storage_path(self, message_data: Dict[str, Any], message_id: str) -> str:
        """Generate a structured storage path for the xAPI statement."""
        timestamp = datetime.now(timezone.utc)

        # Extract actor ID if available
        actor_id = "unknown"
        if "actor" in message_data and isinstance(message_data["actor"], dict):
            if "account" in message_data["actor"]:
                actor_id = message_data["actor"]["account"].get("name", "unknown")
            elif "mbox" in message_data["actor"]:
                actor_id = message_data["actor"]["mbox"].replace("mailto:", "")

        # Generate path: year/month/day/actor_id/timestamp_messageId.json
        path = (
            f"xapi-statements/"
            f"{timestamp.year:04d}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"{actor_id}/"
            f"{timestamp.strftime('%H%M%S')}_{message_id}.json"
        )

        return path

    def store_message_to_gcs(self, message_data: Dict[str, Any], message_id: str) -> bool:
        """Store xAPI message to Cloud Storage."""
        try:
            # Generate storage path
            blob_path = self.generate_storage_path(message_data, message_id)

            # Create blob
            blob = self.bucket.blob(blob_path)

            # Add metadata
            metadata = {
                "message_id": message_id,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "source": "pubsub_storage_subscriber",
                "content_type": "application/json"
            }

            # Store the message
            json_data = json.dumps(message_data, indent=2)
            blob.metadata = metadata
            blob.upload_from_string(json_data, content_type="application/json")

            logger.info(f"Stored message {message_id} to gs://{self.bucket_name}/{blob_path}")
            self.metrics["storage_objects_created"] += 1

            return True

        except Exception as e:
            error_msg = f"Failed to store message {message_id}: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            self.metrics["messages_failed"] += 1
            return False

    def process_message(self, message) -> None:
        """Process a single Pub/Sub message."""
        try:
            self.metrics["messages_received"] += 1

            # Decode message data
            message_data = json.loads(message.data.decode('utf-8'))
            message_id = message.message_id

            logger.info(f"Processing message {message_id}")

            # Store to Cloud Storage
            if self.store_message_to_gcs(message_data, message_id):
                self.metrics["messages_processed"] += 1
                self.metrics["last_message_time"] = datetime.now(timezone.utc)

                # Acknowledge the message
                message.ack()
                logger.info(f"Successfully processed and acknowledged message {message_id}")
            else:
                # Don't acknowledge failed messages - they'll be retried
                logger.warning(f"Failed to process message {message_id}, not acknowledging")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in message {message.message_id}: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            self.metrics["messages_failed"] += 1
        except Exception as e:
            error_msg = f"Unexpected error processing message {message.message_id}: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            self.metrics["messages_failed"] += 1

    def start_subscribing(self) -> None:
        """Start the Pub/Sub subscription loop."""
        if not self.ensure_subscription_exists():
            logger.error("Cannot start subscriber: subscription setup failed")
            return

        if not self.ensure_bucket_exists():
            logger.error("Cannot start subscriber: bucket setup failed")
            return

        self.running = True
        logger.info(f"Starting Pub/Sub subscriber for topic {self.topic_name}")

        def callback(message):
            """Callback function for message processing."""
            try:
                self.process_message(message)
            except Exception as e:
                logger.error(f"Error in message callback: {str(e)}")

        # Start the subscription
        try:
            future = self.subscriber.subscribe(self.subscription_path, callback)

            # Keep the main thread alive
            try:
                future.result()
            except KeyboardInterrupt:
                logger.info("Stopping subscriber...")
                future.cancel()
            except Exception as e:
                logger.error(f"Subscriber error: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to start subscription: {str(e)}")
        finally:
            self.running = False
            self.subscriber.close()

    def stop_subscribing(self) -> None:
        """Stop the subscription."""
        self.running = False
        logger.info("Stopping Pub/Sub storage subscriber")

    def get_status(self) -> Dict[str, Any]:
        """Get subscriber status and metrics."""
        uptime = datetime.now(timezone.utc) - self.metrics["start_time"]

        status = {
            "subscriber_name": self.subscription_name,
            "topic": self.topic_name,
            "bucket": self.bucket_name,
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "subscription_path": self.subscription_path,
            "metrics": self.metrics.copy(),
            "last_check": datetime.now(timezone.utc).isoformat()
        }

        return status

    def get_storage_metrics(self) -> Dict[str, Any]:
        """Get detailed storage metrics."""
        try:
            # Count objects in bucket (this is expensive, so cache it)
            blobs = list(self.bucket.list_blobs(prefix="xapi-statements/"))
            total_objects = len(blobs)

            # Calculate storage size
            total_size = sum(blob.size for blob in blobs if blob.size)

            return {
                "bucket_name": self.bucket_name,
                "total_objects": total_objects,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "objects_created_by_subscriber": self.metrics["storage_objects_created"],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to get storage metrics: {str(e)}",
                "bucket_name": self.bucket_name
            }


# Global subscriber instance
subscriber = PubSubStorageSubscriber()


def start_subscriber_background() -> None:
    """Start the subscriber in a background thread."""
    def run_subscriber():
        subscriber.start_subscribing()

    thread = threading.Thread(target=run_subscriber, daemon=True)
    thread.start()
    logger.info("Started Pub/Sub storage subscriber in background")


def stop_subscriber() -> None:
    """Stop the subscriber."""
    subscriber.stop_subscribing()


# For testing/development
if __name__ == "__main__":
    print("Testing Pub/Sub Storage Subscriber...")
    print("Status:", json.dumps(subscriber.get_status(), indent=2, default=str))

    # Test storage metrics
    print("Storage Metrics:", json.dumps(subscriber.get_storage_metrics(), indent=2, default=str))
