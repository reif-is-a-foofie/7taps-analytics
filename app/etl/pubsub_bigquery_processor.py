"""
Pub/Sub BigQuery Processor for xAPI data pipeline.
Consumes messages from Pub/Sub topic and loads xAPI statements into BigQuery.
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
from google.cloud import bigquery

# Local imports
from app.config.gcp_config import get_gcp_config
from app.logging_config import get_logger
from app.services.user_normalization import get_user_normalization_service

# Configure logging
logger = get_logger("pubsub_bigquery_processor")


class PubSubBigQueryProcessor:
    """Pub/Sub subscriber that loads xAPI statements into BigQuery."""

    def __init__(self):
        self.gcp_config = get_gcp_config()
        self.project_id = self.gcp_config.project_id
        self.topic_name = self.gcp_config.pubsub_topic
        self.dataset_id = self.gcp_config.bigquery_dataset
        self.table_id = "statements"
        self.subscription_name = f"{self.topic_name}-bigquery-processor"

        # Initialize clients
        self.subscriber = pubsub_v1.SubscriberClient(credentials=self.gcp_config.credentials)
        self.bigquery_client = self.gcp_config.bigquery_client

        # BigQuery table reference
        self.table_ref = self.bigquery_client.dataset(self.dataset_id).table(self.table_id)
        self.table = self.bigquery_client.get_table(self.table_ref)

        # Metrics and status
        self.metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bigquery_rows_inserted": 0,
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
            topic_path = self.gcp_config.get_topic_path()
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

    def transform_xapi_to_bigquery_row(self, message_data: Dict[str, Any], message_id: str, normalized_user_id: str = "") -> Dict[str, Any]:
        """Transform xAPI statement to BigQuery row format."""
        try:
            # Extract core fields
            statement_id = message_data.get("id", "")
            timestamp = message_data.get("timestamp") or datetime.now(timezone.utc).isoformat()
            stored = datetime.now(timezone.utc).isoformat()
            version = message_data.get("version", "1.0.3")

            # Extract actor information safely
            actor = message_data.get("actor") or {}
            actor_id = ""
            actor_name = None
            if "account" in actor and actor["account"]:
                actor_id = actor["account"].get("name", "")
                actor_name = actor.get("name")
            elif "mbox" in actor:
                actor_id = actor["mbox"]
                actor_name = actor.get("name")

            # Extract verb information safely
            verb = message_data.get("verb") or {}
            verb_id = verb.get("id", "")
            verb_display = None
            if "display" in verb and verb["display"] and "en-US" in verb["display"]:
                verb_display = verb["display"]["en-US"]

            # Extract object information safely
            obj = message_data.get("object") or {}
            object_id = obj.get("id", "") if isinstance(obj, dict) else ""
            object_name = None
            object_type = obj.get("objectType", "Activity") if isinstance(obj, dict) else "Activity"
            object_definition_type = None

            if isinstance(obj, dict) and "definition" in obj and obj["definition"]:
                definition = obj["definition"]
                if isinstance(definition, dict):
                    if "name" in definition and definition["name"]:
                        if isinstance(definition["name"], dict) and "en-US" in definition["name"]:
                            object_name = definition["name"]["en-US"]
                    object_definition_type = definition.get("type")

            # Extract result information safely
            result = message_data.get("result") or {}
            result_score_scaled = None
            result_score_raw = None
            result_score_min = None
            result_score_max = None
            result_success = None
            result_completion = None
            result_response = None
            result_duration = None

            if result and "score" in result and result["score"]:
                score = result["score"]
                result_score_scaled = score.get("scaled")
                result_score_raw = score.get("raw")
                result_score_min = score.get("min")
                result_score_max = score.get("max")
                
                result_success = result.get("success")
                result_completion = result.get("completion")
                result_response = result.get("response")
                result_duration = result.get("duration")

            # Extract context information safely
            context = message_data.get("context") or {}
            context_registration = context.get("registration")
            context_instructor_id = None
            context_platform = context.get("platform")
            context_language = context.get("language")

            if "instructor" in context and context["instructor"]:
                instructor = context["instructor"]
                if "account" in instructor and instructor["account"]:
                    context_instructor_id = instructor["account"].get("name")
                elif "mbox" in instructor:
                    context_instructor_id = instructor["mbox"]

            # Create BigQuery row
            row = {
                "statement_id": statement_id,
                "timestamp": timestamp,
                "stored": stored,
                "version": version,
                "actor_id": actor_id,
                "actor_name": actor_name,
                "actor_type": actor.get("objectType", "Agent"),
                "normalized_user_id": normalized_user_id,
                "verb_id": verb_id,
                "verb_display": verb_display,
                "object_id": object_id,
                "object_name": object_name,
                "object_type": object_type,
                "object_definition_type": object_definition_type,
                "result_score_scaled": result_score_scaled,
                "result_score_raw": result_score_raw,
                "result_score_min": result_score_min,
                "result_score_max": result_score_max,
                "result_success": result_success,
                "result_completion": result_completion,
                "result_response": result_response,
                "result_duration": result_duration,
                "context_registration": context_registration,
                "context_instructor_id": context_instructor_id,
                "context_platform": context_platform,
                "context_language": context_language,
                "raw_json": json.dumps(message_data)
            }

            return row

        except Exception as e:
            logger.error(f"Failed to transform xAPI statement: {str(e)}")
            raise

    async def statement_exists(self, statement_id: str) -> bool:
        """Check if a statement already exists in BigQuery."""
        try:
            query = f"""
            SELECT statement_id 
            FROM `{self.dataset_id}.{self.table_id}`
            WHERE statement_id = @statement_id
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig()
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter("statement_id", "STRING", statement_id)
            ]
            
            results = self.bigquery_client.query(query, job_config=job_config)
            return len(list(results)) > 0
            
        except Exception as e:
            logger.warning(f"Error checking if statement exists: {e}")
            # If check fails, proceed with insert (fail-safe)
            return False

    async def insert_row_to_bigquery(self, row: Dict[str, Any], message_id: str) -> bool:
        """Insert or update row in BigQuery using MERGE for idempotency."""
        try:
            statement_id = row.get("statement_id", "")
            table_id = f"{self.dataset_id}.{self.table_id}"
            
            # Use MERGE statement for idempotent insert (only inserts if not exists)
            merge_query = f"""
            MERGE `{table_id}` T
            USING (SELECT 
                @statement_id as statement_id,
                @timestamp as timestamp,
                @stored as stored,
                @version as version,
                @actor_id as actor_id,
                @actor_name as actor_name,
                @actor_type as actor_type,
                @verb_id as verb_id,
                @verb_display as verb_display,
                @object_id as object_id,
                @object_name as object_name,
                @object_type as object_type,
                @object_definition_type as object_definition_type,
                @result_score_scaled as result_score_scaled,
                @result_score_raw as result_score_raw,
                @result_score_min as result_score_min,
                @result_score_max as result_score_max,
                @result_success as result_success,
                @result_completion as result_completion,
                @result_response as result_response,
                @result_duration as result_duration,
                @context_registration as context_registration,
                @context_instructor_id as context_instructor_id,
                @context_platform as context_platform,
                @context_language as context_language,
                @raw_json as raw_json
            ) S
            ON T.statement_id = S.statement_id
            WHEN NOT MATCHED THEN
              INSERT (statement_id, timestamp, stored, version, actor_id, actor_name, actor_type,
                      verb_id, verb_display, object_id, object_name, object_type, object_definition_type,
                      result_score_scaled, result_score_raw, result_score_min, result_score_max,
                      result_success, result_completion, result_response, result_duration,
                      context_registration, context_instructor_id, context_platform, context_language,
                      raw_json)
              VALUES (S.statement_id, S.timestamp, S.stored, S.version, S.actor_id, S.actor_name, S.actor_type,
                      S.verb_id, S.verb_display, S.object_id, S.object_name, S.object_type, S.object_definition_type,
                      S.result_score_scaled, S.result_score_raw, S.result_score_min, S.result_score_max,
                      S.result_success, S.result_completion, S.result_response, S.result_duration,
                      S.context_registration, S.context_instructor_id, S.context_platform, S.context_language,
                      S.raw_json)
            """
            
            job_config = bigquery.QueryJobConfig()
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter("statement_id", "STRING", row.get("statement_id", "")),
                bigquery.ScalarQueryParameter("timestamp", "TIMESTAMP", row.get("timestamp")),
                bigquery.ScalarQueryParameter("stored", "TIMESTAMP", row.get("stored")),
                bigquery.ScalarQueryParameter("version", "STRING", row.get("version")),
                bigquery.ScalarQueryParameter("actor_id", "STRING", row.get("actor_id", "")),
                bigquery.ScalarQueryParameter("actor_name", "STRING", row.get("actor_name")),
                bigquery.ScalarQueryParameter("actor_type", "STRING", row.get("actor_type")),
                bigquery.ScalarQueryParameter("verb_id", "STRING", row.get("verb_id", "")),
                bigquery.ScalarQueryParameter("verb_display", "STRING", row.get("verb_display")),
                bigquery.ScalarQueryParameter("object_id", "STRING", row.get("object_id", "")),
                bigquery.ScalarQueryParameter("object_name", "STRING", row.get("object_name")),
                bigquery.ScalarQueryParameter("object_type", "STRING", row.get("object_type")),
                bigquery.ScalarQueryParameter("object_definition_type", "STRING", row.get("object_definition_type")),
                bigquery.ScalarQueryParameter("result_score_scaled", "FLOAT", row.get("result_score_scaled")),
                bigquery.ScalarQueryParameter("result_score_raw", "FLOAT", row.get("result_score_raw")),
                bigquery.ScalarQueryParameter("result_score_min", "FLOAT", row.get("result_score_min")),
                bigquery.ScalarQueryParameter("result_score_max", "FLOAT", row.get("result_score_max")),
                bigquery.ScalarQueryParameter("result_success", "BOOLEAN", row.get("result_success")),
                bigquery.ScalarQueryParameter("result_completion", "BOOLEAN", row.get("result_completion")),
                bigquery.ScalarQueryParameter("result_response", "STRING", row.get("result_response")),
                bigquery.ScalarQueryParameter("result_duration", "STRING", row.get("result_duration")),
                bigquery.ScalarQueryParameter("context_registration", "STRING", row.get("context_registration")),
                bigquery.ScalarQueryParameter("context_instructor_id", "STRING", row.get("context_instructor_id")),
                bigquery.ScalarQueryParameter("context_platform", "STRING", row.get("context_platform")),
                bigquery.ScalarQueryParameter("context_language", "STRING", row.get("context_language")),
                bigquery.ScalarQueryParameter("raw_json", "STRING", row.get("raw_json", ""))
            ]
            
            # Execute MERGE query
            query_job = self.bigquery_client.query(merge_query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            # Check if this was an insert (MERGE only inserts when not matched)
            num_rows_affected = query_job.num_dml_affected_rows or 0
            if num_rows_affected > 0:
                logger.info(f"Successfully inserted statement {statement_id} (message {message_id})")
                self.metrics["bigquery_rows_inserted"] += 1
            else:
                logger.debug(f"Statement {statement_id} already exists, skipped duplicate insert (idempotent)")
            
            return True

        except Exception as e:
            error_msg = f"Failed to insert/update message {message_id} in BigQuery: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    async def process_message(self, message) -> None:
        """Process a single Pub/Sub message."""
        try:
            self.metrics["messages_received"] += 1

            # Decode message data
            message_data = json.loads(message.data.decode('utf-8'))
            message_id = message.message_id
            statement_id = message_data.get("id", "")

            logger.info(f"Processing message {message_id} for BigQuery (statement_id: {statement_id})")

            # Check for duplicate statement (idempotency check)
            if statement_id and await self.statement_exists(statement_id):
                logger.info(f"Statement {statement_id} already exists, skipping duplicate (idempotent)")
                # Acknowledge the message since we've already processed it
                message.ack()
                self.metrics["messages_processed"] += 1
                return

            # Normalize user data and enrich with CSV metadata if matched
            user_service = get_user_normalization_service()
            normalized_statement = await user_service.normalize_xapi_statement(message_data)
            
            # Ensure normalized_statement is not None
            if normalized_statement is None:
                logger.warning(f"normalize_xapi_statement returned None for statement {statement_id}, using original")
                normalized_statement = message_data
            
            normalized_user_id = normalized_statement.get("normalized_user_id", "")

            # Transform xAPI statement to BigQuery row (already enriched by normalization)
            row = self.transform_xapi_to_bigquery_row(normalized_statement, message_id, normalized_user_id)

            # Insert/update into BigQuery (MERGE handles idempotency)
            if await self.insert_row_to_bigquery(row, message_id):
                self.metrics["messages_processed"] += 1
                self.metrics["last_message_time"] = datetime.now(timezone.utc)

                # Acknowledge the message
                message.ack()
                logger.info(f"Successfully processed and acknowledged message {message_id}")
            else:
                # Don't acknowledge failed messages - they'll be retried
                logger.warning(f"Failed to process message {message_id}, not acknowledging")
                self.metrics["messages_failed"] += 1

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

    def start_processing(self) -> None:
        """Start the Pub/Sub subscription loop."""
        if not self.ensure_subscription_exists():
            logger.error("Cannot start processor: subscription setup failed")
            return

        self.running = True
        logger.info(f"Starting Pub/Sub BigQuery processor for topic {self.topic_name}")

        def callback(message):
            """Callback function for message processing."""
            try:
                import asyncio
                # Run the async process_message in a new event loop
                asyncio.run(self.process_message(message))
            except Exception as e:
                logger.error(f"Error in message callback: {str(e)}")

        # Start the subscription
        try:
            future = self.subscriber.subscribe(self.subscription_path, callback)

            # Keep the main thread alive
            try:
                future.result()
            except KeyboardInterrupt:
                logger.info("Stopping processor...")
                future.cancel()
            except Exception as e:
                logger.error(f"Processor error: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to start subscription: {str(e)}")
        finally:
            self.running = False
            self.subscriber.close()

    def stop_processing(self) -> None:
        """Stop the processor."""
        self.running = False
        logger.info("Stopping Pub/Sub BigQuery processor")

    def get_subscription_queue_size(self) -> Dict[str, Any]:
        """Get the current queue size for the Pub/Sub subscription."""
        try:
            if not self.subscription_path:
                return {"error": "No subscription path available"}
            
            # Get subscription details
            subscription = self.subscriber.get_subscription(request={"subscription": self.subscription_path})
            
            # Get topic details to calculate approximate queue size
            topic_path = self.gcp_config.get_topic_path()
            
            return {
                "subscription_name": self.subscription_name,
                "subscription_path": self.subscription_path,
                "topic_path": topic_path,
                "ack_deadline_seconds": subscription.ack_deadline_seconds,
                "message_retention_duration": str(subscription.message_retention_duration),
                "retry_policy": {
                    "minimum_backoff": str(subscription.retry_policy.minimum_backoff) if subscription.retry_policy else None,
                    "maximum_backoff": str(subscription.retry_policy.maximum_backoff) if subscription.retry_policy else None
                } if subscription.retry_policy else None,
                "note": "Exact message count requires Cloud Monitoring API - showing subscription config instead"
            }
            
        except Exception as e:
            logger.error(f"Failed to get subscription queue size: {e}")
            return {"error": f"Failed to get queue size: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """Get processor status and metrics."""
        uptime = datetime.now(timezone.utc) - self.metrics["start_time"]

        status = {
            "processor_name": self.subscription_name,
            "topic": self.topic_name,
            "dataset": self.dataset_id,
            "table": self.table_id,
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "subscription_path": self.subscription_path,
            "metrics": self.metrics.copy(),
            "queue_info": self.get_subscription_queue_size(),
            "last_check": datetime.now(timezone.utc).isoformat()
        }

        return status


# Global processor instance (lazy-loaded)
_processor = None

def get_processor() -> PubSubBigQueryProcessor:
    """Get the global processor instance (lazy-loaded)."""
    global _processor
    if _processor is None:
        _processor = PubSubBigQueryProcessor()
    return _processor


def start_processor_background() -> None:
    """Start the processor in a background thread."""
    def run_processor():
        try:
            processor = get_processor()
            logger.info(f"🔍 DEBUG: Starting ETL processor with subscription: {processor.subscription_name}")
            logger.info(f"🔍 DEBUG: Topic: {processor.topic_name}, Dataset: {processor.dataset_id}")
            processor.start_processing()
        except Exception as e:
            logger.error(f"🔍 DEBUG: ETL processor failed to start: {e}")

    thread = threading.Thread(target=run_processor, daemon=True)
    thread.start()
    logger.info("Started Pub/Sub BigQuery processor in background")


def stop_processor() -> None:
    """Stop the processor."""
    if _processor:
        _processor.stop_processing()


# For testing/development
if __name__ == "__main__":
    print("Testing Pub/Sub BigQuery Processor...")
    processor = get_processor()
    print("Status:", json.dumps(processor.get_status(), indent=2, default=str))
