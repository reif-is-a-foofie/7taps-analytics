"""
Alert Email Management Service

Manages alert email addresses for flagged content notifications.
Stores emails in BigQuery for persistence.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from google.cloud import bigquery

from app.config.gcp_config import gcp_config
from app.logging_config import get_logger

logger = get_logger("alert_email_management")


class AlertEmailManager:
    """Manages alert email addresses."""
    
    def __init__(self):
        try:
            self.client = gcp_config.bigquery_client
            self.dataset_id = gcp_config.bigquery_dataset
            self.project_id = gcp_config.project_id
            self.table_id = "alert_emails"
            self._enabled = True
        except Exception as e:
            logger.warning(f"BigQuery not available, alert email management disabled: {e}")
            self.client = None
            self.dataset_id = None
            self.project_id = None
            self.table_id = "alert_emails"
            self._enabled = False
            # Default emails if BigQuery not available
            self._default_emails = ["reiftauati@gmail.com"]
    
    def ensure_table_exists(self) -> bool:
        """Ensure the alert_emails table exists."""
        try:
            from app.config.bigquery_schema import get_bigquery_schema
            schema = get_bigquery_schema()
            return schema.create_table_if_not_exists(self.table_id, schema.get_alert_emails_table_schema())
        except Exception as e:
            logger.error(f"Failed to ensure alert_emails table exists: {e}")
            return False
    
    async def get_all_emails(self) -> List[Dict[str, Any]]:
        """Get all alert email addresses."""
        if not self._enabled:
            return [{"email": email, "id": f"default_{i}", "created_at": None, "is_active": True} 
                   for i, email in enumerate(self._default_emails)]
        
        try:
            if not self.ensure_table_exists():
                return []
            
            query = f"""
            SELECT 
                email_id,
                email,
                is_active,
                created_at,
                updated_at
            FROM `{self.dataset_id}.{self.table_id}`
            WHERE is_active = true
            ORDER BY created_at DESC
            """
            
            results = list(self.client.query(query).result())
            
            emails = []
            for row in results:
                emails.append({
                    "id": row.email_id,
                    "email": row.email,
                    "is_active": row.is_active,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                })
            
            # Always include default email if not in list
            default_email = "reiftauati@gmail.com"
            if not any(e["email"].lower() == default_email.lower() for e in emails):
                emails.insert(0, {
                    "id": "default",
                    "email": default_email,
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None
                })
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get alert emails: {e}")
            return [{"email": "reiftauati@gmail.com", "id": "default", "is_active": True, "created_at": None, "updated_at": None}]
    
    async def add_email(self, email: str) -> Dict[str, Any]:
        """Add a new alert email address."""
        if not self._enabled:
            return {"success": False, "error": "BigQuery not available"}
        
        try:
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return {"success": False, "error": "Invalid email format"}
            
            # Check if email already exists
            existing = await self.get_all_emails()
            if any(e["email"].lower() == email.lower() for e in existing):
                return {"success": False, "error": "Email already exists"}
            
            if not self.ensure_table_exists():
                return {"success": False, "error": "Table not available"}
            
            email_id = f"email_{int(datetime.now(timezone.utc).timestamp())}"
            now = datetime.now(timezone.utc)
            
            row = {
                "email_id": email_id,
                "email": email.lower().strip(),
                "is_active": True,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            table_ref = self.client.dataset(self.dataset_id).table(self.table_id)
            table = self.client.get_table(table_ref)
            
            errors = self.client.insert_rows_json(table, [row])
            
            if errors:
                logger.error(f"Failed to add alert email: {errors}")
                return {"success": False, "error": str(errors)}
            
            logger.info(f"Added alert email: {email}")
            return {"success": True, "email": row}
            
        except Exception as e:
            logger.error(f"Failed to add alert email: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_email(self, email_id: str) -> Dict[str, Any]:
        """Delete (deactivate) an alert email address."""
        if not self._enabled:
            return {"success": False, "error": "BigQuery not available"}
        
        if email_id == "default":
            return {"success": False, "error": "Cannot delete default email"}
        
        try:
            if not self.ensure_table_exists():
                return {"success": False, "error": "Table not available"}
            
            # Soft delete by setting is_active = false
            update_query = f"""
            UPDATE `{self.dataset_id}.{self.table_id}`
            SET is_active = false,
                updated_at = TIMESTAMP('{datetime.now(timezone.utc).isoformat()}')
            WHERE email_id = @email_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("email_id", "STRING", email_id)
                ]
            )
            
            self.client.query(update_query, job_config=job_config).result()
            
            logger.info(f"Deleted alert email: {email_id}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to delete alert email: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_active_emails(self) -> List[str]:
        """Get list of active email addresses (for sending alerts)."""
        emails = await self.get_all_emails()
        return [e["email"] for e in emails if e.get("is_active", True)]


# Global instance
alert_email_manager = AlertEmailManager()

