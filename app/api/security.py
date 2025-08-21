"""
Security Monitoring API

This module provides endpoints for security monitoring, environment validation,
and secrets management.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from app.security import (
    validate_environment_security, 
    secrets_manager, 
    log_security_event,
    check_for_suspicious_activity
)
import os

router = APIRouter()

class SecurityStatus(BaseModel):
    """Security status response model"""
    environment_valid: bool
    secrets_status: Dict[str, Any]
    recommendations: List[str]
    suspicious_activity: Dict[str, Any]
    timestamp: str

class SecretRotationRequest(BaseModel):
    """Secret rotation request model"""
    secret_name: str
    new_value: str

@router.get("/api/security/status", 
    response_model=SecurityStatus,
    summary="Get security status",
    description="Get comprehensive security status including environment validation and secrets status"
)
async def get_security_status():
    """Get comprehensive security status"""
    try:
        # Validate environment security
        env_status = validate_environment_security()
        
        # Check for suspicious activity
        suspicious_status = check_for_suspicious_activity()
        
        # Log security check
        log_security_event("security_status_check", {
            "environment_valid": env_status["environment_valid"],
            "secrets_count": len(env_status["secrets_status"])
        })
        
        return SecurityStatus(
            environment_valid=env_status["environment_valid"],
            secrets_status=env_status["secrets_status"],
            recommendations=env_status["recommendations"],
            suspicious_activity=suspicious_status,
            timestamp=env_status["timestamp"]
        )
        
    except Exception as e:
        log_security_event("security_status_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Security status check failed: {str(e)}")

@router.post("/api/security/rotate-secret",
    summary="Rotate a secret",
    description="Request rotation of a specific secret (requires proper implementation for production)"
)
async def rotate_secret(request: SecretRotationRequest):
    """Request secret rotation"""
    try:
        # Log rotation attempt
        log_security_event("secret_rotation_requested", {
            "secret_name": request.secret_name,
            "new_value_length": len(request.new_value)
        })
        
        success = secrets_manager.rotate_secret(request.secret_name, request.new_value)
        
        if success:
            return {
                "success": True,
                "message": f"Secret rotation requested for {request.secret_name}",
                "note": "In production, this would update the environment variable"
            }
        else:
            raise HTTPException(status_code=400, detail="Secret rotation failed")
            
    except Exception as e:
        log_security_event("secret_rotation_error", {
            "secret_name": request.secret_name,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Secret rotation failed: {str(e)}")

@router.get("/api/security/validate-environment",
    summary="Validate environment",
    description="Validate that all required environment variables are properly set"
)
async def validate_environment():
    """Validate environment configuration"""
    try:
        status = validate_environment_security()
        
        log_security_event("environment_validation", {
            "valid": status["environment_valid"],
            "secrets_checked": len(status["secrets_status"])
        })
        
        return status
        
    except Exception as e:
        log_security_event("environment_validation_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Environment validation failed: {str(e)}")

@router.get("/api/security/check-rotation",
    summary="Check rotation status",
    description="Check which secrets need rotation"
)
async def check_rotation_status():
    """Check which secrets need rotation"""
    try:
        rotation_status = {}
        
        for secret_name in secrets_manager.secrets_config.keys():
            rotation_status[secret_name] = {
                "needs_rotation": secrets_manager.check_key_rotation_needed(secret_name),
                "last_rotation": secrets_manager.secrets_config[secret_name].last_rotation
            }
        
        log_security_event("rotation_status_check", {
            "secrets_checked": len(rotation_status)
        })
        
        return {
            "rotation_status": rotation_status,
            "timestamp": secrets_manager.secrets_config[list(rotation_status.keys())[0]].last_rotation.isoformat() if rotation_status else None
        }
        
    except Exception as e:
        log_security_event("rotation_status_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Rotation status check failed: {str(e)}")
