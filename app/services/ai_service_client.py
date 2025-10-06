"""
AI Service Client - HTTP client for calling the AI Analysis Cloud Function.
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
from app.config import settings

class AIServiceClient:
    """Client for calling the AI Analysis Cloud Function."""
    
    def __init__(self):
        # AI service URL - will be set after deployment
        self.base_url = getattr(settings, 'AI_SERVICE_URL', None)
        if not self.base_url:
            # Fallback to local processing if AI service not configured
            self.base_url = None
            print("⚠️ AI_SERVICE_URL not configured, falling back to local processing")
    
    async def analyze_content(self, content: str, context: str = "general", 
                            user_id: str = "unknown", statement_id: str = "unknown") -> Dict[str, Any]:
        """
        Analyze content using the AI Analysis service.
        
        Args:
            content: Text content to analyze
            context: Analysis context (general, safety, wellness)
            user_id: User identifier
            statement_id: Statement identifier
            
        Returns:
            Analysis results from AI service
        """
        if not self.base_url:
            # Fallback to local processing
            from app.api.batch_ai_safety import batch_processor
            return await batch_processor.process_content(content, context, user_id, statement_id)
        
        try:
            payload = {
                "content": content,
                "context": context,
                "user_id": user_id,
                "statement_id": statement_id
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/analyze_content",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"❌ AI service call failed: {e}")
            # Fallback to local processing
            from app.api.batch_ai_safety import batch_processor
            return await batch_processor.process_content(content, context, user_id, statement_id)
    
    async def get_batch_status(self) -> Dict[str, Any]:
        """Get batch processor status from AI service."""
        if not self.base_url:
            from app.api.batch_ai_safety import batch_processor
            return batch_processor.get_batch_status()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/batch_status")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"❌ AI service status check failed: {e}")
            from app.api.batch_ai_safety import batch_processor
            return batch_processor.get_batch_status()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AI service health."""
        if not self.base_url:
            return {"status": "fallback_mode", "service": "local"}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e), "service": "ai_service"}

# Global client instance
ai_service_client = AIServiceClient()
