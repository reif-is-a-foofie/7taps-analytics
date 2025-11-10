"""
Service for persisting flagged content to BigQuery and sending alerts.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from google.cloud import bigquery

from app.config.gcp_config import gcp_config
from app.logging_config import get_logger

logger = get_logger("flagged_content_persistence")


class FlaggedContentPersistence:
    """Handles persistence of flagged content to BigQuery and alerts."""
    
    def __init__(self):
        try:
            self.client = gcp_config.bigquery_client
            self.dataset_id = gcp_config.bigquery_dataset
            self.project_id = gcp_config.project_id
            self.table_id = "flagged_content"
            self._enabled = True
        except Exception as e:
            logger.warning(f"BigQuery not available, persistence disabled: {e}")
            self.client = None
            self.dataset_id = None
            self.project_id = None
            self.table_id = "flagged_content"
            self._enabled = False
    
    def ensure_table_exists(self) -> bool:
        """Ensure the flagged_content table exists."""
        try:
            from app.config.bigquery_schema import get_bigquery_schema
            schema = get_bigquery_schema()
            return schema.create_table_if_not_exists(self.table_id, schema.get_flagged_content_table_schema())
        except Exception as e:
            logger.error(f"Failed to ensure flagged_content table exists: {e}")
            return False
    
    async def persist_flagged_content(
        self,
        statement_id: str,
        timestamp: datetime,
        actor_id: str,
        actor_name: Optional[str],
        content: str,
        analysis_result: Dict[str, Any],
        cohort: Optional[str] = None
    ) -> bool:
        """
        Persist flagged content to BigQuery.
        
        Args:
            statement_id: xAPI statement ID
            timestamp: When the statement occurred
            actor_id: Actor identifier
            actor_name: Actor name
            content: The flagged content text
            analysis_result: Complete analysis result
            cohort: Cohort identifier if available
            
        Returns:
            True if persisted successfully, False otherwise
        """
        if not self._enabled:
            logger.debug("Persistence disabled, skipping BigQuery write")
            # Still send alerts even if persistence is disabled
            severity = analysis_result.get("severity", "low")
            if severity in ["critical", "high"]:
                await self._send_alert(statement_id, actor_id, actor_name, content, analysis_result, cohort)
            return False
        
        try:
            # Ensure table exists
            if not self.ensure_table_exists():
                logger.warning("flagged_content table not available, skipping persistence")
                return False
            
            flagged_at = datetime.now(timezone.utc)
            
            # Prepare row
            row = {
                "statement_id": statement_id,
                "timestamp": timestamp.isoformat(),
                "flagged_at": flagged_at.isoformat(),
                "actor_id": actor_id,
                "actor_name": actor_name,
                "content": content[:10000] if content else None,  # Limit to 10k chars
                "is_flagged": analysis_result.get("is_flagged", False),
                "severity": analysis_result.get("severity", "low"),
                "flagged_reasons": analysis_result.get("flagged_reasons", []),
                "confidence_score": analysis_result.get("confidence_score", 0.0),
                "suggested_actions": analysis_result.get("suggested_actions", []),
                "analysis_method": analysis_result.get("analysis_metadata", {}).get("analysis_method", "unknown"),
                "cohort": cohort,
                "raw_analysis": json.dumps(analysis_result)
            }
            
            # Insert into BigQuery
            table_ref = self.client.dataset(self.dataset_id).table(self.table_id)
            table = self.client.get_table(table_ref)
            
            errors = self.client.insert_rows_json(table, [row])
            
            if errors:
                logger.error(f"Failed to persist flagged content: {errors}")
                return False
            
            logger.info(f"Persisted flagged content: {statement_id} (severity: {analysis_result.get('severity')})")
            
            # Send alert for critical/high severity
            severity = analysis_result.get("severity", "low")
            if severity in ["critical", "high"]:
                await self._send_alert(statement_id, actor_id, actor_name, content, analysis_result, cohort)
            
            return True
            
        except Exception as e:
            logger.error(f"Error persisting flagged content: {e}")
            return False
    
    async def _send_alert(
        self,
        statement_id: str,
        actor_id: str,
        actor_name: Optional[str],
        content: str,
        analysis_result: Dict[str, Any],
        cohort: Optional[str]
    ) -> None:
        """Send real-time alert for critical/high severity flags."""
        try:
            severity = analysis_result.get("severity", "low")
            flagged_reasons = analysis_result.get("flagged_reasons", [])
            suggested_actions = analysis_result.get("suggested_actions", [])
            
            # Log critical alert
            alert_message = f"""
🚨 CRITICAL SAFETY ALERT 🚨
Statement ID: {statement_id}
Actor: {actor_name or actor_id}
Severity: {severity.upper()}
Reasons: {', '.join(flagged_reasons)}
Content: {content[:200]}...
Suggested Actions: {', '.join(suggested_actions)}
Cohort: {cohort or 'Unknown'}
Timestamp: {datetime.now(timezone.utc).isoformat()}
"""
            
            logger.critical(alert_message)
            
            # Print to console for immediate visibility
            print(alert_message)
            
            # TODO: Add additional alert channels:
            # - Email notification
            # - Slack webhook
            # - Pub/Sub topic for downstream processing
            # - SMS for critical cases
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


# Global instance
flagged_content_persistence = FlaggedContentPersistence()

