"""
AI Analysis Service - Cloud Function
Handles all AI-powered content analysis for 7taps Analytics.
Deploy time: ~30 seconds for algorithm changes.
"""

import json
import os
import sys
from typing import Dict, Any
from datetime import datetime, timezone
from flask import Request

# Import our AI analysis modules
from batch_ai_safety import batch_processor

def analyze_content(request: Request) -> Dict[str, Any]:
    """
    Cloud Function entry point for content analysis.
    
    Expected request format:
    {
        "content": "text to analyze",
        "context": "general|safety|wellness",
        "user_id": "user identifier",
        "statement_id": "xapi statement id"
    }
    """
    try:
        data = request.get_json()
        
        content = data.get('content', '')
        context = data.get('context', 'general')
        user_id = data.get('user_id', 'unknown')
        statement_id = data.get('statement_id', 'unknown')
        
        if not content:
            return {
                'error': 'No content provided',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Process content with AI analysis (run async function)
        import asyncio
        result = asyncio.run(batch_processor.process_content(
            content=content,
            context=context,
            user_id=user_id,
            statement_id=statement_id
        ))
        
        # Add service metadata
        result['service_info'] = {
            'service': 'ai_analysis',
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'deployment_mode': 'cloud_function'
        }
        
        return result
        
    except Exception as e:
        return {
            'error': f'AI analysis failed: {str(e)}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service_info': {
                'service': 'ai_analysis',
                'version': '1.0.0',
                'error': True
            }
        }

def get_batch_status(request: Request) -> Dict[str, Any]:
    """
    Get batch processor status.
    """
    try:
        status = batch_processor.get_batch_status()
        status['service_info'] = {
            'service': 'ai_analysis',
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return status
    except Exception as e:
        return {
            'error': f'Status check failed: {str(e)}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint.
    """
    return {
        'status': 'healthy',
        'service': 'ai_analysis',
        'version': '1.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'deployment_mode': 'cloud_function'
    }
