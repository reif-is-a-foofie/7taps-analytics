"""
xAPI Statement Models for validation and processing.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json


class xAPIActor(BaseModel):
    """xAPI Actor model."""
    objectType: str = Field(default="Agent")
    name: Optional[str] = None
    mbox: Optional[str] = None
    mbox_sha1sum: Optional[str] = None
    openid: Optional[str] = None
    account: Optional[Dict[str, str]] = None
    member: Optional[List[Dict[str, Any]]] = None


class xAPIVerb(BaseModel):
    """xAPI Verb model."""
    id: str = Field(..., description="Verb identifier")
    display: Optional[Dict[str, str]] = None


class xAPIObject(BaseModel):
    """xAPI Object model."""
    objectType: Optional[str] = Field(default="Activity")
    id: str = Field(..., description="Object identifier")
    definition: Optional[Dict[str, Any]] = None


class xAPIStatement(BaseModel):
    """xAPI Statement model for validation."""
    id: Optional[str] = None
    actor: xAPIActor = Field(..., description="xAPI Actor")
    verb: xAPIVerb = Field(..., description="xAPI Verb")
    object: xAPIObject = Field(..., description="xAPI Object")
    result: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    stored: Optional[datetime] = None
    authority: Optional[xAPIActor] = None
    version: Optional[str] = Field(default="1.0.3")
    attachments: Optional[List[Dict[str, Any]]] = None

    @validator('timestamp', 'stored', pre=True)
    def parse_datetime(cls, v):
        """Parse datetime strings."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return v
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            'id': self.id,
            'actor': self.actor.dict(),
            'verb': self.verb.dict(),
            'object': self.object.dict(),
            'result': self.result,
            'context': self.context,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'stored': self.stored.isoformat() if self.stored else None,
            'authority': self.authority.dict() if self.authority else None,
            'version': self.version,
            'attachments': self.attachments
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'xAPIStatement':
        """Create from dictionary."""
        return cls(**data)


class xAPIIngestionResponse(BaseModel):
    """Response model for xAPI ingestion."""
    success: bool = Field(..., description="Ingestion success status")
    statement_id: Optional[str] = Field(None, description="Statement ID if provided")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    queue_position: Optional[int] = Field(None, description="Position in processing queue")


class xAPIIngestionStatus(BaseModel):
    """Status model for xAPI ingestion endpoint."""
    endpoint_status: str = Field(..., description="Endpoint status")
    redis_connected: bool = Field(..., description="Redis connection status")
    total_statements_ingested: int = Field(..., description="Total statements processed")
    last_ingestion_time: Optional[datetime] = Field(None, description="Last ingestion timestamp")
    queue_size: Optional[int] = Field(None, description="Current queue size")
    error_count: int = Field(default=0, description="Total error count")


class xAPIValidationError(BaseModel):
    """Validation error model."""
    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class xAPIProcessingResult(BaseModel):
    """Processing result model."""
    statement_id: str = Field(..., description="Statement ID")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="Processing status")
    errors: Optional[List[str]] = Field(None, description="Processing errors")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata") 