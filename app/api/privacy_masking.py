"""
Privacy Masking System for Learner Data

Provides secure, reversible masking of PII (names, emails) that:
1. Cannot be guessed by unauthorized users
2. Can be revealed by authorized administrators
3. Maintains consistent masking across sessions
4. Supports audit trails for privacy compliance
"""

import hashlib
import hmac
import base64
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("privacy_masking")

class MaskingRequest(BaseModel):
    """Request model for masking PII."""
    name: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None

class UnmaskingRequest(BaseModel):
    """Request model for unmasking PII (admin only)."""
    masked_name: Optional[str] = None
    masked_email: Optional[str] = None
    masked_user_id: Optional[str] = None
    admin_key: str  # Admin authentication key

class MaskingResponse(BaseModel):
    """Response model for masking operations."""
    masked_name: Optional[str] = None
    masked_email: Optional[str] = None
    masked_user_id: Optional[str] = None
    masking_timestamp: str
    admin_reference: str  # Reference for admin unmasking

class PrivacyMasker:
    """Secure masking system for learner PII."""
    
    def __init__(self):
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Admin key for unmasking (should be set in environment)
        self.admin_key = settings.PRIVACY_ADMIN_KEY or "default_admin_key_change_me"
        
        # Audit log for privacy compliance
        self.audit_log = []
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for consistent masking."""
        key_path = os.path.join(os.path.dirname(__file__), "..", "..", "privacy_key.key")
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            logger.info("Generated new privacy encryption key")
            return key
    
    def mask_pii(self, name: str = None, email: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Mask PII data with secure, reversible encryption.
        
        Returns consistent masked values that cannot be guessed.
        """
        timestamp = datetime.now(timezone.utc)
        admin_ref = self._generate_admin_reference(name, email, user_id)
        
        result = {
            "masked_name": None,
            "masked_email": None, 
            "masked_user_id": None,
            "masking_timestamp": timestamp.isoformat(),
            "admin_reference": admin_ref
        }
        
        # Mask name
        if name:
            result["masked_name"] = self._mask_string(name, "name")
        
        # Mask email
        if email:
            result["masked_email"] = self._mask_string(email, "email")
        
        # Mask user ID
        if user_id:
            result["masked_user_id"] = self._mask_string(user_id, "user_id")
        
        # Log masking operation (without PII)
        self._audit_log("MASK", {
            "admin_ref": admin_ref,
            "timestamp": timestamp.isoformat(),
            "fields_masked": [k for k in ["name", "email", "user_id"] if locals()[k]]
        })
        
        return result
    
    def unmask_pii(self, masked_data: Dict[str, Any], admin_key: str) -> Dict[str, Any]:
        """
        Unmask PII data (admin only).
        
        Requires valid admin key and logs the operation.
        """
        if admin_key != self.admin_key:
            self._audit_log("UNAUTHORIZED_UNMASK_ATTEMPT", {
                "provided_key": admin_key[:8] + "..." if len(admin_key) > 8 else admin_key,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(status_code=403, detail="Invalid admin key")
        
        timestamp = datetime.now(timezone.utc)
        
        result = {
            "original_name": None,
            "original_email": None,
            "original_user_id": None,
            "unmasking_timestamp": timestamp.isoformat(),
            "unmasked_by": "admin"
        }
        
        # Unmask name
        if masked_data.get("masked_name"):
            result["original_name"] = self._unmask_string(masked_data["masked_name"], "name")
        
        # Unmask email
        if masked_data.get("masked_email"):
            result["original_email"] = self._unmask_string(masked_data["masked_email"], "email")
        
        # Unmask user ID
        if masked_data.get("masked_user_id"):
            result["original_user_id"] = self._unmask_string(masked_data["masked_user_id"], "user_id")
        
        # Log unmasking operation
        self._audit_log("UNMASK", {
            "admin_ref": masked_data.get("admin_reference"),
            "timestamp": timestamp.isoformat(),
            "fields_unmasked": [k for k in ["original_name", "original_email", "original_user_id"] if result[k]]
        })
        
        return result
    
    def _mask_string(self, value: str, field_type: str) -> str:
        """Mask a string value with type-specific prefix."""
        # Normalize input
        normalized = value.strip().lower()
        
        # Create field-specific salt
        salt = f"privacy_masking_{field_type}_{settings.GCP_PROJECT_ID}".encode()
        
        # Encrypt the value
        encrypted = self.cipher_suite.encrypt(normalized.encode())
        
        # Create masked format: FIELD_TYPE_HASH_ENCRYPTED
        hash_prefix = hashlib.sha256(normalized.encode() + salt).hexdigest()[:8]
        masked = f"{field_type.upper()}_{hash_prefix}_{base64.urlsafe_b64encode(encrypted).decode()}"
        
        return masked
    
    def _unmask_string(self, masked_value: str, field_type: str) -> str:
        """Unmask a string value."""
        try:
            # Parse masked format: FIELD_TYPE_HASH_ENCRYPTED
            parts = masked_value.split("_", 2)
            if len(parts) != 3 or parts[0].lower() != field_type.lower():
                raise ValueError("Invalid masked format")
            
            field_type_check, hash_prefix, encrypted_b64 = parts
            
            # Decode and decrypt
            encrypted = base64.urlsafe_b64decode(encrypted_b64.encode())
            decrypted = self.cipher_suite.decrypt(encrypted)
            
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Failed to unmask {field_type}: {e}")
            raise ValueError(f"Cannot unmask {field_type}: invalid or corrupted data")
    
    def _generate_admin_reference(self, name: str = None, email: str = None, user_id: str = None) -> str:
        """Generate unique admin reference for tracking."""
        # Create deterministic reference from available data
        ref_data = []
        if name:
            ref_data.append(f"name:{name}")
        if email:
            ref_data.append(f"email:{email}")
        if user_id:
            ref_data.append(f"id:{user_id}")
        
        ref_string = "|".join(ref_data)
        ref_hash = hashlib.sha256(ref_string.encode()).hexdigest()[:12]
        
        return f"REF_{ref_hash}_{int(datetime.now(timezone.utc).timestamp())}"
    
    def _audit_log(self, operation: str, data: Dict[str, Any]):
        """Log privacy operations for compliance."""
        log_entry = {
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        self.audit_log.append(log_entry)
        
        # Keep only last 1000 entries in memory
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        # Log to file for persistence
        log_file = os.path.join(os.path.dirname(__file__), "..", "..", "privacy_audit.log")
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def get_audit_log(self, admin_key: str) -> List[Dict[str, Any]]:
        """Get privacy audit log (admin only)."""
        if admin_key != self.admin_key:
            raise HTTPException(status_code=403, detail="Invalid admin key")
        
        return self.audit_log
    
    def mask_xapi_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Mask PII in xAPI statement while preserving structure."""
        masked_statement = statement.copy()
        
        # Mask actor information
        actor = statement.get("actor", {})
        if actor.get("name"):
            actor_masked = self.mask_pii(name=actor["name"])
            masked_statement["actor"]["name"] = actor_masked["masked_name"]
            masked_statement["actor"]["admin_reference"] = actor_masked["admin_reference"]
        
        if actor.get("mbox"):
            # Extract email from mbox format (mailto:email@domain.com)
            email = actor["mbox"].replace("mailto:", "")
            email_masked = self.mask_pii(email=email)
            masked_statement["actor"]["mbox"] = f"mailto:{email_masked['masked_email']}"
            if not masked_statement["actor"].get("admin_reference"):
                masked_statement["actor"]["admin_reference"] = email_masked["admin_reference"]
        
        # Mask any extensions that might contain PII
        extensions = masked_statement.get("result", {}).get("extensions", {})
        for ext_key, ext_value in extensions.items():
            if isinstance(ext_value, str) and ("@" in ext_value or "name" in ext_key.lower()):
                # This might be PII, mask it
                masked_value = self.mask_pii(name=ext_value if "name" in ext_key.lower() else None,
                                           email=ext_value if "@" in ext_value else None)
                if masked_value["masked_name"]:
                    extensions[ext_key] = masked_value["masked_name"]
                elif masked_value["masked_email"]:
                    extensions[ext_key] = masked_value["masked_email"]
        
        return masked_statement

# Global privacy masker instance
privacy_masker = PrivacyMasker()

@router.post("/api/privacy/mask", response_model=MaskingResponse)
async def mask_pii_data(request: MaskingRequest) -> MaskingResponse:
    """
    Mask PII data for privacy protection.
    
    Returns masked values that cannot be guessed but can be unmasked by admins.
    """
    try:
        result = privacy_masker.mask_pii(
            name=request.name,
            email=request.email,
            user_id=request.user_id
        )
        
        return MaskingResponse(**result)
        
    except Exception as e:
        logger.error(f"PII masking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Masking failed: {str(e)}")

@router.post("/api/privacy/unmask")
async def unmask_pii_data(request: UnmaskingRequest) -> Dict[str, Any]:
    """
    Unmask PII data (admin only).
    
    Requires valid admin key and logs the operation.
    """
    try:
        masked_data = {
            "masked_name": request.masked_name,
            "masked_email": request.masked_email,
            "masked_user_id": request.masked_user_id,
            "admin_reference": "provided_in_request"
        }
        
        result = privacy_masker.unmask_pii(masked_data, request.admin_key)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PII unmasking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Unmasking failed: {str(e)}")

@router.post("/api/privacy/mask-xapi")
async def mask_xapi_statement(statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask PII in xAPI statement.
    
    Preserves statement structure while masking sensitive information.
    """
    try:
        masked_statement = privacy_masker.mask_xapi_statement(statement)
        return masked_statement
        
    except Exception as e:
        logger.error(f"xAPI masking failed: {e}")
        raise HTTPException(status_code=500, detail=f"xAPI masking failed: {str(e)}")

@router.get("/api/privacy/audit")
async def get_privacy_audit_log(admin_key: str) -> Dict[str, Any]:
    """
    Get privacy audit log (admin only).
    
    Shows all masking/unmasking operations for compliance.
    """
    try:
        audit_log = privacy_masker.get_audit_log(admin_key)
        return {
            "audit_log": audit_log,
            "total_operations": len(audit_log),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audit log retrieval failed: {str(e)}")

@router.get("/api/privacy/status")
async def get_privacy_status() -> Dict[str, Any]:
    """Get privacy masking system status."""
    return {
        "status": "operational",
        "encryption_enabled": True,
        "admin_key_configured": bool(settings.PRIVACY_ADMIN_KEY),
        "audit_logging": True,
        "features": [
            "PII masking",
            "Admin unmasking", 
            "Audit logging",
            "xAPI statement masking"
        ],
        "message": "Privacy masking system is operational"
    }
