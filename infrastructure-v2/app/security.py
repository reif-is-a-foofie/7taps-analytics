"""
Security hardening for 7taps Analytics.

This module provides input validation, rate limiting, security headers,
and vulnerability scanning for production security.
"""

import re
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging

from app.logging_config import get_logger, security_logger

logger = get_logger("security")

"""
Secure Secrets Management System

This module provides secure handling of API keys and sensitive configuration
with validation, rotation capabilities, and security monitoring.
"""

import os
import logging
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not available

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecretConfig:
    """Configuration for a secret"""
    name: str
    required: bool = True
    min_length: int = 20
    rotation_days: int = 90
    last_rotation: Optional[datetime] = None

class SecretsManager:
    """Secure secrets management with validation and rotation"""
    
    def __init__(self):
        self.secrets_config = {
            'OPENAI_API_KEY': SecretConfig(
                name='OPENAI_API_KEY',
                required=True,
                min_length=20,
                rotation_days=90
            ),
            'DATABASE_URL': SecretConfig(
                name='DATABASE_URL',
                required=True,
                min_length=10,
                rotation_days=365
            ),
            'REDIS_URL': SecretConfig(
                name='REDIS_URL',
                required=False,
                min_length=10,
                rotation_days=365
            )
        }
        self._validate_environment()
    
    def _validate_environment(self) -> None:
        """Validate all required environment variables are present and secure"""
        missing_secrets = []
        weak_secrets = []
        
        for secret_name, config in self.secrets_config.items():
            value = os.getenv(secret_name)
            
            if config.required and not value:
                missing_secrets.append(secret_name)
            elif value and len(value) < config.min_length:
                weak_secrets.append(secret_name)
        
        if missing_secrets:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_secrets)}")
        
        if weak_secrets:
            logger.warning(f"Weak secrets detected (too short): {', '.join(weak_secrets)}")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret value with validation"""
        if secret_name not in self.secrets_config:
            logger.warning(f"Accessing unconfigured secret: {secret_name}")
            return os.getenv(secret_name)
        
        value = os.getenv(secret_name)
        config = self.secrets_config[secret_name]
        
        if config.required and not value:
            raise ValueError(f"Required secret {secret_name} is not set")
        
        if value and len(value) < config.min_length:
            logger.warning(f"Secret {secret_name} is shorter than recommended minimum length")
        
        return value
    
    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate OpenAI API key format"""
        if not api_key:
            return False
        
        # OpenAI API keys start with 'sk-' and are typically 51 characters
        if not api_key.startswith('sk-'):
            return False
        
        if len(api_key) < 20:
            return False
        
        return True
    
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key with validation"""
        api_key = self.get_secret('OPENAI_API_KEY')
        
        if not self.validate_api_key_format(api_key):
            raise ValueError("Invalid OpenAI API key format")
        
        return api_key
    
    def generate_key_hash(self, api_key: str) -> str:
        """Generate a hash of the API key for logging/monitoring"""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def log_key_usage(self, secret_name: str, operation: str) -> None:
        """Log secret usage for monitoring (without exposing the actual key)"""
        key_hash = self.generate_key_hash(self.get_secret(secret_name) or "")
        logger.info(f"Secret usage: {secret_name} ({key_hash}) - {operation}")
    
    def check_key_rotation_needed(self, secret_name: str) -> bool:
        """Check if a key needs rotation based on age"""
        config = self.secrets_config.get(secret_name)
        if not config or not config.last_rotation:
            return True
        
        days_since_rotation = (datetime.now() - config.last_rotation).days
        return days_since_rotation >= config.rotation_days
    
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate a secret (requires manual implementation for production)"""
        if secret_name not in self.secrets_config:
            logger.error(f"Cannot rotate unconfigured secret: {secret_name}")
            return False
        
        config = self.secrets_config[secret_name]
        
        if len(new_value) < config.min_length:
            logger.error(f"New secret value too short for {secret_name}")
            return False
        
        # In production, this would update the environment variable
        # For now, we just log the rotation
        logger.info(f"Secret rotation requested for {secret_name}")
        config.last_rotation = datetime.now()
        
        return True

# Global secrets manager instance (lazy-loaded)
_secrets_manager = None

def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance (lazy-loaded)."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

# For backward compatibility
secrets_manager = get_secrets_manager

def get_openai_client():
    """Get OpenAI client with secure API key handling"""
    try:
        import openai
        sm = get_secrets_manager()
        api_key = sm.get_openai_api_key()
        sm.log_key_usage('OPENAI_API_KEY', 'OpenAI client creation')
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        raise

def validate_environment_security() -> Dict[str, Any]:
    """Validate environment security and return status report"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'environment_valid': True,
        'secrets_status': {},
        'recommendations': []
    }
    
    try:
        sm = get_secrets_manager()
        for secret_name, config in sm.secrets_config.items():
            secret_status = {
                'present': bool(os.getenv(secret_name)),
                'length': len(os.getenv(secret_name) or ""),
                'meets_min_length': len(os.getenv(secret_name) or "") >= config.min_length,
                'rotation_needed': sm.check_key_rotation_needed(secret_name)
            }
            
            status['secrets_status'][secret_name] = secret_status
            
            if not secret_status['present'] and config.required:
                status['environment_valid'] = False
                status['recommendations'].append(f"Set required secret: {secret_name}")
            
            if secret_status['rotation_needed']:
                status['recommendations'].append(f"Rotate secret: {secret_name}")
        
        return status
    
    except Exception as e:
        status['environment_valid'] = False
        status['error'] = str(e)
        return status

# Security monitoring
def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log security events for monitoring"""
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'details': details
    }
    logger.info(f"Security event: {json.dumps(event)}")

def check_for_suspicious_activity() -> Dict[str, Any]:
    """Check for suspicious activity patterns"""
    # This would integrate with your monitoring system
    # For now, return basic status
    return {
        'timestamp': datetime.now().isoformat(),
        'suspicious_activity_detected': False,
        'checks_performed': ['api_key_usage', 'environment_validation']
    }

class InputValidator:
    """Validate and sanitize input data."""
    
    def __init__(self):
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
            r"(--|#|/\*|\*/)",
            r"(\b(script|javascript|vbscript|expression)\b)",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]
        
        # Path traversal patterns
        self.path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]
    
    def validate_string(self, value: str, max_length: int = 1000) -> bool:
        """Validate string input."""
        if not isinstance(value, str):
            return False
        
        if len(value) > max_length:
            return False
        
        # Check for SQL injection
        for pattern in self.sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_logger.warning("SQL injection attempt detected", input=value)
                return False
        
        # Check for XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_logger.warning("XSS attempt detected", input=value)
                return False
        
        # Check for path traversal
        for pattern in self.path_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_logger.warning("Path traversal attempt detected", input=value)
                return False
        
        return True
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[<>\"']", "", value)
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"vbscript:", "", sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def validate_json(self, data: Any) -> bool:
        """Validate JSON data structure."""
        if not isinstance(data, dict):
            return False
        
        # Check for nested objects that might be too deep
        def check_depth(obj, depth=0):
            if depth > 10:  # Max depth of 10
                return False
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if not self.validate_string(str(key)):
                        return False
                    if not check_depth(value, depth + 1):
                        return False
            elif isinstance(obj, list):
                for item in obj:
                    if not check_depth(item, depth + 1):
                        return False
            
            return True
        
        return check_depth(data)

class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "default": {"requests": 100, "window": 60},  # 100 requests per minute
            "api": {"requests": 1000, "window": 60},     # 1000 API requests per minute
            "auth": {"requests": 5, "window": 300},      # 5 auth attempts per 5 minutes
            "webhook": {"requests": 100, "window": 60},  # 100 webhook requests per minute
        }
    
    def is_allowed(self, identifier: str, limit_type: str = "default") -> bool:
        """Check if request is allowed based on rate limits."""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits["default"])
        
        # Clean old requests
        window_start = now - limit_config["window"]
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit_config["requests"]:
            security_logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                limit_type=limit_type,
                requests=len(self.requests[identifier]),
                limit=limit_config["requests"]
            )
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, limit_type: str = "default") -> int:
        """Get remaining requests for an identifier."""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits["default"])
        
        # Clean old requests
        window_start = now - limit_config["window"]
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        return max(0, limit_config["requests"] - len(self.requests[identifier]))

class SecurityHeaders:
    """Security headers configuration."""
    
    def __init__(self):
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Get security headers."""
        return self.headers.copy()
    
    def add_header(self, name: str, value: str):
        """Add a custom security header."""
        self.headers[name] = value

class WebhookSignatureValidator:
    """Validate webhook signatures for security."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def validate_signature(self, payload: str, signature: str, algorithm: str = "sha256") -> bool:
        """Validate webhook signature."""
        try:
            if algorithm == "sha256":
                expected_signature = hmac.new(
                    self.secret_key,
                    payload.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
            elif algorithm == "sha1":
                expected_signature = hmac.new(
                    self.secret_key,
                    payload.encode('utf-8'),
                    hashlib.sha1
                ).hexdigest()
            else:
                security_logger.error("Unsupported signature algorithm", algorithm=algorithm)
                return False
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            security_logger.error("Signature validation failed", error=e)
            return False
    
    def generate_signature(self, payload: str, algorithm: str = "sha256") -> str:
        """Generate signature for payload."""
        try:
            if algorithm == "sha256":
                return hmac.new(
                    self.secret_key,
                    payload.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
            elif algorithm == "sha1":
                return hmac.new(
                    self.secret_key,
                    payload.encode('utf-8'),
                    hashlib.sha1
                ).hexdigest()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
        except Exception as e:
            security_logger.error("Signature generation failed", error=e)
            raise

class VulnerabilityScanner:
    """Basic vulnerability scanning."""
    
    def __init__(self):
        self.scan_results = []
    
    def scan_input(self, data: Any) -> List[Dict[str, Any]]:
        """Scan input data for potential vulnerabilities."""
        vulnerabilities = []
        
        if isinstance(data, str):
            # Check for common attack patterns
            patterns = {
                "sql_injection": [
                    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                    r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
                ],
                "xss": [
                    r"<script[^>]*>",
                    r"javascript:",
                    r"on\w+\s*=",
                ],
                "path_traversal": [
                    r"\.\./",
                    r"\.\.\\",
                ],
                "command_injection": [
                    r"[;&|`$()]",
                    r"\b(cat|ls|rm|wget|curl|nc|telnet)\b",
                ]
            }
            
            for vuln_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, data, re.IGNORECASE):
                        vulnerabilities.append({
                            "type": vuln_type,
                            "pattern": pattern,
                            "input": data,
                            "severity": "high" if vuln_type in ["sql_injection", "command_injection"] else "medium"
                        })
        
        return vulnerabilities
    
    def scan_headers(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scan HTTP headers for security issues."""
        vulnerabilities = []
        
        # Check for missing security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for header in required_headers:
            if header not in headers:
                vulnerabilities.append({
                    "type": "missing_security_header",
                    "header": header,
                    "severity": "medium"
                })
        
        return vulnerabilities

# Global security instances
input_validator = InputValidator()
rate_limiter = RateLimiter()
security_headers = SecurityHeaders()
vulnerability_scanner = VulnerabilityScanner()

# Initialize webhook validator with secret key
webhook_secret = "your-webhook-secret-key"  # Should be set via environment variable
webhook_validator = WebhookSignatureValidator(webhook_secret)

def validate_api_input(data: Any) -> bool:
    """Validate API input data."""
    if isinstance(data, dict):
        return input_validator.validate_json(data)
    elif isinstance(data, str):
        return input_validator.validate_string(data)
    else:
        return False

def sanitize_api_input(data: Any) -> Any:
    """Sanitize API input data."""
    if isinstance(data, str):
        return input_validator.sanitize_string(data)
    elif isinstance(data, dict):
        return {sanitize_api_input(k): sanitize_api_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_api_input(item) for item in data]
    else:
        return data

def check_rate_limit(identifier: str, limit_type: str = "api") -> bool:
    """Check rate limit for an identifier."""
    return rate_limiter.is_allowed(identifier, limit_type)

def get_security_headers() -> Dict[str, str]:
    """Get security headers for responses."""
    return security_headers.get_headers()

def scan_for_vulnerabilities(data: Any) -> List[Dict[str, Any]]:
    """Scan data for potential vulnerabilities."""
    return vulnerability_scanner.scan_input(data) 