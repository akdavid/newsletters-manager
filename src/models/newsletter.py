from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class NewsletterType(Enum):
    TECH = "tech"
    BUSINESS = "business"
    PERSONAL = "personal"
    NEWS = "news"
    MARKETING = "marketing"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"


class DetectionMethod(Enum):
    HEADER_ANALYSIS = "header_analysis"
    SENDER_PATTERN = "sender_pattern"
    CONTENT_ANALYSIS = "content_analysis"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    MANUAL = "manual"


@dataclass
class NewsletterMetadata:
    sender_frequency: int = 0
    has_unsubscribe_link: bool = False
    html_to_text_ratio: float = 0.0
    contains_tracking_pixels: bool = False
    contains_promotional_keywords: bool = False


@dataclass
class Newsletter:
    email_id: str
    newsletter_type: NewsletterType
    confidence_score: float
    detection_method: DetectionMethod
    sender_domain: str
    sender_name: Optional[str]
    metadata: NewsletterMetadata = field(default_factory=NewsletterMetadata)
    classification_notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_high_confidence(self) -> bool:
        return self.confidence_score >= 0.8

    def get_type_display(self) -> str:
        return self.newsletter_type.value.title()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'email_id': self.email_id,
            'newsletter_type': self.newsletter_type.value,
            'confidence_score': self.confidence_score,
            'detection_method': self.detection_method.value,
            'sender_domain': self.sender_domain,
            'sender_name': self.sender_name,
            'metadata': {
                'sender_frequency': self.metadata.sender_frequency,
                'has_unsubscribe_link': self.metadata.has_unsubscribe_link,
                'html_to_text_ratio': self.metadata.html_to_text_ratio,
                'contains_tracking_pixels': self.metadata.contains_tracking_pixels,
                'contains_promotional_keywords': self.metadata.contains_promotional_keywords
            },
            'classification_notes': self.classification_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }