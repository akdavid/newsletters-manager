import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .base_agent import BaseAgent, MessageType
from ..services.ai_service import AIService
from ..models.email import Email
from ..models.newsletter import Newsletter
from ..models.summary import Summary, SummaryStatus, NewsletterSummaryItem
from ..db.database import get_db_session, db_manager
from ..db.models import SummaryModel, EmailModel, NewsletterModel
from ..utils.config import get_settings
from ..utils.exceptions import SummaryGenerationException
from ..utils.helpers import generate_uuid
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentSummarizerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ContentSummarizer", config)
        self.settings = get_settings()
        self.ai_service = AIService(
            self.settings.openai_api_key,
            self.settings.openai_model,
            self.settings.openai_max_tokens
        )

    async def start(self):
        await super().start()
        await self._setup_subscriptions()

    async def _setup_subscriptions(self):
        self.subscribe_to_message(MessageType.NEWSLETTER_DETECTED, self._handle_newsletters_detected)

    async def _handle_newsletters_detected(self, message):
        self.logger.info("Processing detected newsletters for summarization")
        newsletters = message.data.get("newsletters", [])
        
        if newsletters:
            await self.execute(newsletters)

    async def execute(self, newsletters: List[Newsletter] = None) -> Summary:
        try:
            if newsletters is None:
                newsletters = await self._get_unprocessed_newsletters()
            
            if not newsletters:
                self.logger.info("No newsletters to summarize")
                return None

            self.logger.info(f"Starting summarization for {len(newsletters)} newsletters")
            
            start_time = datetime.now()
            
            emails_dict = await self._get_emails_for_newsletters(newsletters)
            
            newsletter_summaries = []
            for newsletter in newsletters:
                email = emails_dict.get(newsletter.email_id)
                if email:
                    summary_item = await self.ai_service.summarize_newsletter(email, newsletter)
                    if summary_item:
                        newsletter_summaries.append(summary_item)

            if not newsletter_summaries:
                raise SummaryGenerationException("No newsletter summaries generated")

            daily_summary = await self.ai_service.generate_daily_summary(newsletter_summaries)
            daily_summary.processing_duration = (datetime.now() - start_time).total_seconds()
            
            await self._store_summary(daily_summary)
            
            await self._mark_emails_as_processed(newsletters)
            
            await self.publish_message(
                MessageType.SUMMARY_GENERATED,
                {
                    "summary_id": daily_summary.id,
                    "newsletters_count": len(newsletter_summaries),
                    "processing_duration": daily_summary.processing_duration
                }
            )

            self.logger.info(f"Summary generated successfully: {daily_summary.id}")
            return daily_summary
            
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            raise SummaryGenerationException(f"Summarization failed: {e}")

    async def _get_unprocessed_newsletters(self) -> List[Newsletter]:
        try:
            with db_manager.get_session() as session:
                query = session.query(NewsletterModel)\
                    .join(EmailModel, NewsletterModel.email_id == EmailModel.id)\
                    .filter(EmailModel.is_processed == False)\
                    .limit(self.settings.summary_max_newsletters)
                
                newsletter_models = query.all()
                
                newsletters = []
                for model in newsletter_models:
                    newsletter = self._model_to_newsletter(model)
                    newsletters.append(newsletter)
                
                return newsletters
                
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed newsletters: {e}")
            raise

    async def _get_emails_for_newsletters(self, newsletters: List[Newsletter]) -> Dict[str, Email]:
        email_ids = [newsletter.email_id for newsletter in newsletters]
        emails_dict = {}
        
        try:
            with db_manager.get_session() as session:
                email_models = session.query(EmailModel).filter(EmailModel.id.in_(email_ids)).all()
                
                for model in email_models:
                    email = self._model_to_email(model)
                    emails_dict[email.id] = email
                
                return emails_dict
                
        except Exception as e:
            self.logger.error(f"Failed to get emails for newsletters: {e}")
            raise

    def _model_to_newsletter(self, model: NewsletterModel) -> Newsletter:
        from ..models.newsletter import NewsletterType, DetectionMethod, NewsletterMetadata
        
        metadata = NewsletterMetadata(**model.metadata) if model.metadata else NewsletterMetadata()
        
        return Newsletter(
            email_id=model.email_id,
            newsletter_type=NewsletterType(model.newsletter_type),
            confidence_score=model.confidence_score,
            detection_method=DetectionMethod(model.detection_method),
            sender_domain=model.sender_domain,
            sender_name=model.sender_name,
            metadata=metadata,
            classification_notes=model.classification_notes,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _model_to_email(self, model: EmailModel) -> Email:
        from ..models.email import EmailAttachment, AccountType, EmailStatus
        
        attachments = []
        for att_data in model.attachments or []:
            attachment = EmailAttachment(
                filename=att_data.get('filename', ''),
                content_type=att_data.get('content_type', ''),
                size=att_data.get('size', 0),
                attachment_id=att_data.get('attachment_id', '')
            )
            attachments.append(attachment)
        
        return Email(
            id=model.id,
            message_id=model.message_id,
            subject=model.subject,
            sender=model.sender,
            sender_name=model.sender_name,
            recipient=model.recipient,
            content_text=model.content_text,
            content_html=model.content_html,
            received_date=model.received_date,
            account_source=AccountType(model.account_source),
            status=EmailStatus(model.status),
            is_newsletter=model.is_newsletter,
            is_processed=model.is_processed,
            thread_id=model.thread_id,
            labels=model.labels or [],
            attachments=attachments,
            headers=model.headers or {},
            raw_size=model.raw_size,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def _store_summary(self, summary: Summary):
        try:
            with db_manager.get_session() as session:
                summary_model = SummaryModel(
                    id=summary.id,
                    title=summary.title,
                    content=summary.content,
                    format=summary.format.value,
                    status=summary.status.value,
                    newsletters_count=summary.newsletters_count,
                    total_emails_processed=summary.total_emails_processed,
                    generation_date=summary.generation_date,
                    newsletters_summaries=[item.__dict__ for item in summary.newsletters_summaries],
                    metadata=summary.metadata,
                    error_message=summary.error_message,
                    processing_duration=summary.processing_duration,
                    ai_model_used=summary.ai_model_used,
                    word_count=summary.word_count
                )
                session.add(summary_model)
                session.commit()
                
                self.logger.debug(f"Stored summary {summary.id} in database")
                
        except Exception as e:
            self.logger.error(f"Failed to store summary: {e}")
            raise

    async def _mark_emails_as_processed(self, newsletters: List[Newsletter]):
        try:
            email_ids = [newsletter.email_id for newsletter in newsletters]
            
            with db_manager.get_session() as session:
                session.query(EmailModel)\
                    .filter(EmailModel.id.in_(email_ids))\
                    .update({EmailModel.is_processed: True, EmailModel.updated_at: datetime.now()})
                
                session.commit()
                
                self.logger.debug(f"Marked {len(email_ids)} emails as processed")
                
        except Exception as e:
            self.logger.error(f"Failed to mark emails as processed: {e}")
            raise

    async def send_summary_email(self, summary: Summary, recipient: str = None) -> bool:
        try:
            recipient = recipient or self.settings.summary_recipient
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = summary.title
            msg['From'] = self.settings.smtp_username
            msg['To'] = recipient
            
            html_part = MIMEText(summary.content, 'html', 'utf-8')
            msg.attach(html_part)
            
            server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)
            server.starttls()
            server.login(self.settings.smtp_username, self.settings.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.settings.smtp_username, recipient, text)
            server.quit()
            
            await self._update_summary_status(summary.id, SummaryStatus.SENT)
            
            self.logger.info(f"Summary email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send summary email: {e}")
            await self._update_summary_status(summary.id, SummaryStatus.FAILED, str(e))
            return False

    async def _update_summary_status(self, summary_id: str, status: SummaryStatus, error_message: str = None):
        try:
            with db_manager.get_session() as session:
                summary_model = session.query(SummaryModel).filter_by(id=summary_id).first()
                if summary_model:
                    summary_model.status = status.value
                    summary_model.updated_at = datetime.now()
                    if error_message:
                        summary_model.error_message = error_message
                    session.commit()
                    
        except Exception as e:
            self.logger.error(f"Failed to update summary status: {e}")

    async def get_recent_summaries(self, limit: int = 10) -> List[Summary]:
        try:
            with db_manager.get_session() as session:
                summary_models = session.query(SummaryModel)\
                    .order_by(SummaryModel.generation_date.desc())\
                    .limit(limit)\
                    .all()
                
                summaries = []
                for model in summary_models:
                    summary = self._model_to_summary(model)
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            self.logger.error(f"Failed to get recent summaries: {e}")
            raise

    def _model_to_summary(self, model: SummaryModel) -> Summary:
        from ..models.summary import SummaryFormat, SummaryStatus, NewsletterSummaryItem
        
        newsletter_summaries = []
        for item_data in model.newsletters_summaries or []:
            item = NewsletterSummaryItem(**item_data)
            newsletter_summaries.append(item)
        
        return Summary(
            id=model.id,
            title=model.title,
            content=model.content,
            format=SummaryFormat(model.format),
            status=SummaryStatus(model.status),
            newsletters_count=model.newsletters_count,
            total_emails_processed=model.total_emails_processed,
            generation_date=model.generation_date,
            newsletters_summaries=newsletter_summaries,
            metadata=model.metadata or {},
            error_message=model.error_message,
            processing_duration=model.processing_duration,
            ai_model_used=model.ai_model_used,
            word_count=model.word_count,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def health_check(self) -> Dict[str, Any]:
        base_health = await super().health_check()
        
        summarizer_health = {
            "ai_service": self.ai_service is not None,
            "smtp_configured": bool(self.settings.smtp_username and self.settings.smtp_password),
            "max_newsletters": self.settings.summary_max_newsletters
        }
        
        return {**base_health, **summarizer_health}