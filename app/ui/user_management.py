"""
User Access Management for Learning Locker.

This module provides user management interface for Learning Locker access control,
including role management, access level configuration, and permission-based UI elements.
"""

from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import httpx
import json
from datetime import datetime, timedelta
import os
import hashlib
import secrets

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("user_management")
templates = Jinja2Templates(directory="app/templates")

class UserManager:
    """User management for Learning Locker access control."""
    
    def __init__(self):
        self.api_base = os.getenv("API_BASE_URL", "") + "/api"
        
        # Mock user database (in production, this would be a real database)
        self.users = {
            "admin@7taps.com": {
                "id": "user-001",
                "email": "admin@7taps.com",
                "name": "System Administrator",
                "role": "admin",
                "permissions": ["read", "write", "delete", "export", "sync", "manage_users"],
                "created_at": "2025-01-01T00:00:00Z",
                "last_login": "2025-01-05T15:30:00Z",
                "status": "active"
            },
            "analyst@7taps.com": {
                "id": "user-002",
                "email": "analyst@7taps.com",
                "name": "Data Analyst",
                "role": "analyst",
                "permissions": ["read", "export"],
                "created_at": "2025-01-02T00:00:00Z",
                "last_login": "2025-01-05T14:20:00Z",
                "status": "active"
            },
            "viewer@7taps.com": {
                "id": "user-003",
                "email": "viewer@7taps.com",
                "name": "Report Viewer",
                "role": "viewer",
                "permissions": ["read"],
                "created_at": "2025-01-03T00:00:00Z",
                "last_login": "2025-01-05T12:15:00Z",
                "status": "active"
            }
        }
        
        self.roles = {
            "admin": {
                "name": "Administrator",
                "description": "Full system access including user management",
                "permissions": ["read", "write", "delete", "export", "sync", "manage_users"],
                "color": "#e74c3c"
            },
            "analyst": {
                "name": "Data Analyst",
                "description": "Can read data and export reports",
                "permissions": ["read", "export"],
                "color": "#3498db"
            },
            "viewer": {
                "name": "Viewer",
                "description": "Read-only access to reports and dashboards",
                "permissions": ["read"],
                "color": "#27ae60"
            }
        }
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return self.users.get(email)
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        return list(self.users.values())
    
    def create_user(self, email: str, name: str, role: str) -> Dict[str, Any]:
        """Create a new user."""
        if email in self.users:
            raise ValueError("User already exists")
        
        if role not in self.roles:
            raise ValueError("Invalid role")
        
        user_id = f"user-{len(self.users) + 1:03d}"
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "permissions": self.roles[role]["permissions"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "status": "active"
        }
        
        self.users[email] = user
        logger.info(f"Created user: {email} with role: {role}")
        return user
    
    def update_user(self, email: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information."""
        if email not in self.users:
            raise ValueError("User not found")
        
        user = self.users[email]
        
        # Update allowed fields
        if "name" in updates:
            user["name"] = updates["name"]
        if "role" in updates:
            if updates["role"] not in self.roles:
                raise ValueError("Invalid role")
            user["role"] = updates["role"]
            user["permissions"] = self.roles[updates["role"]]["permissions"]
        if "status" in updates:
            user["status"] = updates["status"]
        
        logger.info(f"Updated user: {email}")
        return user
    
    def delete_user(self, email: str) -> bool:
        """Delete a user."""
        if email not in self.users:
            raise ValueError("User not found")
        
        del self.users[email]
        logger.info(f"Deleted user: {email}")
        return True
    
    def get_user_permissions(self, email: str) -> List[str]:
        """Get user permissions."""
        user = self.get_user_by_email(email)
        return user["permissions"] if user else []
    
    def has_permission(self, email: str, permission: str) -> bool:
        """Check if user has specific permission."""
        permissions = self.get_user_permissions(email)
        return permission in permissions
    
    def get_roles(self) -> Dict[str, Any]:
        """Get all available roles."""
        return self.roles
    
    def get_user_activity(self) -> List[Dict[str, Any]]:
        """Get user activity data."""
        activity = []
        for user in self.users.values():
            if user["last_login"]:
                activity.append({
                    "user_id": user["id"],
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "last_login": user["last_login"],
                    "status": user["status"]
                })
        
        return sorted(activity, key=lambda x: x["last_login"], reverse=True)
    
    def get_access_logs(self) -> List[Dict[str, Any]]:
        """Get access logs."""
        # Mock access logs
        logs = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": "admin@7taps.com",
                "action": "login",
                "ip": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
                "user": "analyst@7taps.com",
                "action": "export_data",
                "ip": "192.168.1.101",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "user": "viewer@7taps.com",
                "action": "view_dashboard",
                "ip": "192.168.1.102",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
        ]
        
        return logs

# Global user manager instance
user_manager = UserManager()

@router.get("/user-management", response_class=HTMLResponse)
async def user_management_page(request: Request):
    """User management main page."""
    try:
        users = user_manager.get_all_users()
        roles = user_manager.get_roles()
        activity = user_manager.get_user_activity()
        access_logs = user_manager.get_access_logs()
        
        context = {
            "request": request,
            "users": users,
            "roles": roles,
            "activity": activity,
            "access_logs": access_logs,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("user_management.html", context)
        
    except Exception as e:
        logger.error("Failed to render user management page", error=e)
        raise HTTPException(status_code=500, detail=f"User management error: {str(e)}")

@router.get("/api/users")
async def get_users_api():
    """API endpoint for getting all users."""
    try:
        users = user_manager.get_all_users()
        return {"users": users}
    except Exception as e:
        logger.error("Failed to get users via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.post("/api/users")
async def create_user_api(email: str = Form(...), name: str = Form(...), role: str = Form(...)):
    """API endpoint for creating a new user."""
    try:
        user = user_manager.create_user(email, name, role)
        return {"user": user, "message": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create user via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.put("/api/users/{email}")
async def update_user_api(email: str, updates: Dict[str, Any]):
    """API endpoint for updating a user."""
    try:
        user = user_manager.update_user(email, updates)
        return {"user": user, "message": "User updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update user via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.delete("/api/users/{email}")
async def delete_user_api(email: str):
    """API endpoint for deleting a user."""
    try:
        success = user_manager.delete_user(email)
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete user via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/users/{email}/permissions")
async def get_user_permissions_api(email: str):
    """API endpoint for getting user permissions."""
    try:
        permissions = user_manager.get_user_permissions(email)
        return {"email": email, "permissions": permissions}
    except Exception as e:
        logger.error("Failed to get user permissions via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/roles")
async def get_roles_api():
    """API endpoint for getting all roles."""
    try:
        roles = user_manager.get_roles()
        return {"roles": roles}
    except Exception as e:
        logger.error("Failed to get roles via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/users/activity")
async def get_user_activity_api():
    """API endpoint for getting user activity."""
    try:
        activity = user_manager.get_user_activity()
        return {"activity": activity}
    except Exception as e:
        logger.error("Failed to get user activity via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.get("/api/access-logs")
async def get_access_logs_api():
    """API endpoint for getting access logs."""
    try:
        logs = user_manager.get_access_logs()
        return {"logs": logs}
    except Exception as e:
        logger.error("Failed to get access logs via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.post("/api/auth/login")
async def login_api(email: str = Form(...), password: str = Form(...)):
    """API endpoint for user login."""
    try:
        user = user_manager.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Mock password verification (in production, use proper hashing)
        if password == "password123":  # Mock password
            # Update last login
            user["last_login"] = datetime.now(timezone.utc).isoformat()
            
            return {
                "user": user,
                "message": "Login successful",
                "token": f"mock_token_{secrets.token_hex(16)}"
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logger.error("Failed to login via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

@router.post("/api/auth/logout")
async def logout_api():
    """API endpoint for user logout."""
    try:
        return {"message": "Logout successful"}
    except Exception as e:
        logger.error("Failed to logout via API", error=e)
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}") 