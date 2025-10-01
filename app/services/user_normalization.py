"""
User Normalization Service

Handles user profile normalization, merging, and deduplication across data sources.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.logging_config import get_logger
from app.config.gcp_config import get_gcp_config

logger = get_logger("user_normalization")


class UserNormalizationService:
    """Service for normalizing and merging user profiles across data sources."""
    
    def __init__(self):
        self.gcp_config = get_gcp_config()
        self.bigquery_client = self.gcp_config.bigquery_client
        self.dataset_id = self.gcp_config.bigquery_dataset
    
    def normalize_email(self, email: str) -> str:
        """Normalize email address for consistent matching."""
        if not email:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = email.lower().strip()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, normalized):
            logger.warning(f"Invalid email format: {email}")
            return email  # Return original if invalid
        
        return normalized
    
    def generate_user_id(self, email: str, name: Optional[str] = None) -> str:
        """Generate a consistent user ID based on normalized email."""
        normalized_email = self.normalize_email(email)
        if not normalized_email:
            return ""
        
        # Use email as primary identifier
        return normalized_email
    
    def extract_user_info_from_xapi(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from xAPI statement."""
        actor = statement.get("actor", {})
        
        user_info = {
            "user_id": "",
            "email": "",
            "name": "",
            "source": "xapi",
            "first_seen": statement.get("timestamp"),
            "last_seen": statement.get("timestamp"),
            "activity_count": 1
        }
        
        # Handle different actor types
        if "mbox" in actor and actor["mbox"]:
            # Email-based actor
            mbox_value = actor["mbox"]
            if mbox_value and isinstance(mbox_value, str):
                email = mbox_value.replace("mailto:", "")
                user_info["email"] = self.normalize_email(email)
                user_info["user_id"] = self.generate_user_id(email)
            
            if "name" in actor:
                user_info["name"] = actor["name"]
        
        elif "account" in actor:
            # Account-based actor
            account = actor["account"]
            if "name" in account:
                user_info["name"] = account["name"]
            if "homePage" in account:
                user_info["user_id"] = f"{account['homePage']}#{account.get('name', '')}"
        
        elif "openid" in actor:
            # OpenID actor
            user_info["user_id"] = actor["openid"]
        
        else:
            # Anonymous or other actor types
            user_info["user_id"] = actor.get("id", "")
        
        return user_info
    
    def extract_user_info_from_csv(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from CSV row."""
        user_info = {
            "user_id": "",
            "email": "",
            "name": "",
            "source": "csv",
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "activity_count": 1,
            "csv_data": row  # Store original CSV data
        }
        
        # Try to find email in various possible columns
        email_candidates = [
            row.get("email"),
            row.get("Email"),
            row.get("EMAIL"),
            row.get("user_email"),
            row.get("learner_email"),
            row.get("participant_email")
        ]
        
        email = None
        for candidate in email_candidates:
            if candidate and self.normalize_email(candidate):
                email = candidate
                break
        
        if email:
            user_info["email"] = self.normalize_email(email)
            user_info["user_id"] = self.generate_user_id(email)
        
        # Try to find name in various possible columns
        name_candidates = [
            row.get("name"),
            row.get("Name"),
            row.get("NAME"),
            row.get("full_name"),
            row.get("learner_name"),
            row.get("participant_name"),
            row.get("first_name"),
            row.get("last_name")
        ]
        
        name = None
        for candidate in name_candidates:
            if candidate:
                name = candidate
                break
        
        if name:
            user_info["name"] = name
        
        return user_info
    
    async def find_existing_user(self, user_id: str, email: str = "") -> Optional[Dict[str, Any]]:
        """Find existing user by ID or email."""
        try:
            # Try to find by user_id first
            if user_id:
                query = f"""
                SELECT * FROM `{self.dataset_id}.users` 
                WHERE user_id = @user_id
                LIMIT 1
                """
                
                job_config = self.bigquery_client.query_config()
                job_config.query_parameters = [
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
                ]
                
                results = self.bigquery_client.query(query, job_config=job_config)
                for row in results:
                    return dict(row)
            
            # Try to find by email if user_id didn't work
            if email:
                normalized_email = self.normalize_email(email)
                query = f"""
                SELECT * FROM `{self.dataset_id}.users` 
                WHERE email = @email
                LIMIT 1
                """
                
                job_config = self.bigquery_client.query_config()
                job_config.query_parameters = [
                    bigquery.ScalarQueryParameter("email", "STRING", normalized_email)
                ]
                
                results = self.bigquery_client.query(query, job_config=job_config)
                for row in results:
                    return dict(row)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding existing user: {e}")
            return None
    
    async def merge_user_data(self, existing_user: Dict[str, Any], new_user: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new user data with existing user data."""
        merged = existing_user.copy()
        
        # Update timestamps
        if new_user.get("first_seen") and new_user["first_seen"] < merged.get("first_seen", ""):
            merged["first_seen"] = new_user["first_seen"]
        
        if new_user.get("last_seen") and new_user["last_seen"] > merged.get("last_seen", ""):
            merged["last_seen"] = new_user["last_seen"]
        
        # Update activity count
        merged["activity_count"] = merged.get("activity_count", 0) + new_user.get("activity_count", 0)
        
        # Merge names (prefer non-empty names)
        if new_user.get("name") and not merged.get("name"):
            merged["name"] = new_user["name"]
        elif new_user.get("name") and merged.get("name") and new_user["name"] != merged["name"]:
            # If both have names but they're different, keep the longer one
            if len(new_user["name"]) > len(merged["name"]):
                merged["name"] = new_user["name"]
        
        # Merge sources
        existing_sources = merged.get("sources", [])
        if isinstance(existing_sources, str):
            existing_sources = [existing_sources]
        
        new_source = new_user.get("source", "")
        if new_source and new_source not in existing_sources:
            existing_sources.append(new_source)
        
        merged["sources"] = existing_sources
        
        # Merge CSV data if present
        if new_user.get("csv_data"):
            existing_csv_data = merged.get("csv_data", [])
            if isinstance(existing_csv_data, str):
                existing_csv_data = [existing_csv_data]
            existing_csv_data.append(new_user["csv_data"])
            merged["csv_data"] = existing_csv_data
        
        return merged
    
    async def upsert_user(self, user_data: Dict[str, Any]) -> bool:
        """Insert or update user in BigQuery."""
        try:
            # Check if user already exists
            existing_user = await self.find_existing_user(
                user_data.get("user_id", ""),
                user_data.get("email", "")
            )
            
            if existing_user:
                # Merge with existing user
                user_data = await self.merge_user_data(existing_user, user_data)
                logger.info(f"Merged user data for {user_data.get('user_id', 'unknown')}")
            else:
                logger.info(f"Creating new user: {user_data.get('user_id', 'unknown')}")
            
            # Prepare data for BigQuery
            bigquery_row = {
                "user_id": user_data.get("user_id", ""),
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
                "sources": user_data.get("sources", [user_data.get("source", "")]),
                "first_seen": user_data.get("first_seen", ""),
                "last_seen": user_data.get("last_seen", ""),
                "activity_count": user_data.get("activity_count", 0),
                "csv_data": user_data.get("csv_data", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert/update in BigQuery
            table_id = f"{self.dataset_id}.users"
            table = self.bigquery_client.get_table(table_id)
            
            # Use MERGE statement for upsert
            merge_query = f"""
            MERGE `{table_id}` T
            USING (SELECT @user_id as user_id, @email as email, @name as name, 
                          @sources as sources, @first_seen as first_seen, @last_seen as last_seen,
                          @activity_count as activity_count, @csv_data as csv_data,
                          @created_at as created_at, @updated_at as updated_at) S
            ON T.user_id = S.user_id
            WHEN MATCHED THEN
              UPDATE SET 
                email = S.email,
                name = S.name,
                sources = S.sources,
                first_seen = S.first_seen,
                last_seen = S.last_seen,
                activity_count = S.activity_count,
                csv_data = S.csv_data,
                updated_at = S.updated_at
            WHEN NOT MATCHED THEN
              INSERT (user_id, email, name, sources, first_seen, last_seen, 
                      activity_count, csv_data, created_at, updated_at)
              VALUES (S.user_id, S.email, S.name, S.sources, S.first_seen, S.last_seen,
                      S.activity_count, S.csv_data, S.created_at, S.updated_at)
            """
            
            job_config = self.bigquery_client.query_config()
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter("user_id", "STRING", bigquery_row["user_id"]),
                bigquery.ScalarQueryParameter("email", "STRING", bigquery_row["email"]),
                bigquery.ScalarQueryParameter("name", "STRING", bigquery_row["name"]),
                bigquery.ScalarQueryParameter("sources", "STRING", str(bigquery_row["sources"])),
                bigquery.ScalarQueryParameter("first_seen", "STRING", bigquery_row["first_seen"]),
                bigquery.ScalarQueryParameter("last_seen", "STRING", bigquery_row["last_seen"]),
                bigquery.ScalarQueryParameter("activity_count", "INT64", bigquery_row["activity_count"]),
                bigquery.ScalarQueryParameter("csv_data", "STRING", str(bigquery_row["csv_data"])),
                bigquery.ScalarQueryParameter("created_at", "STRING", bigquery_row["created_at"]),
                bigquery.ScalarQueryParameter("updated_at", "STRING", bigquery_row["updated_at"])
            ]
            
            self.bigquery_client.query(merge_query, job_config=job_config)
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting user: {e}")
            return False
    
    async def normalize_xapi_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize xAPI statement with user information."""
        # Extract user info
        user_info = self.extract_user_info_from_xapi(statement)
        
        # Upsert user
        await self.upsert_user(user_info)
        
        # Return normalized statement with user_id
        normalized_statement = statement.copy()
        normalized_statement["normalized_user_id"] = user_info["user_id"]
        
        return normalized_statement
    
    async def normalize_csv_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CSV row with user information."""
        # Extract user info
        user_info = self.extract_user_info_from_csv(row)
        
        # Upsert user
        await self.upsert_user(user_info)
        
        # Return normalized row with user_id
        normalized_row = row.copy()
        normalized_row["normalized_user_id"] = user_info["user_id"]
        
        return normalized_row


# Global service instance (lazy-loaded)
user_normalization_service = None

def get_user_normalization_service():
    """Get the global user normalization service instance (lazy-loaded)."""
    global user_normalization_service
    if user_normalization_service is None:
        user_normalization_service = UserNormalizationService()
    return user_normalization_service
