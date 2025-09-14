"""
BigQuery schema definitions for structured xAPI events.
Defines tables for actors, verbs, objects, contexts, and results.
"""

from google.cloud import bigquery
from typing import List, Dict, Any
from app.config.gcp_config import gcp_config


class BigQuerySchema:
    """BigQuery schema definitions for xAPI analytics."""

    def __init__(self):
        self.dataset_id = gcp_config.bigquery_dataset
        self.project_id = gcp_config.project_id
        self.client = gcp_config.bigquery_client

    def get_statements_table_schema(self) -> List[bigquery.SchemaField]:
        """Schema for the main statements table."""
        return [
            bigquery.SchemaField("statement_id", "STRING", mode="REQUIRED",
                               description="Unique identifier for the xAPI statement"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED",
                               description="When the statement occurred"),
            bigquery.SchemaField("stored", "TIMESTAMP", mode="REQUIRED",
                               description="When the statement was stored"),
            bigquery.SchemaField("version", "STRING", mode="NULLABLE",
                               description="xAPI version"),
            bigquery.SchemaField("actor_id", "STRING", mode="REQUIRED",
                               description="Actor identifier (mbox, account name, or openid)"),
            bigquery.SchemaField("actor_name", "STRING", mode="NULLABLE",
                               description="Human-readable actor name"),
            bigquery.SchemaField("actor_type", "STRING", mode="NULLABLE",
                               description="Actor objectType (Agent, Group)"),
            bigquery.SchemaField("verb_id", "STRING", mode="REQUIRED",
                               description="Verb IRI"),
            bigquery.SchemaField("verb_display", "STRING", mode="NULLABLE",
                               description="Human-readable verb description"),
            bigquery.SchemaField("object_id", "STRING", mode="REQUIRED",
                               description="Object IRI or identifier"),
            bigquery.SchemaField("object_name", "STRING", mode="NULLABLE",
                               description="Human-readable object name"),
            bigquery.SchemaField("object_type", "STRING", mode="NULLABLE",
                               description="Object type (Activity, Agent, Group, SubStatement, StatementRef)"),
            bigquery.SchemaField("object_definition_type", "STRING", mode="NULLABLE",
                               description="Activity definition type IRI"),
            bigquery.SchemaField("result_score_scaled", "FLOAT", mode="NULLABLE",
                               description="Scaled score between 0 and 1"),
            bigquery.SchemaField("result_score_raw", "FLOAT", mode="NULLABLE",
                               description="Raw numeric score"),
            bigquery.SchemaField("result_score_min", "FLOAT", mode="NULLABLE",
                               description="Minimum possible score"),
            bigquery.SchemaField("result_score_max", "FLOAT", mode="NULLABLE",
                               description="Maximum possible score"),
            bigquery.SchemaField("result_success", "BOOLEAN", mode="NULLABLE",
                               description="Whether the activity was successful"),
            bigquery.SchemaField("result_completion", "BOOLEAN", mode="NULLABLE",
                               description="Whether the activity was completed"),
            bigquery.SchemaField("result_response", "STRING", mode="NULLABLE",
                               description="Response to the activity"),
            bigquery.SchemaField("result_duration", "STRING", mode="NULLABLE",
                               description="Time taken to complete the activity"),
            bigquery.SchemaField("context_registration", "STRING", mode="NULLABLE",
                               description="Context registration UUID"),
            bigquery.SchemaField("context_instructor_id", "STRING", mode="NULLABLE",
                               description="Instructor actor identifier"),
            bigquery.SchemaField("context_platform", "STRING", mode="NULLABLE",
                               description="Platform that launched the activity"),
            bigquery.SchemaField("context_language", "STRING", mode="NULLABLE",
                               description="Language of the context"),
            bigquery.SchemaField("raw_json", "STRING", mode="NULLABLE",
                               description="Complete raw xAPI statement as JSON"),
        ]

    def get_actors_table_schema(self) -> List[bigquery.SchemaField]:
        """Schema for the actors dimension table."""
        return [
            bigquery.SchemaField("actor_id", "STRING", mode="REQUIRED",
                               description="Unique actor identifier"),
            bigquery.SchemaField("mbox", "STRING", mode="NULLABLE",
                               description="Email address (mbox)"),
            bigquery.SchemaField("mbox_sha1sum", "STRING", mode="NULLABLE",
                               description="SHA1 hash of mbox"),
            bigquery.SchemaField("openid", "STRING", mode="NULLABLE",
                               description="OpenID identifier"),
            bigquery.SchemaField("account_homepage", "STRING", mode="NULLABLE",
                               description="Account homepage"),
            bigquery.SchemaField("account_name", "STRING", mode="NULLABLE",
                               description="Account name"),
            bigquery.SchemaField("name", "STRING", mode="NULLABLE",
                               description="Human-readable name"),
            bigquery.SchemaField("object_type", "STRING", mode="NULLABLE",
                               description="Object type (Agent, Group)"),
            bigquery.SchemaField("first_seen", "TIMESTAMP", mode="NULLABLE",
                               description="First time this actor was seen"),
            bigquery.SchemaField("last_seen", "TIMESTAMP", mode="NULLABLE",
                               description="Last time this actor was seen"),
            bigquery.SchemaField("statement_count", "INTEGER", mode="NULLABLE",
                               description="Total statements for this actor"),
        ]

    def get_verbs_table_schema(self) -> List[bigquery.SchemaField]:
        """Schema for the verbs dimension table."""
        return [
            bigquery.SchemaField("verb_id", "STRING", mode="REQUIRED",
                               description="Verb IRI"),
            bigquery.SchemaField("display_en", "STRING", mode="NULLABLE",
                               description="English display text"),
            bigquery.SchemaField("first_seen", "TIMESTAMP", mode="NULLABLE",
                               description="First time this verb was seen"),
            bigquery.SchemaField("last_seen", "TIMESTAMP", mode="NULLABLE",
                               description="Last time this verb was seen"),
            bigquery.SchemaField("statement_count", "INTEGER", mode="NULLABLE",
                               description="Total statements using this verb"),
        ]

    def get_activities_table_schema(self) -> List[bigquery.SchemaField]:
        """Schema for the activities dimension table."""
        return [
            bigquery.SchemaField("activity_id", "STRING", mode="REQUIRED",
                               description="Activity IRI"),
            bigquery.SchemaField("name_en", "STRING", mode="NULLABLE",
                               description="English activity name"),
            bigquery.SchemaField("description_en", "STRING", mode="NULLABLE",
                               description="English activity description"),
            bigquery.SchemaField("type", "STRING", mode="NULLABLE",
                               description="Activity type IRI"),
            bigquery.SchemaField("more_info", "STRING", mode="NULLABLE",
                               description="Additional information URL"),
            bigquery.SchemaField("interaction_type", "STRING", mode="NULLABLE",
                               description="Interaction type for assessment activities"),
            bigquery.SchemaField("correct_responses_pattern", "STRING", mode="REPEATED",
                               description="Array of correct response patterns"),
            bigquery.SchemaField("choices", "STRING", mode="REPEATED",
                               description="Array of choice options"),
            bigquery.SchemaField("scale", "STRING", mode="REPEATED",
                               description="Array of scale options"),
            bigquery.SchemaField("source", "STRING", mode="REPEATED",
                               description="Array of source options"),
            bigquery.SchemaField("target", "STRING", mode="REPEATED",
                               description="Array of target options"),
            bigquery.SchemaField("steps", "STRING", mode="REPEATED",
                               description="Array of sequencing steps"),
            bigquery.SchemaField("first_seen", "TIMESTAMP", mode="NULLABLE",
                               description="First time this activity was seen"),
            bigquery.SchemaField("last_seen", "TIMESTAMP", mode="NULLABLE",
                               description="Last time this activity was seen"),
            bigquery.SchemaField("statement_count", "INTEGER", mode="NULLABLE",
                               description="Total statements for this activity"),
        ]

    def get_table_schemas(self) -> Dict[str, List[bigquery.SchemaField]]:
        """Get all table schemas."""
        return {
            "statements": self.get_statements_table_schema(),
            "actors": self.get_actors_table_schema(),
            "verbs": self.get_verbs_table_schema(),
            "activities": self.get_activities_table_schema(),
        }

    def create_dataset_if_not_exists(self) -> bool:
        """Create BigQuery dataset if it doesn't exist."""
        try:
            dataset_ref = self.client.dataset(self.dataset_id)
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = gcp_config.location

            try:
                self.client.get_dataset(dataset_ref)
                print(f"Dataset {self.dataset_id} already exists")
                return True
            except Exception:
                # Dataset doesn't exist, create it
                dataset = self.client.create_dataset(dataset)
                print(f"Created dataset {self.dataset_id}")
                return True

        except Exception as e:
            print(f"Error creating/checking dataset: {str(e)}")
            return False

    def create_table_if_not_exists(self, table_name: str, schema: List[bigquery.SchemaField]) -> bool:
        """Create BigQuery table if it doesn't exist."""
        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_name)
            table = bigquery.Table(table_ref, schema=schema)

            # Set table options
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="timestamp" if table_name == "statements" else "first_seen"
            )

            try:
                self.client.get_table(table_ref)
                print(f"Table {table_name} already exists")
                return True
            except Exception:
                # Table doesn't exist, create it
                table = self.client.create_table(table)
                print(f"Created table {table_name}")
                return True

        except Exception as e:
            print(f"Error creating/checking table {table_name}: {str(e)}")
            return False

    def create_all_tables(self) -> Dict[str, bool]:
        """Create all required tables."""
        results = {}
        schemas = self.get_table_schemas()

        # Ensure dataset exists
        dataset_created = self.create_dataset_if_not_exists()
        if not dataset_created:
            return {"dataset": False}

        # Create each table
        for table_name, schema in schemas.items():
            results[table_name] = self.create_table_if_not_exists(table_name, schema)

        return results

    def get_table_info(self) -> Dict[str, Any]:
        """Get information about all tables in the dataset."""
        info = {}
        try:
            dataset_ref = self.client.dataset(self.dataset_id)
            tables = list(self.client.list_tables(dataset_ref))

            for table in tables:
                table_info = self.client.get_table(table)
                info[table.table_id] = {
                    "row_count": table_info.num_rows,
                    "size_bytes": table_info.num_bytes,
                    "created": table_info.created.isoformat() if table_info.created else None,
                    "last_modified": table_info.modified.isoformat() if table_info.modified else None,
                }
        except Exception as e:
            info["error"] = str(e)

        return info


# Global schema instance (lazy-loaded)
_bigquery_schema = None

def get_bigquery_schema() -> BigQuerySchema:
    """Get the global BigQuery schema instance (lazy-loaded)."""
    global _bigquery_schema
    if _bigquery_schema is None:
        _bigquery_schema = BigQuerySchema()
    return _bigquery_schema

# For backward compatibility
bigquery_schema = get_bigquery_schema
