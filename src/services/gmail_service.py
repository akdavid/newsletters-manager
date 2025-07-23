import os
import base64
import pickle
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models.email import Email, AccountType, EmailStatus, EmailAttachment
from ..utils.exceptions import GmailServiceException
from ..utils.helpers import (
    extract_email_address, extract_sender_name, generate_email_id,
    parse_email_date, html_to_text, extract_text_from_html
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GmailService:
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.send'
    ]

    def __init__(self, credentials_path: str, account_type: AccountType):
        self.credentials_path = credentials_path
        self.account_type = account_type
        self.service = None
        self.credentials = None

    async def authenticate(self):
        try:
            creds = None
            token_path = self.credentials_path.replace('.json', '_token.pickle')
            
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = Flow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    logger.info(f"Please visit this URL to authorize Gmail access: {auth_url}")
                    
                    authorization_code = input('Enter the authorization code: ')
                    flow.fetch_token(code=authorization_code)
                    creds = flow.credentials
                
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info(f"Gmail service authenticated for {self.account_type.value}")
            
        except Exception as e:
            logger.error(f"Gmail authentication failed for {self.account_type.value}: {e}")
            raise GmailServiceException(f"Authentication failed: {e}")

    async def get_unread_messages(self, max_results: int = 100) -> List[Dict[str, Any]]:
        try:
            if not self.service:
                await self.authenticate()
            
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread messages for {self.account_type.value}")
            return messages
            
        except HttpError as e:
            logger.error(f"Error getting unread messages: {e}")
            raise GmailServiceException(f"Failed to get unread messages: {e}")

    async def get_message_details(self, message_id: str) -> Optional[Email]:
        try:
            if not self.service:
                await self.authenticate()
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(message)
            
        except HttpError as e:
            logger.error(f"Error getting message details for {message_id}: {e}")
            return None

    def _parse_message(self, message: Dict[str, Any]) -> Email:
        payload = message['payload']
        headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
        
        subject = headers.get('subject', 'No Subject')
        sender = headers.get('from', '')
        recipient = headers.get('to', '')
        date_str = headers.get('date', '')
        message_id = headers.get('message-id', message['id'])
        thread_id = message.get('threadId')
        
        received_date = parse_email_date(date_str) or datetime.now()
        sender_email = extract_email_address(sender)
        sender_name = extract_sender_name(sender)
        
        content_text = ""
        content_html = ""
        attachments = []
        
        if 'parts' in payload:
            content_text, content_html, attachments = self._extract_content_from_parts(payload['parts'])
        else:
            if payload.get('mimeType') == 'text/plain':
                content_text = self._decode_body(payload.get('body', {}))
            elif payload.get('mimeType') == 'text/html':
                content_html = self._decode_body(payload.get('body', {}))
                content_text = html_to_text(content_html)
        
        if not content_text and content_html:
            content_text = extract_text_from_html(content_html)
        
        labels = [label for label in message.get('labelIds', []) if not label.startswith('Label_')]
        
        email_id = generate_email_id(message_id, self.account_type.value)
        
        return Email(
            id=email_id,
            message_id=message_id,
            subject=subject,
            sender=sender_email,
            sender_name=sender_name,
            recipient=extract_email_address(recipient),
            content_text=content_text,
            content_html=content_html,
            received_date=received_date,
            account_source=self.account_type,
            status=EmailStatus.UNREAD,
            thread_id=thread_id,
            labels=labels,
            attachments=attachments,
            headers=headers,
            raw_size=int(message.get('sizeEstimate', 0))
        )

    def _extract_content_from_parts(self, parts: List[Dict[str, Any]]) -> tuple:
        content_text = ""
        content_html = ""
        attachments = []
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                content_text += self._decode_body(part.get('body', {}))
            elif mime_type == 'text/html':
                content_html += self._decode_body(part.get('body', {}))
            elif 'parts' in part:
                sub_text, sub_html, sub_attachments = self._extract_content_from_parts(part['parts'])
                content_text += sub_text
                content_html += sub_html
                attachments.extend(sub_attachments)
            elif part.get('filename'):
                attachment = EmailAttachment(
                    filename=part['filename'],
                    content_type=mime_type,
                    size=int(part.get('body', {}).get('size', 0)),
                    attachment_id=part.get('body', {}).get('attachmentId', '')
                )
                attachments.append(attachment)
        
        return content_text, content_html, attachments

    def _decode_body(self, body: Dict[str, Any]) -> str:
        try:
            data = body.get('data', '')
            if data:
                decoded = base64.urlsafe_b64decode(data + '===')
                return decoded.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Failed to decode email body: {e}")
        return ""

    async def mark_message_as_read(self, message_id: str) -> bool:
        try:
            if not self.service:
                await self.authenticate()
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.debug(f"Marked message {message_id} as read")
            return True
            
        except HttpError as e:
            logger.error(f"Error marking message {message_id} as read: {e}")
            return False

    async def send_email(self, to: str, subject: str, body: str, is_html: bool = False) -> bool:
        try:
            if not self.service:
                await self.authenticate()
            
            message = MIMEMultipart() if is_html else MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if is_html:
                message.attach(MIMEText(body, 'html'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except HttpError as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def get_user_email(self) -> Optional[str]:
        try:
            if not self.service:
                await self.authenticate()
            
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
            
        except HttpError as e:
            logger.error(f"Error getting user email: {e}")
            return None