from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


def utc_now():
    return datetime.now(timezone.utc)


Base = declarative_base()


class EmailModel(Base):
    __tablename__ = "emails"

    id = Column(String, primary_key=True)
    message_id = Column(String, unique=True, nullable=False)
    subject = Column(Text, nullable=False)
    sender = Column(String, nullable=False)
    sender_name = Column(String)
    recipient = Column(String, nullable=False)
    content_text = Column(Text)
    content_html = Column(Text)
    received_date = Column(DateTime, nullable=False)
    account_source = Column(String, nullable=False)
    status = Column(String, default="unread")
    is_newsletter = Column(Boolean)
    is_processed = Column(Boolean, default=False)
    thread_id = Column(String)
    labels = Column(JSON, default=list)
    attachments = Column(JSON, default=list)
    headers = Column(JSON, default=dict)
    raw_size = Column(Integer, default=0)
    provider_id = Column(
        String
    )  # For storing provider-specific IDs (e.g., Graph API ID)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    newsletter = relationship("NewsletterModel", back_populates="email", uselist=False)


class NewsletterModel(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=False)
    newsletter_type = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    detection_method = Column(String, nullable=False)
    sender_domain = Column(String, nullable=False)
    sender_name = Column(String)
    extra_metadata = Column(JSON, default=dict)
    classification_notes = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    email = relationship("EmailModel", back_populates="newsletter")


class SummaryModel(Base):
    __tablename__ = "summaries"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    format = Column(String, default="text")
    status = Column(String, default="pending")
    newsletters_count = Column(Integer, default=0)
    total_emails_processed = Column(Integer, default=0)
    generation_date = Column(DateTime, nullable=False)
    newsletters_summaries = Column(JSON, default=list)
    extra_metadata = Column(JSON, default=dict)
    error_message = Column(Text)
    processing_duration = Column(Float)
    ai_model_used = Column(String)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ProcessingLogModel(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(Text)
    extra_metadata = Column(JSON, default=dict)
    execution_time = Column(Float)
    timestamp = Column(DateTime, default=utc_now)


class SenderStatsModel(Base):
    __tablename__ = "sender_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_email = Column(String, nullable=False, unique=True)
    sender_name = Column(String)
    sender_domain = Column(String, nullable=False)
    total_emails = Column(Integer, default=0)
    newsletter_emails = Column(Integer, default=0)
    last_email_date = Column(DateTime)
    is_frequent_sender = Column(Boolean, default=False)
    average_confidence_score = Column(Float)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
