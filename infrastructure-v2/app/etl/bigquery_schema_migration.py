"""
BigQuery Schema Migration ETL for xAPI data.
Transforms raw xAPI JSON from Pub/Sub into structured BigQuery tables.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Google Cloud imports
from google.cloud import pubsub_v1, bigquery
from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage

# Local imports
from app.config.gcp_config import gcp_config
from app.config.bigquery_schema import get_bigquery_schema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BigQuerySchemaMigration:
    """ETL processor for migrating xAPI data to BigQuery structured tables."""

    def __init__(self):
        self.project_id = gcp_config.project_id
        self.topic_name = gcp_config.pubsub_topic
        self.storage_bucket = gcp_config.storage_bucket
        self.dataset_id = gcp_config.bigquery_dataset

        # Initialize clients
        self.subscriber = pubsub_v1.SubscriberClient(credentials=gcp_config.credentials)
        self.storage_client = gcp_config.storage_client
        self.bq_client = gcp_config.bigquery_client

        # Control flags
        self.running = False
        self.subscription_path = None
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Metrics and status
        self.metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bq_rows_inserted": 0,
            "last_message_time": None,
            "start_time": datetime.now(timezone.utc),
            "errors": []
        }

    def ensure_subscription_exists(self) -> bool:
        """Ensure the subscription exists for raw data processing."""
        try:
            # Use a different subscription for BigQuery processing
            topic_path = gcp_config.get_topic_path()
            self.subscription_path = self.subscriber.subscription_path(
                self.project_id, f"{self.topic_name}-bigquery-migration"
            )

            # Try to get existing subscription
            try:
                self.subscriber.get_subscription(request={"subscription": self.subscription_path})
                logger.info(f"BigQuery subscription already exists")
                return True
            except gcp_exceptions.NotFound:
                # Create new subscription
                request = {
                    "name": self.subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 300,  # 5 minutes for complex processing
                    "enable_message_ordering": False
                }
                self.subscriber.create_subscription(request)
                logger.info(f"Created BigQuery subscription")
                return True

        except Exception as e:
            error_msg = f"Failed to ensure subscription exists: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    def ensure_tables_exist(self) -> bool:
        """Ensure BigQuery tables exist."""
        try:
            results = get_bigquery_schema().create_all_tables()
            success = all(results.values())

            if success:
                logger.info("All BigQuery tables verified/created successfully")
                return True
            else:
                error_msg = f"Failed to create tables: {results}"
                logger.error(error_msg)
                self.metrics["errors"].append(error_msg)
                return False

        except Exception as e:
            error_msg = f"Error ensuring tables exist: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    def extract_actor_info(self, actor: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actor information from xAPI statement."""
        actor_info = {
            "actor_id": None,
            "mbox": None,
            "mbox_sha1sum": None,
            "openid": None,
            "account_homepage": None,
            "account_name": None,
            "name": actor.get("name"),
            "object_type": actor.get("objectType", "Agent")
        }

        # Extract identifier based on available fields
        if "mbox" in actor:
            actor_info["actor_id"] = actor["mbox"]
            actor_info["mbox"] = actor["mbox"]
        elif "mbox_sha1sum" in actor:
            actor_info["actor_id"] = actor["mbox_sha1sum"]
            actor_info["mbox_sha1sum"] = actor["mbox_sha1sum"]
        elif "openid" in actor:
            actor_info["actor_id"] = actor["openid"]
            actor_info["openid"] = actor["openid"]
        elif "account" in actor:
            account = actor["account"]
            homepage = account.get("homePage", "")
            name = account.get("name", "")
            actor_info["actor_id"] = f"{homepage}:{name}"
            actor_info["account_homepage"] = homepage
            actor_info["account_name"] = name

        return actor_info

    def extract_verb_info(self, verb: Dict[str, Any]) -> Dict[str, Any]:
        """Extract verb information from xAPI statement."""
        verb_info = {
            "verb_id": verb.get("id"),
            "display_en": None
        }

        # Extract display text (prefer English)
        display = verb.get("display", {})
        if "en" in display:
            verb_info["display_en"] = display["en"]
        elif "en-US" in display:
            verb_info["display_en"] = display["en-US"]
        elif display:
            # Use first available language
            verb_info["display_en"] = next(iter(display.values()))

        return verb_info

    def extract_activity_info(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract activity information from xAPI statement."""
        activity_info = {
            "activity_id": obj.get("id"),
            "name_en": None,
            "description_en": None,
            "type": None,
            "more_info": obj.get("moreInfo"),
            "interaction_type": None,
            "correct_responses_pattern": [],
            "choices": [],
            "scale": [],
            "source": [],
            "target": [],
            "steps": []
        }

        definition = obj.get("definition", {})

        # Extract name and description
        if "name" in definition:
            name = definition["name"]
            if "en" in name:
                activity_info["name_en"] = name["en"]
            elif "en-US" in name:
                activity_info["name_en"] = name["en-US"]

        if "description" in definition:
            desc = definition["description"]
            if "en" in desc:
                activity_info["description_en"] = desc["en"]
            elif "en-US" in desc:
                activity_info["description_en"] = desc["en-US"]

        # Extract type and interaction details
        activity_info["type"] = definition.get("type")

        if "interactionType" in definition:
            activity_info["interaction_type"] = definition["interactionType"]

            # Extract interaction-specific data
            if definition["interactionType"] == "choice":
                activity_info["choices"] = [
                    f"{choice.get('id', '')}: {choice.get('description', {}).get('en', '')}"
                    for choice in definition.get("choices", [])
                ]
                activity_info["correct_responses_pattern"] = definition.get("correctResponsesPattern", [])

            elif definition["interactionType"] == "sequencing":
                activity_info["choices"] = [
                    f"{choice.get('id', '')}: {choice.get('description', {}).get('en', '')}"
                    for choice in definition.get("choices", [])
                ]

            elif definition["interactionType"] == "likert":
                activity_info["scale"] = [
                    f"{scale.get('id', '')}: {scale.get('description', {}).get('en', '')}"
                    for scale in definition.get("scale", [])
                ]

            elif definition["interactionType"] == "matching":
                activity_info["source"] = [
                    f"{src.get('id', '')}: {src.get('description', {}).get('en', '')}"
                    for src in definition.get("source", [])
                ]
                activity_info["target"] = [
                    f"{tgt.get('id', '')}: {tgt.get('description', {}).get('en', '')}"
                    for tgt in definition.get("target", [])
                ]

            elif definition["interactionType"] == "performance":
                activity_info["steps"] = [
                    f"{step.get('id', '')}: {step.get('description', {}).get('en', '')}"
                    for step in definition.get("steps", [])
                ]

        return activity_info

    def transform_xapi_to_structured(self, xapi_statement: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw xAPI JSON to structured format for BigQuery."""
        try:
            statement_id = xapi_statement.get("id", "")
            timestamp_str = xapi_statement.get("timestamp", "")

            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now(timezone.utc)

            # Extract actor information
            actor_info = self.extract_actor_info(xapi_statement.get("actor", {}))

            # Extract verb information
            verb_info = self.extract_verb_info(xapi_statement.get("verb", {}))

            # Extract object information
            obj = xapi_statement.get("object", {})
            object_id = obj.get("id", "")
            object_name = None
            object_type = obj.get("objectType", "Activity")
            object_definition_type = None

            if "definition" in obj:
                definition = obj["definition"]
                if "name" in definition:
                    name_dict = definition["name"]
                    if "en" in name_dict:
                        object_name = name_dict["en"]
                    elif "en-US" in name_dict:
                        object_name = name_dict["en-US"]

                if "type" in definition:
                    object_definition_type = definition["type"]

            # Extract result information
            result = xapi_statement.get("result", {})
            result_score_scaled = result.get("score", {}).get("scaled")
            result_score_raw = result.get("score", {}).get("raw")
            result_score_min = result.get("score", {}).get("min")
            result_score_max = result.get("score", {}).get("max")
            result_success = result.get("success")
            result_completion = result.get("completion")
            result_response = result.get("response")
            result_duration = result.get("duration")

            # Extract context information
            context = xapi_statement.get("context", {})
            context_registration = context.get("registration")
            context_instructor_id = None
            context_platform = context.get("platform")
            context_language = context.get("language")

            if "instructor" in context:
                instructor_info = self.extract_actor_info(context["instructor"])
                context_instructor_id = instructor_info["actor_id"]

            # Create structured statement record
            structured_statement = {
                "statement_id": statement_id,
                "timestamp": timestamp.isoformat(),
                "stored": datetime.now(timezone.utc).isoformat(),
                "version": xapi_statement.get("version", "1.0.0"),
                "actor_id": actor_info["actor_id"],
                "actor_name": actor_info["name"],
                "actor_type": actor_info["object_type"],
                "verb_id": verb_info["verb_id"],
                "verb_display": verb_info["display_en"],
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
                "raw_json": json.dumps(xapi_statement)
            }

            return {
                "statement": structured_statement,
                "actor": actor_info,
                "verb": verb_info,
                "activity": self.extract_activity_info(obj) if object_type == "Activity" else None
            }

        except Exception as e:
            logger.error(f"Error transforming xAPI statement: {str(e)}")
            raise

    def insert_into_bigquery(self, data: Dict[str, Any]) -> bool:
        """Insert transformed data into BigQuery tables."""
        try:
            # Insert statement
            if "statement" in data:
                table_ref = self.bq_client.dataset(self.dataset_id).table("statements")
                table = self.bq_client.get_table(table_ref)

                errors = self.bq_client.insert_rows(table, [data["statement"]])
                if errors:
                    logger.error(f"BigQuery insert errors: {errors}")
                    return False

            # Insert/update actor (upsert logic would be handled by BigQuery scheduled queries)
            if "actor" in data:
                table_ref = self.bq_client.dataset(self.dataset_id).table("actors")
                table = self.bq_client.get_table(table_ref)

                # For now, just insert - deduplication would be handled by scheduled queries
                try:
                    errors = self.bq_client.insert_rows(table, [data["actor"]])
                    if errors:
                        logger.debug(f"Actor insert errors (expected for duplicates): {errors}")
                except Exception:
                    # Ignore duplicate key errors for actors
                    pass

            # Insert/update verb
            if "verb" in data:
                table_ref = self.bq_client.dataset(self.dataset_id).table("verbs")
                table = self.bq_client.get_table(table_ref)

                try:
                    errors = self.bq_client.insert_rows(table, [data["verb"]])
                    if errors:
                        logger.debug(f"Verb insert errors (expected for duplicates): {errors}")
                except Exception:
                    # Ignore duplicate key errors for verbs
                    pass

            # Insert/update activity
            if "activity" in data and data["activity"]:
                table_ref = self.bq_client.dataset(self.dataset_id).table("activities")
                table = self.bq_client.get_table(table_ref)

                try:
                    errors = self.bq_client.insert_rows(table, [data["activity"]])
                    if errors:
                        logger.debug(f"Activity insert errors (expected for duplicates): {errors}")
                except Exception:
                    # Ignore duplicate key errors for activities
                    pass

            self.metrics["bq_rows_inserted"] += 1
            return True

        except Exception as e:
            error_msg = f"BigQuery insert error: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            return False

    def process_message(self, message) -> None:
        """Process a single Pub/Sub message."""
        try:
            self.metrics["messages_received"] += 1

            # Decode message data (this comes from Cloud Function, contains raw xAPI)
            message_data = json.loads(message.data.decode('utf-8'))
            message_id = message.message_id

            logger.info(f"Processing BigQuery message {message_id}")

            # Transform xAPI to structured format
            structured_data = self.transform_xapi_to_structured(message_data)

            # Insert into BigQuery
            if self.insert_into_bigquery(structured_data):
                self.metrics["messages_processed"] += 1
                self.metrics["last_message_time"] = datetime.now(timezone.utc)

                # Acknowledge the message
                message.ack()
                logger.info(f"Successfully processed and inserted message {message_id}")
            else:
                # Don't acknowledge failed messages - they'll be retried
                logger.warning(f"Failed to insert message {message_id}, not acknowledging")

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

    def start_migration(self) -> None:
        """Start the BigQuery migration subscription loop."""
        if not self.ensure_subscription_exists():
            logger.error("Cannot start migration: subscription setup failed")
            return

        if not self.ensure_tables_exist():
            logger.error("Cannot start migration: table setup failed")
            return

        self.running = True
        logger.info(f"Starting BigQuery migration for topic {self.topic_name}")

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
                logger.info("Stopping BigQuery migration...")
                future.cancel()
            except Exception as e:
                logger.error(f"Migration error: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to start migration subscription: {str(e)}")
        finally:
            self.running = False
            self.subscriber.close()

    def stop_migration(self) -> None:
        """Stop the migration."""
        self.running = False
        logger.info("Stopping BigQuery schema migration")

    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status and metrics."""
        uptime = datetime.now(timezone.utc) - self.metrics["start_time"]

        status = {
            "migration_name": "bigquery_schema_migration",
            "topic": self.topic_name,
            "dataset": self.dataset_id,
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "subscription_path": self.subscription_path,
            "metrics": self.metrics.copy(),
            "last_check": datetime.now(timezone.utc).isoformat()
        }

        return status

    def get_bigquery_metrics(self) -> Dict[str, Any]:
        """Get BigQuery table metrics."""
        try:
            table_info = get_bigquery_schema().get_table_info()
            return {
                "dataset": self.dataset_id,
                "tables": table_info,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to get BigQuery metrics: {str(e)}",
                "dataset": self.dataset_id
            }

    def trigger_manual_migration(self, raw_xapi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manually trigger migration for a single xAPI statement."""
        try:
            # Transform the data
            structured_data = self.transform_xapi_to_structured(raw_xapi_data)

            # Insert into BigQuery
            success = self.insert_into_bigquery(structured_data)

            result = {
                "success": success,
                "statement_id": raw_xapi_data.get("id", "unknown"),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }

            if success:
                self.metrics["messages_processed"] += 1
                result["message"] = "Statement successfully migrated to BigQuery"
            else:
                result["message"] = "Failed to migrate statement to BigQuery"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "statement_id": raw_xapi_data.get("id", "unknown"),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }


# Global migration instance (lazy-loaded)
_migration = None

def get_migration() -> BigQuerySchemaMigration:
    """Get the global migration instance (lazy-loaded)."""
    global _migration
    if _migration is None:
        _migration = BigQuerySchemaMigration()
    return _migration

# For backward compatibility
migration = get_migration


def start_migration_background() -> None:
    """Start the migration in a background thread."""
    def run_migration():
        migration.start_migration()

    thread = threading.Thread(target=run_migration, daemon=True)
    thread.start()
    logger.info("Started BigQuery schema migration in background")


def stop_migration() -> None:
    """Stop the migration."""
    migration.stop_migration()


# For testing/development
if __name__ == "__main__":
    print("Testing BigQuery Schema Migration...")
    print("Status:", json.dumps(migration.get_migration_status(), indent=2, default=str))
    print("BigQuery Metrics:", json.dumps(migration.get_bigquery_metrics(), indent=2, default=str))
