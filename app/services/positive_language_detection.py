"""
Positive Language Detection Service

Detects positive language, gratitude, growth mindset, and encouraging content.
These are stored separately from flagged content and do NOT trigger email alerts.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from google.cloud import bigquery

from app.config.gcp_config import gcp_config
from app.logging_config import get_logger

logger = get_logger("positive_language_detection")


class PositiveLanguageDetection:
    """Detects and stores positive language patterns."""
    
    def __init__(self):
        try:
            self.client = gcp_config.bigquery_client
            self.dataset_id = gcp_config.bigquery_dataset
            self.project_id = gcp_config.project_id
            self.table_id = "positive_language"
            self._enabled = True
        except Exception as e:
            logger.warning(f"BigQuery not available, positive language detection disabled: {e}")
            self.client = None
            self.dataset_id = None
            self.project_id = None
            self.table_id = "positive_language"
            self._enabled = False
    
    def ensure_table_exists(self) -> bool:
        """Ensure the positive_language table exists."""
        try:
            from app.config.bigquery_schema import get_bigquery_schema
            schema = get_bigquery_schema()
            return schema.create_table_if_not_exists(self.table_id, schema.get_positive_language_table_schema())
        except Exception as e:
            logger.error(f"Failed to ensure positive_language table exists: {e}")
            return False
    
    async def detect_positive_language(
        self,
        content: str,
        context: str = "general"
    ) -> Dict[str, Any]:
        """
        Detect positive language in content.
        
        Returns:
            Dict with is_positive, sentiment_score, positive_categories, etc.
        """
        try:
            import google.generativeai as genai
            from app.config import settings
            
            if not settings.GOOGLE_AI_API_KEY:
                return self._fallback_positive_detection(content)
            
            genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""
            Analyze this learner content for POSITIVE language, gratitude, growth mindset, and encouraging expressions.
            
            CONTENT: "{content}"
            CONTEXT: {context}
            
            Look for:
            1. **Gratitude expressions**: "thankful", "grateful", "appreciate", "blessed"
            2. **Growth mindset**: "learning", "improving", "progress", "getting better"
            3. **Encouraging language**: "inspired", "motivated", "excited", "hopeful"
            4. **Positive outcomes**: "helped me", "made a difference", "feeling better"
            5. **Celebration**: "proud", "accomplished", "achieved", "success"
            
            Respond with JSON only:
            {{
                "is_positive": true/false,
                "sentiment_score": 0.0-1.0,
                "positive_categories": ["gratitude", "growth_mindset", "encouraging", "positive_outcome", "celebration"],
                "positive_phrases": ["specific phrases detected"],
                "confidence_score": 0.0-1.0,
                "analysis_notes": "brief explanation"
            }}
            
            Only mark as positive if there are clear positive expressions. Be conservative.
            """
            
            response = model.generate_content(prompt)
            
            # Parse response
            try:
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                result = json.loads(response_text)
                result["analysis_metadata"] = {
                    "analysis_method": "ai_positive_detection",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                return result
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse positive language AI response: {response.text}")
                return self._fallback_positive_detection(content)
                
        except Exception as e:
            logger.error(f"Positive language AI analysis failed: {e}")
            return self._fallback_positive_detection(content)
    
    def _fallback_positive_detection(self, content: str) -> Dict[str, Any]:
        """Fallback keyword-based positive detection."""
        import re
        
        content_lower = content.lower()
        positive_patterns = [
            r"\b(thankful|grateful|appreciate|blessed)\b",
            r"\b(learning|improving|progress|getting better)\b",
            r"\b(inspired|motivated|excited|hopeful)\b",
            r"\b(helped me|made a difference|feeling better)\b",
            r"\b(proud|accomplished|achieved|success)\b"
        ]
        
        matches = []
        for pattern in positive_patterns:
            if re.search(pattern, content_lower):
                matches.append(pattern)
        
        is_positive = len(matches) > 0
        
        return {
            "is_positive": is_positive,
            "sentiment_score": 0.7 if is_positive else 0.3,
            "positive_categories": ["keyword_match"] if is_positive else [],
            "positive_phrases": matches if is_positive else [],
            "confidence_score": 0.6 if is_positive else 0.4,
            "analysis_metadata": {
                "analysis_method": "fallback_keywords"
            }
        }
    
    async def persist_positive_language(
        self,
        statement_id: str,
        timestamp: datetime,
        actor_id: str,
        actor_name: Optional[str],
        content: str,
        positive_result: Dict[str, Any],
        cohort: Optional[str] = None
    ) -> bool:
        """
        Persist positive language detection to BigQuery.
        Does NOT send email alerts.
        """
        if not self._enabled:
            logger.debug("Positive language persistence disabled, skipping BigQuery write")
            return False
        
        try:
            # Ensure table exists
            if not self.ensure_table_exists():
                logger.warning("positive_language table not available, skipping persistence")
                return False
            
            detected_at = datetime.now(timezone.utc)
            
            # Prepare row
            row = {
                "statement_id": statement_id,
                "timestamp": timestamp.isoformat(),
                "detected_at": detected_at.isoformat(),
                "actor_id": actor_id,
                "actor_name": actor_name,
                "content": content[:10000] if content else None,
                "is_positive": positive_result.get("is_positive", False),
                "sentiment_score": positive_result.get("sentiment_score", 0.0),
                "positive_categories": positive_result.get("positive_categories", []),
                "positive_phrases": positive_result.get("positive_phrases", []),
                "confidence_score": positive_result.get("confidence_score", 0.0),
                "cohort": cohort,
                "raw_analysis": json.dumps(positive_result)
            }
            
            # Insert into BigQuery
            table_ref = self.client.dataset(self.dataset_id).table(self.table_id)
            table = self.client.get_table(table_ref)
            
            errors = self.client.insert_rows_json(table, [row])
            
            if errors:
                logger.error(f"Failed to persist positive language: {errors}")
                return False
            
            logger.info(f"Persisted positive language: {statement_id} (sentiment: {positive_result.get('sentiment_score', 0):.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Error persisting positive language: {e}")
            return False


# Global instance
positive_language_detection = PositiveLanguageDetection()

