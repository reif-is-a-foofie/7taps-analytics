"""
Improved Batch AI Safety System

Smart batching strategy:
1. Content input
2. Obvious flag check (local rules)
   - If obvious flag → Run AI immediately
   - If flag → Create flag post
   - If not flag → Add to batch
3. If other → Add to batch
4. Batch trigger: 100k tokens OR 2 hours
5. Run batch AI analysis
6. Process results: flag posts or mark as analyzed
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import deque
import hashlib

from config import settings
import logging

logger = logging.getLogger("batch_ai_safety")

@dataclass
class BatchItem:
    """Item in the analysis batch."""
    content: str
    context: str
    statement_id: str
    user_id: str
    timestamp: datetime
    content_hash: str

@dataclass
class BatchConfig:
    """Batch processing configuration."""
    max_tokens: int = 100000  # 100k tokens
    max_time_hours: int = 2   # 2 hours
    max_items: int = 50       # Max items per batch
    immediate_threshold: float = 0.9  # Confidence for immediate processing

class BatchProcessor:
    """Handles batching and AI analysis."""
    
    def __init__(self):
        self.batch_queue: deque = deque()
        self.batch_config = BatchConfig()
        self.last_batch_time = datetime.now(timezone.utc)
        self.batch_lock = asyncio.Lock()
        
        # Background processor will be started when needed
        self._background_task = None
    
    def start_background_processor(self):
        """Start background batch processor if not already running."""
        if self._background_task is None or self._background_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._background_task = loop.create_task(self._background_processor())
            except RuntimeError:
                # No event loop running, background processor will start later
                pass
    
    async def process_content(self, content: str, context: str, statement_id: str, user_id: str) -> Dict[str, Any]:
        """
        Main entry point for content processing.
        
        Returns immediate result for obvious cases, or queued for batch processing.
        """
        content_hash = self._hash_content(content)
        timestamp = datetime.now(timezone.utc)
        
        # Step 1: Check for obvious flags using local rules
        obvious_result = await self._check_obvious_flags(content)
        
        if obvious_result["is_obvious"]:
            logger.info(f"Obvious flag detected for statement {statement_id} - running AI immediately for safety")
            
            # Step 2: Run AI immediately for ANY obvious flag (safety first!)
            ai_result = await self._run_immediate_ai_analysis(content, context)
            return self._create_flag_result(ai_result, statement_id, user_id, timestamp, immediate=True)
        else:
            # Step 3: Add to batch for AI analysis
            batch_item = BatchItem(
                content=content,
                context=context,
                statement_id=statement_id,
                user_id=user_id,
                timestamp=timestamp,
                content_hash=content_hash
            )
            
            async with self.batch_lock:
                self.batch_queue.append(batch_item)
                logger.info(f"Added to batch queue: {statement_id} (queue size: {len(self.batch_queue)})")
            
            # Start background processor if needed
            self.start_background_processor()
            
            # Check if batch should be processed
            await self._check_batch_trigger()
            
            # Return queued status
            return {
                "status": "queued",
                "statement_id": statement_id,
                "queue_position": len(self.batch_queue),
                "estimated_processing_time": self._estimate_processing_time(),
                "message": "Content queued for batch AI analysis"
            }
    
    async def _check_obvious_flags(self, content: str) -> Dict[str, Any]:
        """Check for obvious flags using local rules."""
        import re
        
        content_lower = content.lower()
        
        # Critical patterns - always flag immediately
        critical_patterns = [
            r"\b(kill myself|suicide|end my life|end it all)\b",
            r"\b(hurt myself|self harm|self-harm)\b",
            r"\b(want to die|don't want to live)\b"
        ]
        
        # High patterns - flag immediately
        high_patterns = [
            r"\b(rape|raped|abuse|abused)\b",
            r"\b(hurt you|kill you|threaten)\b"
        ]
        
        # Medium patterns - add to batch for AI confirmation
        medium_patterns = [
            r"\b(depressed|depression|hopeless|hopelessness)\b",
            r"\b(empty inside|nothing matters|pointless)\b"
        ]
        
        # Check critical
        for pattern in critical_patterns:
            if re.search(pattern, content_lower):
                return {
                    "is_obvious": True,
                    "severity": "critical",
                    "confidence": 0.95,
                    "flagged_reasons": ["Critical safety concern detected"],
                    "suggested_actions": ["Immediate intervention required"]
                }
        
        # Check high
        for pattern in high_patterns:
            if re.search(pattern, content_lower):
                return {
                    "is_obvious": True,
                    "severity": "high",
                    "confidence": 0.9,
                    "flagged_reasons": ["High-risk content detected"],
                    "suggested_actions": ["Urgent review required"]
                }
        
        # Check medium
        for pattern in medium_patterns:
            if re.search(pattern, content_lower):
                return {
                    "is_obvious": True,
                    "severity": "medium",
                    "confidence": 0.8,
                    "flagged_reasons": ["Potential mental health concern"],
                    "suggested_actions": ["Monitor and review"]
                }
        
        return {"is_obvious": False}
    
    async def _run_immediate_ai_analysis(self, content: str, context: str) -> Dict[str, Any]:
        """Run AI analysis immediately for safety concerns."""
        try:
            import google.generativeai as genai
            
            if not settings.GOOGLE_AI_API_KEY:
                return {"error": "AI not configured"}
            
            genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""
            You are a specialized AI safety analyst for a digital wellness education platform. Your role is to analyze learner responses for potential safety concerns, mental health issues, or harmful content.

            CONTENT TO ANALYZE: "{content}"
            CONTEXT: {context}
            
            This content has triggered our preliminary safety filters and requires immediate AI analysis. Analyze it thoroughly for:
            
            1. **Self-harm or suicide ideation** (critical priority)
            2. **Violence or threats** (high priority) 
            3. **Mental health distress** (medium priority)
            4. **Trauma disclosures** (medium priority)
            5. **Harmful or inappropriate content** (low priority)
            
            Consider context carefully - distinguish between:
            - Direct expressions of harm vs. metaphorical language
            - Genuine distress vs. casual expressions
            - Learning-related frustration vs. serious mental health concerns
            
            Provide your analysis in this exact JSON format:
            
            {{
                "is_flagged": true/false,
                "severity": "critical/high/medium/low",
                "flagged_reasons": ["specific reasons for flagging"],
                "confidence_score": 0.0-1.0,
                "suggested_actions": ["specific recommended actions"],
                "analysis_notes": "brief explanation of your assessment"
            }}
            
            Be thorough but precise. Err on the side of caution for safety concerns.
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
                    "analysis_method": "immediate_ai",
                    "processing_time": "immediate",
                    "batch_id": None
                }
                return result
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse immediate AI response: {response.text}")
                return {"error": "AI response parsing failed"}
                
        except Exception as e:
            logger.error(f"Immediate AI analysis failed: {e}")
            return {"error": str(e)}
    
    async def _check_batch_trigger(self):
        """Check if batch should be processed based on size, tokens, or time."""
        current_time = datetime.now(timezone.utc)
        
        # Check time trigger (2 hours)
        time_trigger = (current_time - self.last_batch_time).total_seconds() > (self.batch_config.max_time_hours * 3600)
        
        # Check size trigger (50 items or 100k tokens)
        size_trigger = len(self.batch_queue) >= self.batch_config.max_items
        
        # Estimate token count (rough estimate: 1 token ≈ 4 characters)
        estimated_tokens = sum(len(item.content) for item in self.batch_queue) // 4
        token_trigger = estimated_tokens >= self.batch_config.max_tokens
        
        if time_trigger or size_trigger or token_trigger:
            logger.info(f"Batch trigger activated: time={time_trigger}, size={size_trigger}, tokens={token_trigger}")
            await self._process_batch()
    
    async def _process_batch(self):
        """Process the current batch with AI analysis."""
        if not self.batch_queue:
            return
        
        async with self.batch_lock:
            if not self.batch_queue:
                return
            
            # Take items from queue
            batch_items = list(self.batch_queue)
            self.batch_queue.clear()
            self.last_batch_time = datetime.now(timezone.utc)
        
        logger.info(f"Processing batch of {len(batch_items)} items")
        
        # Process batch with AI
        batch_results = await self._run_batch_ai_analysis(batch_items)
        
        # Process results
        await self._process_batch_results(batch_items, batch_results)
    
    async def _run_batch_ai_analysis(self, batch_items: List[BatchItem]) -> List[Dict[str, Any]]:
        """Run AI analysis on a batch of items."""
        try:
            import google.generativeai as genai
            
            if not settings.GOOGLE_AI_API_KEY:
                return [{"error": "AI not configured"} for _ in batch_items]
            
            genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Create batch prompt
            batch_content = []
            for i, item in enumerate(batch_items):
                batch_content.append(f"{i+1}. CONTENT: \"{item.content}\" | CONTEXT: {item.context}")
            
            batch_text = "\n".join(batch_content)
            
            prompt = f"""
            You are a specialized AI safety analyst for a digital wellness education platform. Your role is to analyze learner responses for potential safety concerns, mental health issues, or harmful content.

            BATCH ANALYSIS: {len(batch_items)} learner responses requiring safety review
            
            BATCH CONTENT:
            {batch_text}
            
            Analyze each item thoroughly for:
            1. **Self-harm or suicide ideation** (critical priority)
            2. **Violence or threats** (high priority) 
            3. **Mental health distress** (medium priority)
            4. **Trauma disclosures** (medium priority)
            5. **Harmful or inappropriate content** (low priority)
            
            Consider context carefully - distinguish between:
            - Direct expressions of harm vs. metaphorical language
            - Genuine distress vs. casual expressions
            - Learning-related frustration vs. serious mental health concerns
            
            For each item, provide analysis in this exact JSON format:
            {{
                "item_number": 1-{len(batch_items)},
                "is_flagged": true/false,
                "severity": "low/medium/high/critical",
                "flagged_reasons": ["specific reasons for flagging"],
                "confidence_score": 0.0-1.0,
                "suggested_actions": ["specific recommended actions"],
                "analysis_notes": "brief explanation of assessment"
            }}
            
            Return as JSON array: [{{...}}, {{...}}, ...]
            
            Be thorough but precise. Err on the side of caution for safety concerns.
            """
            
            response = model.generate_content(prompt)
            
            # Parse batch response
            try:
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                results = json.loads(response_text)
                
                # Add metadata to each result
                for i, result in enumerate(results):
                    result["analysis_metadata"] = {
                        "analysis_method": "batch_ai",
                        "batch_size": len(batch_items),
                        "batch_id": f"batch_{int(time.time())}"
                    }
                
                return results
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse batch AI response: {response.text}")
                return [{"error": "Batch AI response parsing failed"} for _ in batch_items]
                
        except Exception as e:
            logger.error(f"Batch AI analysis failed: {e}")
            return [{"error": str(e)} for _ in batch_items]
    
    async def _process_batch_results(self, batch_items: List[BatchItem], batch_results: List[Dict[str, Any]]):
        """Process results from batch AI analysis."""
        for item, result in zip(batch_items, batch_results):
            if result.get("error"):
                logger.error(f"Error processing {item.statement_id}: {result['error']}")
                continue
            
            if result.get("is_flagged", False):
                # Create flag post
                flag_result = self._create_flag_result(result, item.statement_id, item.user_id, item.timestamp, immediate=False)
                logger.info(f"Flagged content from batch: {item.statement_id} - {result.get('severity', 'unknown')}")
                # TODO: Store flag result in database or send alerts
            else:
                # Mark as analyzed
                logger.info(f"Content cleared from batch: {item.statement_id}")
                # TODO: Mark as analyzed in database
    
    def _create_flag_result(self, analysis_result: Dict[str, Any], statement_id: str, user_id: str, timestamp: datetime, immediate: bool) -> Dict[str, Any]:
        """Create standardized flag result."""
        return {
            "status": "flagged",
            "statement_id": statement_id,
            "user_id": user_id,
            "timestamp": timestamp.isoformat(),
            "is_flagged": analysis_result.get("is_flagged", False),
            "severity": analysis_result.get("severity", "unknown"),
            "flagged_reasons": analysis_result.get("flagged_reasons", []),
            "confidence_score": analysis_result.get("confidence_score", 0.0),
            "suggested_actions": analysis_result.get("suggested_actions", []),
            "analysis_metadata": {
                **analysis_result.get("analysis_metadata", {}),
                "immediate_processing": immediate,
                "processing_time": timestamp.isoformat()
            }
        }
    
    def _hash_content(self, content: str) -> str:
        """Create hash for content deduplication."""
        return hashlib.md5(content.lower().strip().encode()).hexdigest()
    
    def _estimate_processing_time(self) -> str:
        """Estimate when batch will be processed."""
        if len(self.batch_queue) >= self.batch_config.max_items:
            return "Within minutes (batch size reached)"
        
        time_remaining = self.batch_config.max_time_hours * 3600 - (datetime.now(timezone.utc) - self.last_batch_time).total_seconds()
        if time_remaining <= 0:
            return "Processing now"
        elif time_remaining < 3600:
            return f"Within {int(time_remaining/60)} minutes"
        else:
            return f"Within {int(time_remaining/3600)} hours"
    
    async def _background_processor(self):
        """Background task to process batches periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._check_batch_trigger()
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def get_batch_status(self) -> Dict[str, Any]:
        """Get current batch processing status."""
        return {
            "queue_size": len(self.batch_queue),
            "last_batch_time": self.last_batch_time.isoformat(),
            "time_since_last_batch": (datetime.now(timezone.utc) - self.last_batch_time).total_seconds(),
            "estimated_tokens": sum(len(item.content) for item in self.batch_queue) // 4,
            "config": {
                "max_tokens": self.batch_config.max_tokens,
                "max_time_hours": self.batch_config.max_time_hours,
                "max_items": self.batch_config.max_items
            }
        }

# Global batch processor instance
batch_processor = BatchProcessor()


# FastAPI routes removed - using Flask instead
