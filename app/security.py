"""
Security hardening for 7taps Analytics.

This module provides input validation, rate limiting, security headers,
and vulnerability scanning for production security.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger, security_logger

logger = get_logger("security")


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
            "api": {"requests": 1000, "window": 60},  # 1000 API requests per minute
            "auth": {"requests": 5, "window": 300},  # 5 auth attempts per 5 minutes
            "webhook": {
                "requests": 100,
                "window": 60,
            },  # 100 webhook requests per minute
        }

    def is_allowed(self, identifier: str, limit_type: str = "default") -> bool:
        """Check if request is allowed based on rate limits."""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits["default"])

        # Clean old requests
        window_start = now - limit_config["window"]
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit_config["requests"]:
            security_logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                limit_type=limit_type,
                requests=len(self.requests[identifier]),
                limit=limit_config["requests"],
            )
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True

    def get_remaining_requests(
        self, identifier: str, limit_type: str = "default"
    ) -> int:
        """Get remaining requests for an identifier."""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits["default"])

        # Clean old requests
        window_start = now - limit_config["window"]
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
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
        self.secret_key = secret_key.encode("utf-8")

    def validate_signature(
        self, payload: str, signature: str, algorithm: str = "sha256"
    ) -> bool:
        """Validate webhook signature."""
        try:
            if algorithm == "sha256":
                expected_signature = hmac.new(
                    self.secret_key, payload.encode("utf-8"), hashlib.sha256
                ).hexdigest()
            elif algorithm == "sha1":
                expected_signature = hmac.new(
                    self.secret_key, payload.encode("utf-8"), hashlib.sha1
                ).hexdigest()
            else:
                security_logger.error(
                    "Unsupported signature algorithm", algorithm=algorithm
                )
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
                    self.secret_key, payload.encode("utf-8"), hashlib.sha256
                ).hexdigest()
            elif algorithm == "sha1":
                return hmac.new(
                    self.secret_key, payload.encode("utf-8"), hashlib.sha1
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
                ],
            }

            for vuln_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, data, re.IGNORECASE):
                        vulnerabilities.append(
                            {
                                "type": vuln_type,
                                "pattern": pattern,
                                "input": data,
                                "severity": (
                                    "high"
                                    if vuln_type
                                    in ["sql_injection", "command_injection"]
                                    else "medium"
                                ),
                            }
                        )

        return vulnerabilities

    def scan_headers(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scan HTTP headers for security issues."""
        vulnerabilities = []

        # Check for missing security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
        ]

        for header in required_headers:
            if header not in headers:
                vulnerabilities.append(
                    {
                        "type": "missing_security_header",
                        "header": header,
                        "severity": "medium",
                    }
                )

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
