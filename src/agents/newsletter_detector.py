import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..db.database import db_manager, get_db_session
from ..db.models import NewsletterModel, SenderStatsModel
from ..models.email import Email
from ..models.newsletter import (
    DetectionMethod,
    Newsletter,
    NewsletterMetadata,
    NewsletterType,
)
from ..services.ai_service import AIService
from ..utils.config import get_settings
from ..utils.exceptions import NewsletterDetectionException
from ..utils.helpers import (
    calculate_html_to_text_ratio,
    contains_promotional_keywords,
    contains_tracking_pixels,
    extract_domain,
    has_unsubscribe_link,
)
from ..utils.logger import get_logger
from .base_agent import BaseAgent, MessageType

logger = get_logger(__name__)


class NewsletterDetectorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("NewsletterDetector", config)
        self.settings = get_settings()
        self.ai_service = AIService(
            self.settings.openai_api_key,
            self.settings.openai_model,
            self.settings.openai_max_tokens,
        )

    async def start(self):
        await super().start()
        await self._setup_subscriptions()

    async def _setup_subscriptions(self):
        # Import the global message broker to ensure we use the same instance
        from .base_agent import message_broker

        self.logger.info("🔔 NewsletterDetector subscribing to EMAIL_COLLECTED messages")

        # Check current subscription count before subscribing
        before_count = message_broker.get_subscription_count(
            MessageType.EMAIL_COLLECTED
        )
        self.logger.info(f"EMAIL_COLLECTED subscriptions before: {before_count}")

        message_broker.subscribe(
            MessageType.EMAIL_COLLECTED, self._handle_email_collected
        )

        # Check subscription count after subscribing
        after_count = message_broker.get_subscription_count(MessageType.EMAIL_COLLECTED)
        self.logger.info(f"EMAIL_COLLECTED subscriptions after: {after_count}")
        self.logger.info("🔔 NewsletterDetector subscription setup complete")

    async def _handle_email_collected(self, message):
        self.logger.info("Processing collected emails for newsletter detection")
        emails = message.data.get("emails", [])

        if emails:
            await self.execute(emails)

    async def execute(self, emails: List[Email]) -> Dict[str, Any]:
        self.logger.info(f"Starting newsletter detection for {len(emails)} emails")

        start_time = datetime.now(timezone.utc)
        detected_newsletters = []
        processed_count = 0
        errors = []

        for email in emails:
            try:
                newsletter = await self._detect_newsletter(email)
                if newsletter:
                    detected_newsletters.append(newsletter)
                    await self._store_newsletter(newsletter)
                    await self._update_sender_stats(email, newsletter)

                processed_count += 1

            except Exception as e:
                error_msg = f"Detection failed for email {email.id}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = {
            "processed_count": processed_count,
            "detected_count": len(detected_newsletters),
            "errors": errors,
            "execution_time": execution_time,
            "newsletters": detected_newsletters,
        }

        self.logger.info(
            f"Publishing NEWSLETTER_DETECTED message with {len(detected_newsletters)} newsletters"
        )
        # Use global message broker to ensure orchestrator receives the message
        from .base_agent import AgentMessage, message_broker

        message = AgentMessage.create(
            msg_type=MessageType.NEWSLETTER_DETECTED, sender=self.name, data=result
        )
        await message_broker.publish(message)
        self.logger.info("NEWSLETTER_DETECTED message published successfully")

        self.logger.info(
            f"Newsletter detection completed: {len(detected_newsletters)} newsletters detected"
        )
        return result

    async def _detect_newsletter(self, email: Email) -> Optional[Newsletter]:
        try:
            # Use the same simple logic that was working in Gmail service
            if self.ai_service:
                try:
                    ai_classification = await self.ai_service.classify_email_content(
                        email
                    )
                    is_newsletter = ai_classification.get("is_newsletter", False)
                    self.logger.debug(
                        f"AI classification for '{email.subject[:30]}...': {ai_classification}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"AI classification failed for {email.id}, using fallback: {e}"
                    )
                    is_newsletter = self._fallback_newsletter_detection(email)
            else:
                is_newsletter = self._fallback_newsletter_detection(email)

            # If not classified as newsletter, return None
            if not is_newsletter:
                return None

            # Create newsletter object with AI classification results
            confidence_score = (
                ai_classification.get("confidence", 0.8)
                if "ai_classification" in locals()
                else 0.7
            )
            detection_methods = [DetectionMethod.CONTENT_ANALYSIS]

            # Get newsletter type from AI classification
            newsletter_type = self._map_ai_type_to_enum(
                ai_classification.get("type", "other")
                if "ai_classification" in locals()
                else "other"
            )

            # Add basic detection signals
            basic_score, basic_methods = self._basic_newsletter_detection(email)
            if basic_score > 0:
                detection_methods.extend(basic_methods)
                confidence_score = min(0.95, confidence_score + (basic_score * 0.1))

            # Add sender frequency analysis
            sender_frequency_score = await self._calculate_sender_frequency_score(
                email.sender
            )
            if sender_frequency_score > 0.3:
                detection_methods.append(DetectionMethod.FREQUENCY_ANALYSIS)
                confidence_score = min(
                    0.98, confidence_score + (sender_frequency_score * 0.1)
                )

            # Always create newsletter if AI classified it as such (no min threshold check)
            metadata = self._create_newsletter_metadata(email)

            newsletter = Newsletter(
                email_id=email.id,
                newsletter_type=newsletter_type,
                confidence_score=confidence_score,
                detection_method=detection_methods[0]
                if detection_methods
                else DetectionMethod.HEADER_ANALYSIS,
                sender_domain=extract_domain(email.sender),
                sender_name=email.sender_name,
                metadata=metadata,
                classification_notes=f"Detected using methods: {', '.join([m.value for m in detection_methods])}",
            )

            return newsletter

        except Exception as e:
            self.logger.error(f"Newsletter detection failed for email {email.id}: {e}")
            raise NewsletterDetectionException(f"Detection failed: {e}")

    def _fallback_newsletter_detection(self, email: Email) -> bool:
        """
        Basic newsletter detection if AI is not available.
        Uses the existing method from the Email model.
        """
        return email.is_likely_newsletter()

    def _basic_newsletter_detection(
        self, email: Email
    ) -> tuple[float, List[DetectionMethod]]:
        score = 0.0
        methods = []

        if email.has_unsubscribe_header():
            score += 0.4
            methods.append(DetectionMethod.HEADER_ANALYSIS)

        sender_lower = email.sender.lower()
        newsletter_patterns = [
            "newsletter",
            "noreply",
            "no-reply",
            "donotreply",
            "digest",
            "update",
            "notification",
            "bulletin",
            "news",
        ]

        if any(pattern in sender_lower for pattern in newsletter_patterns):
            score += 0.3
            methods.append(DetectionMethod.SENDER_PATTERN)

        subject_patterns = [
            "newsletter",
            "digest",
            "weekly",
            "daily",
            "monthly",
            "update",
            "news",
            "bulletin",
        ]

        subject_lower = email.subject.lower()
        if any(pattern in subject_lower for pattern in subject_patterns):
            score += 0.2
            methods.append(DetectionMethod.SENDER_PATTERN)

        commercial_domains = [
            "mailchimp.com",
            "constantcontact.com",
            "sendgrid.net",
            "amazonses.com",
            "mailgun.org",
            "postmarkapp.com",
        ]

        sender_domain = extract_domain(email.sender)
        if any(domain in sender_domain for domain in commercial_domains):
            score += 0.3
            methods.append(DetectionMethod.SENDER_PATTERN)

        return min(score, 1.0), methods

    async def _calculate_sender_frequency_score(self, sender: str) -> float:
        try:
            with db_manager.get_session() as session:
                stats = (
                    session.query(SenderStatsModel)
                    .filter_by(sender_email=sender)
                    .first()
                )

                if not stats:
                    return 0.0

                if stats.total_emails >= 5:
                    newsletter_ratio = stats.newsletter_emails / stats.total_emails
                    return min(newsletter_ratio, 1.0)

                return 0.0

        except Exception as e:
            self.logger.warning(
                f"Failed to calculate sender frequency for {sender}: {e}"
            )
            return 0.0

    def _map_ai_type_to_enum(self, ai_type: str) -> NewsletterType:
        type_mapping = {
            "tech": NewsletterType.TECH,
            "business": NewsletterType.BUSINESS,
            "news": NewsletterType.NEWS,
            "marketing": NewsletterType.MARKETING,
            "education": NewsletterType.EDUCATION,
            "entertainment": NewsletterType.ENTERTAINMENT,
            "health": NewsletterType.HEALTH,
            "personal": NewsletterType.PERSONAL,
            "other": NewsletterType.OTHER,
        }
        return type_mapping.get(ai_type.lower(), NewsletterType.OTHER)

    def _create_newsletter_metadata(self, email: Email) -> NewsletterMetadata:
        content_html = email.content_html or ""
        content_text = email.content_text or ""

        return NewsletterMetadata(
            sender_frequency=0,
            has_unsubscribe_link=has_unsubscribe_link(content_html, content_text),
            html_to_text_ratio=calculate_html_to_text_ratio(content_html, content_text),
            contains_tracking_pixels=contains_tracking_pixels(content_html),
            contains_promotional_keywords=contains_promotional_keywords(content_text),
        )

    async def _store_newsletter(self, newsletter: Newsletter):
        try:
            with db_manager.get_session() as session:
                existing = (
                    session.query(NewsletterModel)
                    .filter_by(email_id=newsletter.email_id)
                    .first()
                )

                if not existing:
                    newsletter_model = NewsletterModel(
                        email_id=newsletter.email_id,
                        newsletter_type=newsletter.newsletter_type.value,
                        confidence_score=newsletter.confidence_score,
                        detection_method=newsletter.detection_method.value,
                        sender_domain=newsletter.sender_domain,
                        sender_name=newsletter.sender_name,
                        metadata=newsletter.metadata.__dict__,
                        classification_notes=newsletter.classification_notes,
                    )
                    session.add(newsletter_model)

                    from ..db.models import EmailModel

                    email_model = (
                        session.query(EmailModel)
                        .filter_by(id=newsletter.email_id)
                        .first()
                    )
                    if email_model:
                        email_model.is_newsletter = True

                    session.commit()
                    self.logger.debug(
                        f"Stored newsletter for email {newsletter.email_id}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to store newsletter: {e}")
            raise

    async def _update_sender_stats(self, email: Email, newsletter: Newsletter):
        try:
            with db_manager.get_session() as session:
                stats = (
                    session.query(SenderStatsModel)
                    .filter_by(sender_email=email.sender)
                    .first()
                )

                if not stats:
                    stats = SenderStatsModel(
                        sender_email=email.sender,
                        sender_name=email.sender_name,
                        sender_domain=extract_domain(email.sender),
                        total_emails=1,
                        newsletter_emails=1,
                        last_email_date=email.received_date
                        if email.received_date.tzinfo
                        else email.received_date.replace(tzinfo=timezone.utc),
                        average_confidence_score=newsletter.confidence_score,
                    )
                    session.add(stats)
                else:
                    stats.total_emails += 1
                    stats.newsletter_emails += 1
                    # Ensure both datetimes are timezone-aware for comparison
                    email_date = email.received_date
                    if email_date.tzinfo is None:
                        email_date = email_date.replace(tzinfo=timezone.utc)

                    last_date = stats.last_email_date
                    if last_date.tzinfo is None:
                        last_date = last_date.replace(tzinfo=timezone.utc)

                    stats.last_email_date = max(last_date, email_date)

                    old_avg = stats.average_confidence_score or 0.0
                    stats.average_confidence_score = (
                        old_avg + newsletter.confidence_score
                    ) / 2

                stats.is_frequent_sender = stats.total_emails >= 3
                stats.updated_at = datetime.now(timezone.utc)

                session.commit()

        except Exception as e:
            self.logger.error(f"Failed to update sender stats: {e}")

    async def get_newsletters_by_type(
        self, newsletter_type: NewsletterType = None, limit: int = None
    ) -> List[Newsletter]:
        try:
            with db_manager.get_session() as session:
                query = session.query(NewsletterModel)

                if newsletter_type:
                    query = query.filter_by(newsletter_type=newsletter_type.value)

                if limit:
                    query = query.limit(limit)

                newsletter_models = query.all()

                newsletters = []
                for model in newsletter_models:
                    newsletter = self._model_to_newsletter(model)
                    newsletters.append(newsletter)

                return newsletters

        except Exception as e:
            self.logger.error(f"Failed to get newsletters by type: {e}")
            raise

    def _model_to_newsletter(self, model: NewsletterModel) -> Newsletter:
        metadata = (
            NewsletterMetadata(**model.metadata)
            if model.metadata
            else NewsletterMetadata()
        )

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
            updated_at=model.updated_at,
        )

    async def health_check(self) -> Dict[str, Any]:
        base_health = await super().health_check()

        ai_health = {
            "ai_service": self.ai_service is not None,
            "min_confidence_score": self.settings.min_confidence_score,
        }

        return {**base_health, **ai_health}
