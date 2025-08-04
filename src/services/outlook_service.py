import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import aiohttp
import msal

from ..models.email import Email, AccountType, EmailStatus, EmailAttachment
from ..utils.exceptions import OutlookServiceException
from ..utils.helpers import (
    extract_email_address, extract_sender_name, generate_email_id,
    html_to_text, extract_text_from_html
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OutlookService:
    GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES = [
        "Mail.Read",
        "Mail.ReadWrite", 
        "User.Read"
    ]

    def __init__(self, client_id: str, client_secret: str, tenant_id: str = "common"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None
        self.token_expires_at = None
        
        # Use PublicClientApplication for device flow (personal accounts)
        # Clear token cache to force fresh authentication with new permissions
        self.public_app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )

    async def authenticate(self, username: str = None):
        try:
            # First try silent authentication
            accounts = self.public_app.get_accounts()
            if accounts:
                result = self.public_app.acquire_token_silent(self.SCOPES, account=accounts[0])
                if result and "access_token" in result:
                    self.access_token = result["access_token"]
                    self.token_expires_at = datetime.now().timestamp() + result.get("expires_in", 3600)
                    logger.info("Outlook service authenticated silently")
                    return
            
            # If silent fails, use device flow
            flow = self.public_app.initiate_device_flow(scopes=self.SCOPES)
            if "user_code" not in flow:
                raise OutlookServiceException("Failed to create device flow")
            
            print(f"\n🔗 Please visit: {flow['verification_uri']}")
            print(f"🔢 Enter code: {flow['user_code']}")
            print("⏳ Waiting for authentication...")
            
            result = self.public_app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.token_expires_at = datetime.now().timestamp() + result.get("expires_in", 3600)
                logger.info("Outlook service authenticated successfully")
            else:
                error = result.get("error_description", "Unknown error")
                raise OutlookServiceException(f"Authentication failed: {error}")
                
        except Exception as e:
            logger.error(f"Outlook authentication failed: {e}")
            raise OutlookServiceException(f"Authentication failed: {e}")

    async def _ensure_token_valid(self):
        if not self.access_token or (self.token_expires_at and datetime.now().timestamp() >= self.token_expires_at):
            accounts = self.public_app.get_accounts()
            if accounts:
                result = self.public_app.acquire_token_silent(self.SCOPES, account=accounts[0])
                if result and "access_token" in result:
                    self.access_token = result["access_token"]
                    self.token_expires_at = datetime.now().timestamp() + result.get("expires_in", 3600)
                else:
                    raise OutlookServiceException("Token refresh failed, re-authentication required")

    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        await self._ensure_token_valid()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.GRAPH_ENDPOINT}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Outlook API error: {response.status} - {error_text}")
                    raise OutlookServiceException(f"API request failed: {response.status} - {error_text}")

    async def get_unread_messages(self, max_results: int = 100) -> List[Dict[str, Any]]:
        try:
            # Only get messages from Inbox folder to avoid spam/junk
            endpoint = f"/me/mailFolders/Inbox/messages?$filter=isRead eq false&$top={max_results}&$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments,internetMessageId"
            
            response = await self._make_request("GET", endpoint)
            messages = response.get("value", [])
            
            logger.info(f"Found {len(messages)} unread messages in Outlook Inbox")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting unread messages from Outlook: {e}")
            raise OutlookServiceException(f"Failed to get unread messages: {e}")

    async def get_message_details(self, message_id: str) -> Optional[Email]:
        try:
            endpoint = f"/me/messages/{message_id}"
            message_data = await self._make_request("GET", endpoint)
            
            return self._parse_message(message_data)
            
        except Exception as e:
            logger.error(f"Error getting message details for {message_id}: {e}")
            return None

    def _parse_message(self, message: Dict[str, Any]) -> Email:
        # Use internetMessageId for uniqueness/deduplication, Graph ID for API operations
        message_id = message.get("internetMessageId", message.get("id", ""))
        graph_id = message.get("id", "")  # Microsoft Graph API ID for operations
        subject = message.get("subject", "No Subject")
        
        from_data = message.get("from", {}).get("emailAddress", {})
        sender_email = from_data.get("address", "")
        sender_name = from_data.get("name", "")
        
        to_recipients = message.get("toRecipients", [])
        recipient = to_recipients[0].get("emailAddress", {}).get("address", "") if to_recipients else ""
        
        received_date_str = message.get("receivedDateTime", "")
        received_date = datetime.fromisoformat(received_date_str.replace('Z', '+00:00')) if received_date_str else datetime.now()
        
        body_data = message.get("body", {})
        content_type = body_data.get("contentType", "text")
        content = body_data.get("content", "")
        
        content_html = ""
        content_text = ""
        
        if content_type.lower() == "html":
            content_html = content
            content_text = html_to_text(content)
        else:
            content_text = content
        
        if not content_text and content_html:
            content_text = extract_text_from_html(content_html)
        
        attachments = []
        if message.get("hasAttachments", False):
            attachments_data = message.get("attachments", [])
            for att_data in attachments_data:
                attachment = EmailAttachment(
                    filename=att_data.get("name", ""),
                    content_type=att_data.get("contentType", ""),
                    size=att_data.get("size", 0),
                    attachment_id=att_data.get("id", "")
                )
                attachments.append(attachment)
        
        categories = message.get("categories", [])
        
        email_id = generate_email_id(message_id, AccountType.HOTMAIL.value)
        
        return Email(
            id=email_id,
            message_id=message_id,
            subject=subject,
            sender=sender_email,
            sender_name=sender_name,
            recipient=recipient,
            content_text=content_text,
            content_html=content_html,
            received_date=received_date,
            account_source=AccountType.HOTMAIL,
            status=EmailStatus.UNREAD,
            labels=categories,
            attachments=attachments,
            headers={},
            raw_size=len(content),
            provider_id=graph_id  # Store Graph API ID for operations
        )

    async def mark_message_as_read(self, message_id: str) -> bool:
        try:
            endpoint = f"/me/messages/{message_id}"
            data = {"isRead": True}
            
            await self._make_request("PATCH", endpoint, data)
            logger.debug(f"Marked Outlook message {message_id} as read")
            return True
            
        except Exception as e:
            logger.error(f"Error marking Outlook message {message_id} as read: {e}")
            return False

    async def send_email(self, to: str, subject: str, body: str, is_html: bool = False) -> bool:
        try:
            content_type = "HTML" if is_html else "Text"
            
            message_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": content_type,
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to
                            }
                        }
                    ]
                }
            }
            
            endpoint = "/me/sendMail"
            await self._make_request("POST", endpoint, message_data)
            
            logger.info(f"Email sent successfully to {to} via Outlook")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via Outlook: {e}")
            return False

    async def get_user_email(self) -> Optional[str]:
        try:
            endpoint = "/me"
            user_data = await self._make_request("GET", endpoint)
            return user_data.get("mail") or user_data.get("userPrincipalName")
            
        except Exception as e:
            logger.error(f"Error getting user email from Outlook: {e}")
            return None