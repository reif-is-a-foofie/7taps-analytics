"""
Gmail OAuth Service

Handles Gmail OAuth authentication and email sending via Gmail API.
Much easier than SMTP - user just logs in with Google!
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import bigquery

from app.config.gcp_config import gcp_config
from app.logging_config import get_logger

logger = get_logger("gmail_oauth")

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# OAuth2 client configuration
# These should be set in GCP Secret Manager or environment variables
CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/settings/gmail/callback")


class GmailOAuthService:
    """Manages Gmail OAuth authentication and email sending."""
    
    def __init__(self):
        try:
            self.client = gcp_config.bigquery_client
            self.dataset_id = gcp_config.bigquery_dataset
            self.project_id = gcp_config.project_id
            self.table_id = "gmail_oauth_tokens"
            self._enabled = True
        except Exception as e:
            logger.warning(f"BigQuery not available, Gmail OAuth disabled: {e}")
            self.client = None
            self.dataset_id = None
            self.project_id = None
            self.table_id = "gmail_oauth_tokens"
            self._enabled = False
    
    def ensure_table_exists(self) -> bool:
        """Ensure the gmail_oauth_tokens table exists."""
        try:
            from app.config.bigquery_schema import get_bigquery_schema
            schema = get_bigquery_schema()
            return schema.create_table_if_not_exists(self.table_id, schema.get_gmail_oauth_table_schema())
        except Exception as e:
            logger.error(f"Failed to ensure gmail_oauth_tokens table exists: {e}")
            return False
    
    def get_authorization_url(self, request_url: str) -> Dict[str, Any]:
        """Generate OAuth authorization URL."""
        if not CLIENT_ID or not CLIENT_SECRET:
            return {
                "success": False,
                "error": "Gmail OAuth not configured. Please set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET"
            }
        
        # Build redirect URI from request
        if "localhost" in request_url or "127.0.0.1" in request_url:
            redirect_uri = "http://localhost:8000/api/settings/gmail/callback"
        else:
            # Extract host from request URL
            from urllib.parse import urlparse
            parsed = urlparse(request_url)
            redirect_uri = f"{parsed.scheme}://{parsed.netloc}/api/settings/gmail/callback"
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return {
            "success": True,
            "authorization_url": authorization_url,
            "state": state,
            "redirect_uri": redirect_uri
        }
    
    async def handle_callback(self, code: str, state: str, redirect_uri: str) -> Dict[str, Any]:
        """Handle OAuth callback and store credentials."""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=SCOPES
            )
            flow.redirect_uri = redirect_uri
            
            # Exchange code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user email
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile.get('emailAddress', 'unknown')
            
            # Store credentials
            await self._store_credentials(user_email, credentials)
            
            return {
                "success": True,
                "email": user_email,
                "message": "Gmail connected successfully!"
            }
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth callback: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _store_credentials(self, email: str, credentials: Credentials) -> bool:
        """Store OAuth credentials in BigQuery."""
        if not self._enabled:
            logger.warning("BigQuery not available, cannot store credentials")
            return False
        
        try:
            if not self.ensure_table_exists():
                return False
            
            token_id = f"gmail_{email}"
            now = datetime.now(timezone.utc)
            
            row = {
                "token_id": token_id,
                "email": email,
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": json.dumps(credentials.scopes),
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # Delete existing token for this email
            delete_query = f"""
            DELETE FROM `{self.dataset_id}.{self.table_id}`
            WHERE token_id = @token_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("token_id", "STRING", token_id)
                ]
            )
            self.client.query(delete_query, job_config=job_config).result()
            
            # Insert new token
            table_ref = self.client.dataset(self.dataset_id).table(self.table_id)
            table = self.client.get_table(table_ref)
            errors = self.client.insert_rows_json(table, [row])
            
            if errors:
                logger.error(f"Failed to store Gmail credentials: {errors}")
                return False
            
            logger.info(f"Stored Gmail OAuth credentials for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing Gmail credentials: {e}")
            return False
    
    async def get_credentials(self, email: Optional[str] = None) -> Optional[Credentials]:
        """Get stored OAuth credentials."""
        if not self._enabled:
            return None
        
        try:
            if not self.ensure_table_exists():
                return None
            
            query = f"""
            SELECT 
                email, token, refresh_token, token_uri, client_id, client_secret,
                scopes, expiry
            FROM `{self.dataset_id}.{self.table_id}`
            ORDER BY updated_at DESC
            LIMIT 1
            """
            
            if email:
                query = f"""
                SELECT 
                    email, token, refresh_token, token_uri, client_id, client_secret,
                    scopes, expiry
                FROM `{self.dataset_id}.{self.table_id}`
                WHERE email = @email
                ORDER BY updated_at DESC
                LIMIT 1
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("email", "STRING", email)
                    ]
                )
                results = list(self.client.query(query, job_config=job_config).result())
            else:
                results = list(self.client.query(query).result())
            
            if not results:
                return None
            
            row = results[0]
            
            # Reconstruct credentials
            credentials = Credentials(
                token=row.token,
                refresh_token=row.refresh_token,
                token_uri=row.token_uri or "https://oauth2.googleapis.com/token",
                client_id=row.client_id or CLIENT_ID,
                client_secret=row.client_secret or CLIENT_SECRET,
                scopes=json.loads(row.scopes) if row.scopes else SCOPES
            )
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                await self._store_credentials(row.email, credentials)
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting Gmail credentials: {e}")
            return None
    
    async def send_email(
        self,
        to_emails: list,
        subject: str,
        body: str,
        sender_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using Gmail API."""
        try:
            credentials = await self.get_credentials(sender_email)
            if not credentials:
                return {
                    "success": False,
                    "error": "Gmail not connected. Please connect your Gmail account first."
                }
            
            service = build('gmail', 'v1', credentials=credentials)
            
            # Create message
            message = self._create_message(
                to_emails,
                subject,
                body,
                sender_email or 'me'
            )
            
            # Send message
            sent_message = service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent via Gmail API: {sent_message.get('id')}")
            
            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "message": "Email sent successfully"
            }
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {
                "success": False,
                "error": f"Gmail API error: {e.content.decode() if hasattr(e, 'content') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to send email via Gmail: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_message(self, to_emails: list, subject: str, body: str, sender: str) -> Dict[str, str]:
        """Create a message for Gmail API."""
        message = f"To: {', '.join(to_emails)}\r\n"
        message += f"Subject: {subject}\r\n"
        message += "Content-Type: text/plain; charset=utf-8\r\n"
        message += "\r\n"
        message += body
        
        return {
            'raw': base64.urlsafe_b64encode(message.encode('utf-8')).decode('utf-8')
        }
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get Gmail connection status."""
        credentials = await self.get_credentials()
        
        if not credentials:
            return {
                "connected": False,
                "email": None,
                "error": "Gmail not connected"
            }
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress')
            
            return {
                "connected": True,
                "email": email,
                "scopes": credentials.scopes
            }
        except Exception as e:
            return {
                "connected": False,
                "email": None,
                "error": str(e)
            }


# Global instance
gmail_oauth_service = GmailOAuthService()

