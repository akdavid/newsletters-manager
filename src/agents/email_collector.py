import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .base_agent import BaseAgent, MessageType
from ..services.gmail_service import GmailService
from ..services.outlook_service import OutlookService
from ..models.email import Email, AccountType
from ..db.database import get_db_session, db_manager
from ..db.models import EmailModel
from ..utils.config import get_settings
from ..utils.exceptions import EmailServiceException
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EmailCollectorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("EmailCollector", config)
        self.settings = get_settings()
        self.gmail_services = []
        self.outlook_service = None
        
    async def start(self):
        await super().start()
        await self._initialize_services()

    async def _initialize_services(self):
        try:
            for i, credentials_path in enumerate(self.settings.gmail_credentials_paths):
                if not credentials_path or credentials_path.strip() == '' or credentials_path == '/path/to/gmail2_credentials.json':
                    self.logger.info(f"Skipping Gmail account {i+1} (no credentials configured)")
                    continue
                    
                account_type = [AccountType.GMAIL_1, AccountType.GMAIL_2, AccountType.GMAIL_3][i]
                gmail_service = GmailService(credentials_path, account_type)
                await gmail_service.authenticate()
                self.gmail_services.append(gmail_service)
                self.logger.info(f"Gmail account {i+1} ({account_type.value}) initialized successfully")
                
            # Initialize Outlook service if configured
            if (self.settings.outlook_client_id and 
                self.settings.outlook_client_id != 'your_outlook_client_id' and
                self.settings.outlook_client_secret and 
                self.settings.outlook_client_secret != 'your_outlook_client_secret'):
                
                self.outlook_service = OutlookService(
                    self.settings.outlook_client_id,
                    self.settings.outlook_client_secret,
                    self.settings.outlook_tenant_id
                )
                await self.outlook_service.authenticate(self.settings.outlook_email)
                self.logger.info("Outlook service initialized successfully")
            else:
                self.logger.info("Skipping Outlook service (no credentials configured)")
            
            self.logger.info("All email services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize email services: {e}")
            raise EmailServiceException(f"Service initialization failed: {e}")

    async def execute(self, max_emails_per_account: int = None) -> Dict[str, Any]:
        max_emails = max_emails_per_account or self.settings.max_emails_per_run
        
        self.logger.info(f"Starting email collection (max {max_emails} per account)")
        
        start_time = datetime.now(timezone.utc)
        collected_emails = []
        errors = []

        tasks = []
        for gmail_service in self.gmail_services:
            tasks.append(self._collect_from_gmail(gmail_service, max_emails))
        
        tasks.append(self._collect_from_outlook(max_emails))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                self.logger.error(f"Collection error: {result}")
            else:
                collected_emails.extend(result)

        await self._store_emails(collected_emails)
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        result = {
            "collected_count": len(collected_emails),
            "errors": errors,
            "execution_time": execution_time,
            "accounts_processed": len(self.gmail_services) + 1,
            "emails": collected_emails
        }

        await self.publish_message(
            MessageType.EMAIL_COLLECTED,
            result
        )
        
        self.logger.info(f"Email collection completed: {len(collected_emails)} emails collected")
        return result

    async def _collect_from_gmail(self, gmail_service: GmailService, max_emails: int) -> List[Email]:
        try:
            self.logger.info(f"Collecting emails from {gmail_service.account_type.value}")
            
            message_list = await gmail_service.get_unread_messages(max_emails)
            emails = []
            
            for message_info in message_list:
                try:
                    email = await gmail_service.get_message_details(message_info['id'])
                    if email:
                        emails.append(email)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get details for Gmail message {message_info['id']}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(emails)} emails from {gmail_service.account_type.value}")
            return emails
            
        except Exception as e:
            self.logger.error(f"Gmail collection failed for {gmail_service.account_type.value}: {e}")
            raise

    async def _collect_from_outlook(self, max_emails: int) -> List[Email]:
        try:
            self.logger.info("Collecting emails from Hotmail/Outlook")
            
            message_list = await self.outlook_service.get_unread_messages(max_emails)
            emails = []
            
            for message_info in message_list:
                try:
                    email = await self.outlook_service.get_message_details(message_info['id'])
                    if email:
                        emails.append(email)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get details for Outlook message {message_info['id']}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(emails)} emails from Hotmail/Outlook")
            return emails
            
        except Exception as e:
            self.logger.error(f"Outlook collection failed: {e}")
            raise

    async def _store_emails(self, emails: List[Email]):
        if not emails:
            return
            
        try:
            with db_manager.get_session() as session:
                for email in emails:
                    existing = session.query(EmailModel).filter_by(message_id=email.message_id).first()
                    
                    if not existing:
                        email_model = EmailModel(
                            id=email.id,
                            message_id=email.message_id,
                            subject=email.subject,
                            sender=email.sender,
                            sender_name=email.sender_name,
                            recipient=email.recipient,
                            content_text=email.content_text,
                            content_html=email.content_html,
                            received_date=email.received_date if email.received_date.tzinfo else email.received_date.replace(tzinfo=timezone.utc),
                            account_source=email.account_source.value,
                            status=email.status.value,
                            is_newsletter=email.is_newsletter,
                            is_processed=email.is_processed,
                            thread_id=email.thread_id,
                            labels=email.labels,
                            attachments=[att.__dict__ for att in email.attachments],
                            headers=email.headers,
                            raw_size=email.raw_size
                        )
                        session.add(email_model)
                    else:
                        self.logger.debug(f"Email {email.message_id} already exists in database")
                
                session.commit()
                self.logger.info(f"Stored {len(emails)} emails in database")
                
        except Exception as e:
            self.logger.error(f"Failed to store emails: {e}")
            raise

    async def mark_emails_as_read(self, email_ids: List[str]) -> Dict[str, bool]:
        results = {}
        successful_marks = 0
        
        self.logger.info(f"Attempting to mark {len(email_ids)} emails as read")
        
        try:
            with db_manager.get_session() as session:
                for email_id in email_ids:
                    email_model = session.query(EmailModel).filter_by(id=email_id).first()
                    if not email_model:
                        self.logger.warning(f"Email {email_id} not found in database")
                        results[email_id] = False
                        continue
                    
                    success = False
                    
                    if email_model.account_source.startswith('gmail'):
                        service_index = int(email_model.account_source[-1]) - 1
                        if service_index < len(self.gmail_services):
                            success = await self.gmail_services[service_index].mark_message_as_read(
                                email_model.message_id
                            )
                        else:
                            self.logger.error(f"Gmail service index {service_index} not available")
                    elif email_model.account_source == 'hotmail':
                        if self.outlook_service:
                            success = await self.outlook_service.mark_message_as_read(
                                email_model.message_id
                            )
                        else:
                            self.logger.error("Outlook service not configured")
                    else:
                        self.logger.error(f"Unknown account source: {email_model.account_source}")
                    
                    if success:
                        email_model.status = 'read'
                        email_model.updated_at = datetime.now(timezone.utc)
                        successful_marks += 1
                        self.logger.debug(f"Successfully marked email {email_id} as read")
                    else:
                        self.logger.warning(f"Failed to mark email {email_id} as read")
                    
                    results[email_id] = success
                
                session.commit()
                self.logger.info(f"Successfully marked {successful_marks}/{len(email_ids)} emails as read")
                
        except Exception as e:
            self.logger.error(f"Failed to mark emails as read: {e}")
            raise
        
        await self.publish_message(
            MessageType.EMAILS_MARKED_READ,
            {"results": results, "processed_count": len(email_ids)}
        )
        
        return results

    async def get_unprocessed_emails(self, limit: int = None) -> List[Email]:
        try:
            with db_manager.get_session() as session:
                query = session.query(EmailModel).filter_by(is_processed=False)
                
                if limit:
                    query = query.limit(limit)
                
                email_models = query.all()
                
                emails = []
                for model in email_models:
                    email = self._model_to_email(model)
                    emails.append(email)
                
                return emails
                
        except Exception as e:
            self.logger.error(f"Failed to get unprocessed emails: {e}")
            raise

    def _model_to_email(self, model: EmailModel) -> Email:
        from ..models.email import EmailAttachment
        
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
            status=model.status,
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

    async def health_check(self) -> Dict[str, Any]:
        base_health = await super().health_check()
        
        service_health = {
            "gmail_services": len(self.gmail_services),
            "outlook_service": self.outlook_service is not None
        }
        
        return {**base_health, **service_health}