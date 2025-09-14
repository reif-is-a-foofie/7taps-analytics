#!/usr/bin/env python3
"""
Heroku PostgreSQL to BigQuery Data Migration Script

This script migrates existing data from the Heroku PostgreSQL database
to the newly deployed BigQuery infrastructure.

Usage:
    python migrate_heroku_to_bigquery.py [--dry-run]
"""

import os
import sys
import json
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.api_core import exceptions as google_exceptions
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    print("Please install required packages:")
    print("pip install psycopg2-binary pandas google-cloud-bigquery")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HerokuToBigQueryMigrator:
    """Migrates data from Heroku PostgreSQL to BigQuery."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_id = "taps-data"
        self.dataset_id = "taps_data"
        self.heroku_credentials = self.get_heroku_credentials()
        self.bq_client = self.get_bigquery_client()
        
        self.migration_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "tables_migrated": [],
            "errors": [],
            "summary": {}
        }

    def get_heroku_credentials(self) -> Dict[str, str]:
        """Get Heroku PostgreSQL credentials."""
        return {
            "host": "c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
            "database": "d7s5ke2hmuqipn",
            "user": "u19o5qm786p1d1",
            "password": "p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2",
            "port": "5432"
        }

    def get_bigquery_client(self):
        """Get BigQuery client."""
        key_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'google-cloud-key.json'
        )

        if os.path.exists(key_file):
            credentials = service_account.Credentials.from_service_account_file(key_file)
            return bigquery.Client(credentials=credentials, project=self.project_id)
        else:
            return bigquery.Client(project=self.project_id)

    def get_heroku_connection(self):
        """Get connection to Heroku PostgreSQL database."""
        try:
            conn = psycopg2.connect(
                host=self.heroku_credentials["host"],
                database=self.heroku_credentials["database"],
                user=self.heroku_credentials["user"],
                password=self.heroku_credentials["password"],
                port=self.heroku_credentials["port"]
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to Heroku database: {e}")
            raise

    def get_heroku_tables(self) -> List[str]:
        """Get list of tables from Heroku database."""
        try:
            with self.get_heroku_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name;
                    """)
                    tables = [row[0] for row in cur.fetchall()]
                    logger.info(f"Found {len(tables)} tables in Heroku database: {tables}")
                    return tables
        except Exception as e:
            logger.error(f"Failed to get Heroku tables: {e}")
            self.migration_results["errors"].append(f"Failed to get Heroku tables: {e}")
            return []

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema from Heroku database."""
        try:
            with self.get_heroku_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position;
                    """, (table_name,))
                    
                    schema = []
                    for row in cur.fetchall():
                        schema.append({
                            "name": row[0],
                            "type": row[1],
                            "nullable": row[2] == "YES",
                            "default": row[3]
                        })
                    return schema
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            return []

    def map_postgres_to_bigquery_type(self, pg_type: str) -> str:
        """Map PostgreSQL data types to BigQuery data types."""
        type_mapping = {
            "integer": "INTEGER",
            "bigint": "INTEGER",
            "smallint": "INTEGER",
            "serial": "INTEGER",
            "bigserial": "INTEGER",
            "real": "FLOAT",
            "double precision": "FLOAT",
            "numeric": "NUMERIC",
            "decimal": "NUMERIC",
            "boolean": "BOOLEAN",
            "character varying": "STRING",
            "varchar": "STRING",
            "text": "STRING",
            "character": "STRING",
            "char": "STRING",
            "timestamp without time zone": "TIMESTAMP",
            "timestamp with time zone": "TIMESTAMP",
            "date": "DATE",
            "time": "TIME",
            "json": "JSON",
            "jsonb": "JSON"
        }
        return type_mapping.get(pg_type.lower(), "STRING")

    def create_bigquery_schema(self, table_name: str, pg_schema: List[Dict[str, Any]]) -> List[bigquery.SchemaField]:
        """Create BigQuery schema from PostgreSQL schema."""
        bq_schema = []
        for column in pg_schema:
            bq_type = self.map_postgres_to_bigquery_type(column["type"])
            mode = "NULLABLE" if column["nullable"] else "REQUIRED"
            
            bq_schema.append(bigquery.SchemaField(
                name=column["name"],
                field_type=bq_type,
                mode=mode,
                description=f"Migrated from Heroku PostgreSQL table {table_name}"
            ))
        return bq_schema

    def migrate_table(self, table_name: str) -> Dict[str, Any]:
        """Migrate a single table from Heroku to BigQuery."""
        logger.info(f"Starting migration of table: {table_name}")
        
        result = {
            "table_name": table_name,
            "status": "pending",
            "rows_migrated": 0,
            "errors": []
        }
        
        try:
            # Get table schema
            pg_schema = self.get_table_schema(table_name)
            if not pg_schema:
                result["status"] = "failed"
                result["errors"].append("Could not get table schema")
                return result
            
            # Create BigQuery schema
            bq_schema = self.create_bigquery_schema(table_name, pg_schema)
            
            # Get data from Heroku
            with self.get_heroku_connection() as conn:
                # Handle case-sensitive table names
                quoted_table_name = f'"{table_name}"' if table_name.isupper() else table_name
                df = pd.read_sql_query(f"SELECT * FROM {quoted_table_name}", conn)
                logger.info(f"Retrieved {len(df)} rows from {table_name}")
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would migrate {len(df)} rows from {table_name}")
                result["status"] = "dry_run"
                result["rows_migrated"] = len(df)
                return result
            
            # Create BigQuery table
            table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
            table = bigquery.Table(table_ref, schema=bq_schema)
            
            try:
                table = self.bq_client.create_table(table)
                logger.info(f"Created BigQuery table: {table_name}")
            except google_exceptions.Conflict:
                logger.info(f"BigQuery table {table_name} already exists, will append data")
                table = self.bq_client.get_table(table_ref)
            
            # Upload data to BigQuery
            if len(df) > 0:
                job_config = bigquery.LoadJobConfig(
                    schema=bq_schema,
                    write_disposition="WRITE_TRUNCATE"  # Replace existing data
                )
                
                job = self.bq_client.load_table_from_dataframe(
                    df, table_ref, job_config=job_config
                )
                job.result()  # Wait for job to complete
                
                logger.info(f"Successfully migrated {len(df)} rows to BigQuery table {table_name}")
                result["status"] = "success"
                result["rows_migrated"] = len(df)
            else:
                logger.info(f"No data to migrate for table {table_name}")
                result["status"] = "success"
                result["rows_migrated"] = 0
                
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            result["status"] = "failed"
            result["errors"].append(str(e))
        
        return result

    def run_migration(self) -> Dict[str, Any]:
        """Run the complete migration process."""
        logger.info("🚀 Starting Heroku to BigQuery Migration")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be written to BigQuery")
        
        # Get list of tables to migrate
        tables = self.get_heroku_tables()
        if not tables:
            logger.error("No tables found to migrate")
            return self.migration_results
        
        # Migrate each table
        successful_migrations = 0
        total_rows = 0
        
        for table_name in tables:
            result = self.migrate_table(table_name)
            self.migration_results["tables_migrated"].append(result)
            
            if result["status"] == "success":
                successful_migrations += 1
                total_rows += result["rows_migrated"]
            elif result["status"] == "dry_run":
                successful_migrations += 1
                total_rows += result["rows_migrated"]
        
        # Generate summary
        self.migration_results["summary"] = {
            "total_tables": len(tables),
            "successful_migrations": successful_migrations,
            "failed_migrations": len(tables) - successful_migrations,
            "total_rows_migrated": total_rows,
            "migration_complete": successful_migrations == len(tables)
        }
        
        # Log results
        logger.info("\n" + "=" * 60)
        logger.info("📋 MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total tables: {len(tables)}")
        logger.info(f"Successful migrations: {successful_migrations}")
        logger.info(f"Failed migrations: {len(tables) - successful_migrations}")
        logger.info(f"Total rows migrated: {total_rows}")
        
        if self.migration_results["errors"]:
            logger.error(f"Errors encountered: {len(self.migration_results['errors'])}")
            for error in self.migration_results["errors"]:
                logger.error(f"  • {error}")
        
        if self.migration_results["summary"]["migration_complete"]:
            logger.info("🎉 MIGRATION COMPLETE!")
        else:
            logger.warning("⚠️  MIGRATION INCOMPLETE - Some tables failed to migrate")
        
        return self.migration_results

    def save_results(self, filename: str = None):
        """Save migration results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'heroku_to_bigquery_migration_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.migration_results, f, indent=2, default=str)
        
        logger.info(f"📄 Migration results saved to: {filename}")
        return filename

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Heroku PostgreSQL to BigQuery Migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--output-file', help='Output file for migration results')
    
    args = parser.parse_args()
    
    print("🔄 Heroku PostgreSQL to BigQuery Migration Tool")
    print("Migrating existing data to GCP infrastructure...\n")
    
    migrator = HerokuToBigQueryMigrator(dry_run=args.dry_run)
    results = migrator.run_migration()
    output_file = migrator.save_results(args.output_file)
    
    # Return appropriate exit code
    exit_code = 0 if results["summary"]["migration_complete"] else 1
    print(f"\n🔚 Migration completed with exit code: {exit_code}")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
