from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class SummaryStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SENT = "sent"


class SummaryFormat(Enum):
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class NewsletterSummaryItem:
    email_id: str
    subject: str
    sender: str
    newsletter_type: str
    summary_text: str
    key_points: List[str]
    confidence_score: float
    original_length: int
    summary_length: int
    links: List[str] = field(default_factory=list)
    received_date: Optional[datetime] = None
    account_source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper datetime serialization."""
        return {
            'email_id': self.email_id,
            'subject': self.subject,
            'sender': self.sender,
            'newsletter_type': self.newsletter_type,
            'summary_text': self.summary_text,
            'key_points': self.key_points,
            'confidence_score': self.confidence_score,
            'original_length': self.original_length,
            'summary_length': self.summary_length,
            'links': self.links,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'account_source': self.account_source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsletterSummaryItem':
        """Create from dictionary with proper datetime deserialization."""
        received_date = None
        if data.get('received_date'):
            from datetime import datetime
            received_date = datetime.fromisoformat(data['received_date'])
        
        return cls(
            email_id=data['email_id'],
            subject=data['subject'],
            sender=data['sender'],
            newsletter_type=data['newsletter_type'],
            summary_text=data['summary_text'],
            key_points=data.get('key_points', []),
            confidence_score=data['confidence_score'],
            original_length=data['original_length'],
            summary_length=data['summary_length'],
            links=data.get('links', []),
            received_date=received_date,
            account_source=data.get('account_source')
        )


@dataclass
class Summary:
    id: str
    title: str
    content: str
    format: SummaryFormat
    status: SummaryStatus
    newsletters_count: int
    total_emails_processed: int
    generation_date: datetime
    newsletters_summaries: List[NewsletterSummaryItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processing_duration: Optional[float] = None
    ai_model_used: Optional[str] = None
    word_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_newsletter_summary(self, newsletter_summary: NewsletterSummaryItem):
        self.newsletters_summaries.append(newsletter_summary)
        self.newsletters_count = len(self.newsletters_summaries)

    def get_compression_ratio(self) -> float:
        if not self.newsletters_summaries:
            return 0.0
        
        total_original = sum(item.original_length for item in self.newsletters_summaries)
        total_summary = sum(item.summary_length for item in self.newsletters_summaries)
        
        if total_original == 0:
            return 0.0
        
        return total_summary / total_original

    def get_average_confidence(self) -> float:
        if not self.newsletters_summaries:
            return 0.0
        
        return sum(item.confidence_score for item in self.newsletters_summaries) / len(self.newsletters_summaries)

    def get_newsletters_by_type(self) -> Dict[str, List[NewsletterSummaryItem]]:
        by_type: Dict[str, List[NewsletterSummaryItem]] = {}
        
        for item in self.newsletters_summaries:
            newsletter_type = item.newsletter_type
            if newsletter_type not in by_type:
                by_type[newsletter_type] = []
            by_type[newsletter_type].append(item)
        
        return by_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'format': self.format.value,
            'status': self.status.value,
            'newsletters_count': self.newsletters_count,
            'total_emails_processed': self.total_emails_processed,
            'generation_date': self.generation_date.isoformat(),
            'newsletters_summaries': [item.to_dict() for item in self.newsletters_summaries],
            'metadata': self.metadata,
            'error_message': self.error_message,
            'processing_duration': self.processing_duration,
            'ai_model_used': self.ai_model_used,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'compression_ratio': self.get_compression_ratio(),
            'average_confidence': self.get_average_confidence()
        }