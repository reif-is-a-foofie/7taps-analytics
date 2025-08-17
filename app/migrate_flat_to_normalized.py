"""
Migration script to move data from statements_flat to normalized tables
Fixes the ETL process issue where data is not being normalized
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from app.data_normalization import DataNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlatToNormalizedMigrator:
    """Migrate data from statements_flat to normalized tables"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics",
        )

        # Connection pool
        self.db_pool = SimpleConnectionPool(
            minconn=1, maxconn=10, dsn=self.database_url
        )

        # Initialize normalizer
        self.normalizer = DataNormalizer()

        # Migration stats
        self.migrated_count = 0
        self.error_count = 0

    async def get_db_connection(self):
        """Get database connection from pool"""
        return self.db_pool.getconn()

    async def put_db_connection(self, conn):
        """Return database connection to pool"""
        self.db_pool.putconn(conn)

    async def get_flat_statements(self) -> List[Dict[str, Any]]:
        """Get all statements from statements_flat table"""
        try:
            conn = await self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT * FROM statements_flat 
                ORDER BY processed_at ASC
            """
            )

            statements = cursor.fetchall()
            cursor.close()
            await self.put_db_connection(conn)

            logger.info(f"Found {len(statements)} statements in statements_flat")
            return statements

        except Exception as e:
            logger.error(f"Error getting flat statements: {e}")
            raise

    async def migrate_statement(self, flat_statement: Dict[str, Any]) -> bool:
        """Migrate a single statement from flat to normalized"""
        try:
            # Parse the raw statement
            raw_statement = json.loads(flat_statement["raw_statement"])

            # Process through normalization pipeline
            await self.normalizer.process_statement_normalization(raw_statement)

            self.migrated_count += 1
            logger.info(
                f"Migrated statement {flat_statement['statement_id']} ({self.migrated_count})"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error migrating statement {flat_statement['statement_id']}: {e}"
            )
            self.error_count += 1
            return False

    async def validate_schema(self) -> bool:
        """Check that all required tables and indexes exist before migration."""
        required_tables = [
            "statements_flat",
            "statements_normalized",
            "actors",
            "activities",
            "verbs",
        ]
        try:
            conn = await self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN %s
            """,
                (tuple(required_tables),),
            )
            found = {row[0] for row in cursor.fetchall()}
            cursor.close()
            await self.put_db_connection(conn)
            missing = [t for t in required_tables if t not in found]
            if missing:
                logger.error(f"Missing required tables: {missing}")
                return False
            return True
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False

    async def run_migration(self) -> Dict[str, Any]:
        """Run the complete migration"""
        logger.info("Starting migration from statements_flat to normalized tables")

        try:
            # Pre-migration schema validation
            if not await self.validate_schema():
                return {
                    "migrated_count": 0,
                    "error_count": 0,
                    "total_count": 0,
                    "success": False,
                    "error": "Schema validation failed. Required tables missing.",
                }
            # Get all flat statements
            flat_statements = await self.get_flat_statements()

            if not flat_statements:
                logger.info("No statements found in statements_flat")
                return {
                    "migrated_count": 0,
                    "error_count": 0,
                    "total_count": 0,
                    "success": True,
                }

            # Migrate each statement (idempotent: ON CONFLICT DO NOTHING in insert)
            for statement in flat_statements:
                try:
                    await self.migrate_statement(statement)
                except Exception as e:
                    logger.error(
                        f"Migration failed for statement {statement.get('statement_id')}: {e}"
                    )
                    self.error_count += 1

            # Get final stats
            stats = await self.normalizer.get_normalization_stats()

            result = {
                "migrated_count": self.migrated_count,
                "error_count": self.error_count,
                "total_count": len(flat_statements),
                "success": self.error_count == 0,
                "normalization_stats": stats,
            }

            logger.info(f"Migration completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {
                "migrated_count": self.migrated_count,
                "error_count": self.error_count,
                "total_count": 0,
                "success": False,
                "error": str(e),
            }

    async def validate_migration(self) -> Dict[str, Any]:
        """Validate the migration results"""
        try:
            conn = await self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get counts
            cursor.execute("SELECT COUNT(*) as count FROM statements_flat")
            flat_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM statements_normalized")
            normalized_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM actors")
            actor_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM activities")
            activity_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM verbs")
            verb_count = cursor.fetchone()["count"]

            cursor.close()
            await self.put_db_connection(conn)

            return {
                "statements_flat": flat_count,
                "statements_normalized": normalized_count,
                "actors": actor_count,
                "activities": activity_count,
                "verbs": verb_count,
                "normalization_ratio": round(
                    (normalized_count / max(flat_count, 1)) * 100, 2
                ),
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e)}


# CLI interface
async def main():
    """Main migration function"""
    migrator = FlatToNormalizedMigrator()

    print("🚀 Starting migration from statements_flat to normalized tables...")

    # Run migration
    result = await migrator.run_migration()

    if result["success"]:
        print(f"✅ Migration completed successfully!")
        print(f"   Migrated: {result['migrated_count']} statements")
        print(f"   Errors: {result['error_count']}")
        print(f"   Total: {result['total_count']}")
    else:
        print(f"❌ Migration failed!")
        print(f"   Migrated: {result['migrated_count']} statements")
        print(f"   Errors: {result['error_count']}")
        if "error" in result:
            print(f"   Error: {result['error']}")

    # Validate results
    print("\n📊 Validation Results:")
    validation = await migrator.validate_migration()

    if "error" not in validation:
        print(f"   Statements (Flat): {validation['statements_flat']}")
        print(f"   Statements (Normalized): {validation['statements_normalized']}")
        print(f"   Actors: {validation['actors']}")
        print(f"   Activities: {validation['activities']}")
        print(f"   Verbs: {validation['verbs']}")
        print(f"   Normalization Ratio: {validation['normalization_ratio']}%")
    else:
        print(f"   Validation Error: {validation['error']}")


if __name__ == "__main__":
    asyncio.run(main())
