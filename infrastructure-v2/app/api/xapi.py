"""
xAPI ingestion endpoints with proper error handling and validation.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Dict, Any, Optional, List
import structlog
import json
from datetime import datetime

from config.settings import settings
from config.gcp_config import gcp_config
from app.core.exceptions import ValidationError, ExternalServiceError
from app.services.xapi_service import XAPIService

logger = structlog.get_logger()
router = APIRouter()


class XAPIStatement(BaseModel):
    """xAPI statement model with validation."""
    
    id: Optional[str] = None
    actor: Dict[str, Any]
    verb: Dict[str, Any]
    object: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    stored: Optional[str] = None
    
    @validator('actor')
    def validate_actor(cls, v):
        """Validate actor structure."""
        if not isinstance(v, dict):
            raise ValueError("Actor must be an object")
        if not v.get('mbox') and not v.get('mbox_sha1sum') and not v.get('openid'):
            raise ValueError("Actor must have mbox, mbox_sha1sum, or openid")
        return v
    
    @validator('verb')
    def validate_verb(cls, v):
        """Validate verb structure."""
        if not isinstance(v, dict):
            raise ValueError("Verb must be an object")
        if not v.get('id'):
            raise ValueError("Verb must have an id")
        return v
    
    @validator('object')
    def validate_object(cls, v):
        """Validate object structure."""
        if not isinstance(v, dict):
            raise ValueError("Object must be an object")
        if not v.get('id'):
            raise ValueError("Object must have an id")
        return v


class XAPIBatch(BaseModel):
    """Batch xAPI statements model."""
    
    statements: List[XAPIStatement]
    
    @validator('statements')
    def validate_statements(cls, v):
        """Validate statements list."""
        if not v:
            raise ValueError("Statements list cannot be empty")
        if len(v) > 100:  # Reasonable batch limit
            raise ValueError("Cannot process more than 100 statements at once")
        return v


@router.post("/ingest")
async def ingest_xapi_statement(statement: XAPIStatement) -> Dict[str, Any]:
    """Ingest a single xAPI statement."""
    try:
        logger.info(
            "Processing xAPI statement",
            statement_id=statement.id,
            actor=statement.actor,
            verb=statement.verb.get('id'),
            object=statement.object.get('id')
        )
        
        # Initialize xAPI service
        xapi_service = XAPIService(gcp_config)
        
        # Process statement
        result = await xapi_service.ingest_statement(statement.dict())
        
        logger.info(
            "xAPI statement processed successfully",
            statement_id=statement.id,
            result=result
        )
        
        return {
            "success": True,
            "statement_id": statement.id,
            "processed_at": datetime.utcnow().isoformat(),
            "result": result
        }
        
    except ValidationError as e:
        logger.warning("xAPI validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except ExternalServiceError as e:
        logger.error("xAPI service error", error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
        
    except Exception as e:
        logger.error("Unexpected xAPI error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest/batch")
async def ingest_xapi_batch(batch: XAPIBatch) -> Dict[str, Any]:
    """Ingest multiple xAPI statements."""
    try:
        logger.info(
            "Processing xAPI batch",
            statement_count=len(batch.statements)
        )
        
        # Initialize xAPI service
        xapi_service = XAPIService(gcp_config)
        
        # Process batch
        results = await xapi_service.ingest_batch([s.dict() for s in batch.statements])
        
        successful = len([r for r in results if r.get('success')])
        failed = len(results) - successful
        
        logger.info(
            "xAPI batch processed",
            total=len(batch.statements),
            successful=successful,
            failed=failed
        )
        
        return {
            "success": True,
            "processed_at": datetime.utcnow().isoformat(),
            "summary": {
                "total": len(batch.statements),
                "successful": successful,
                "failed": failed
            },
            "results": results
        }
        
    except ValidationError as e:
        logger.warning("xAPI batch validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error("Unexpected xAPI batch error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def xapi_status() -> Dict[str, Any]:
    """Get xAPI ingestion service status."""
    try:
        xapi_service = XAPIService(gcp_config)
        status = await xapi_service.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": status
        }
        
    except Exception as e:
        logger.error("xAPI status check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

