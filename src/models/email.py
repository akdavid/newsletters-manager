from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AccountType(Enum):
    GMAIL_1 = "gmail_1"
    GMAIL_2 = "gmail_2"
    GMAIL_3 = "gmail_3"
    HOTMAIL = "hotmail"


class EmailStatus(Enum):
    UNREAD = "unread"
    READ = "read"
    PROCESSED = "processed"
    ERROR = "error"


@dataclass
class EmailAttachment:
    filename: str
    content_type: str
    size: int
    attachment_id: str


@dataclass
class Email:
    id: str
    message_id: str
    subject: str
    sender: str
    sender_name: Optional[str]
    recipient: str
    content_text: str
    content_html: Optional[str]
    received_date: datetime
    account_source: AccountType
    status: EmailStatus = EmailStatus.UNREAD
    is_newsletter: Optional[bool] = None
    is_processed: bool = False
    thread_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    attachments: List[EmailAttachment] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    raw_size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def has_unsubscribe_header(self) -> bool:
        unsubscribe_headers = ['list-unsubscribe', 'unsubscribe']
        return any(header.lower() in [h.lower() for h in self.headers.keys()] 
                  for header in unsubscribe_headers)

    def is_likely_newsletter(self) -> bool:
        newsletter_indicators = [
            'newsletter', 'unsubscribe', 'noreply', 'no-reply',
            'digest', 'bulletin', 'update', 'notification'
        ]
        
        sender_lower = self.sender.lower()
        subject_lower = self.subject.lower()
        
        return (
            any(indicator in sender_lower for indicator in newsletter_indicators) or
            any(indicator in subject_lower for indicator in newsletter_indicators) or
            self.has_unsubscribe_header()
        )

    def get_display_name(self) -> str:
        return self.sender_name if self.sender_name else self.sender

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'message_id': self.message_id,
            'subject': self.subject,
            'sender': self.sender,
            'sender_name': self.sender_name,
            'recipient': self.recipient,
            'content_text': self.content_text,
            'content_html': self.content_html,
            'received_date': self.received_date.isoformat(),
            'account_source': self.account_source.value,
            'status': self.status.value,
            'is_newsletter': self.is_newsletter,
            'is_processed': self.is_processed,
            'thread_id': self.thread_id,
            'labels': self.labels,
            'attachments': [
                {
                    'filename': att.filename,
                    'content_type': att.content_type,
                    'size': att.size,
                    'attachment_id': att.attachment_id
                } for att in self.attachments
            ],
            'headers': self.headers,
            'raw_size': self.raw_size,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }