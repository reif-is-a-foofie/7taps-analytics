"""
Simple Privacy Masking System

Provides basic masking with eye icon toggle and password-protected exports.
"""

import base64
import hashlib
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone

from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("simple_privacy")

class MaskingRequest(BaseModel):
    """Request model for masking data."""
    name: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None

class UnmaskingRequest(BaseModel):
    """Request model for unmasking data."""
    masked_name: Optional[str] = None
    masked_email: Optional[str] = None
    masked_user_id: Optional[str] = None
    password: str

class ExportRequest(BaseModel):
    """Request model for exporting unmasked data."""
    data: Dict[str, Any]
    password: str
    export_reason: str

class SimpleMasker:
    """Simple masking system with eye icon toggle."""
    
    def __init__(self):
        # Simple masking key (in production, use proper key management)
        self.mask_key = settings.PRIVACY_ADMIN_KEY or "default_mask_key_2024"
        self.admin_password = "admin_safety_2024"  # In production, store securely
        
        # Track masked/unmasked state
        self.unmasked_data = {}  # {session_id: {data}}
    
    def mask_pii(self, name: str = None, email: str = None, user_id: str = None) -> Dict[str, Any]:
        """Mask PII data with simple encoding."""
        
        result = {}
        
        if name:
            result["masked_name"] = self._mask_string(name)
            result["original_name"] = name  # Keep for unmasking
        
        if email:
            result["masked_email"] = self._mask_string(email)
            result["original_email"] = email
        
        if user_id:
            result["masked_user_id"] = self._mask_string(user_id)
            result["original_user_id"] = user_id
        
        result["masking_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def unmask_pii(self, masked_data: Dict[str, Any], password: str) -> Dict[str, Any]:
        """Unmask PII data with password verification."""
        
        if password != self.admin_password:
            raise HTTPException(status_code=403, detail="Invalid password")
        
        result = {}
        
        if masked_data.get("original_name"):
            result["unmasked_name"] = masked_data["original_name"]
        
        if masked_data.get("original_email"):
            result["unmasked_email"] = masked_data["original_email"]
        
        if masked_data.get("original_user_id"):
            result["unmasked_user_id"] = masked_data["original_user_id"]
        
        result["unmasking_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    def _mask_string(self, value: str) -> str:
        """Simple string masking."""
        # Create a simple hash-based mask
        hash_obj = hashlib.md5((value + self.mask_key).encode())
        hash_hex = hash_obj.hexdigest()[:8]
        
        # Create masked format: TYPE_HASH
        if "@" in value:
            return f"EMAIL_{hash_hex}"
        elif " " in value:
            return f"NAME_{hash_hex}"
        else:
            return f"ID_{hash_hex}"
    
    def export_data(self, data: Dict[str, Any], password: str, reason: str) -> Dict[str, Any]:
        """Export data with password protection."""
        
        if password != self.admin_password:
            raise HTTPException(status_code=403, detail="Invalid export password")
        
        # Log export for audit
        logger.info(f"Data export requested: {reason}")
        
        return {
            "exported_data": data,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "export_reason": reason,
            "exported_by": "admin"
        }

# Global masker instance
simple_masker = SimpleMasker()

@router.post("/api/privacy/mask")
async def mask_pii_data(request: MaskingRequest) -> Dict[str, Any]:
    """Mask PII data for privacy protection."""
    try:
        result = simple_masker.mask_pii(
            name=request.name,
            email=request.email,
            user_id=request.user_id
        )
        return result
        
    except Exception as e:
        logger.error(f"PII masking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Masking failed: {str(e)}")

@router.post("/api/privacy/unmask")
async def unmask_pii_data(request: UnmaskingRequest) -> Dict[str, Any]:
    """Unmask PII data with password verification."""
    try:
        masked_data = {
            "original_name": request.masked_name,
            "original_email": request.masked_email,
            "original_user_id": request.masked_user_id
        }
        
        result = simple_masker.unmask_pii(masked_data, request.password)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PII unmasking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Unmasking failed: {str(e)}")

@router.post("/api/privacy/export")
async def export_data(request: ExportRequest) -> Dict[str, Any]:
    """Export data with password protection."""
    try:
        result = simple_masker.export_data(request.data, request.password, request.export_reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/api/privacy/status")
async def get_privacy_status() -> Dict[str, Any]:
    """Get privacy masking system status."""
    return {
        "status": "operational",
        "masking_enabled": True,
        "password_protected": True,
        "features": [
            "Simple PII masking",
            "Password-protected unmasking",
            "Password-protected exports"
        ],
        "message": "Simple privacy masking system is operational"
    }
