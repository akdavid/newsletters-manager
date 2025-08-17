from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...db.database import get_db_session
from ...db.models import EmailModel
from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/emails", response_model=List[Dict[str, Any]])
async def get_emails(
    limit: int = Query(50, ge=1, le=1000, description="Number of emails to return"),
    account_source: Optional[str] = Query(None, description="Filter by account source"),
    is_newsletter: Optional[bool] = Query(
        None, description="Filter by newsletter status"
    ),
    is_processed: Optional[bool] = Query(
        None, description="Filter by processed status"
    ),
):
    try:
        with get_db_session() as session:
            query = session.query(EmailModel).order_by(EmailModel.received_date.desc())

            if account_source:
                query = query.filter(EmailModel.account_source == account_source)

            if is_newsletter is not None:
                query = query.filter(EmailModel.is_newsletter == is_newsletter)

            if is_processed is not None:
                query = query.filter(EmailModel.is_processed == is_processed)

            emails = query.limit(limit).all()

            result = []
            for email in emails:
                result.append(
                    {
                        "id": email.id,
                        "message_id": email.message_id,
                        "subject": email.subject,
                        "sender": email.sender,
                        "sender_name": email.sender_name,
                        "recipient": email.recipient,
                        "received_date": email.received_date.isoformat(),
                        "account_source": email.account_source,
                        "status": email.status,
                        "is_newsletter": email.is_newsletter,
                        "is_processed": email.is_processed,
                        "labels": email.labels,
                        "raw_size": email.raw_size,
                        "created_at": email.created_at.isoformat(),
                        "updated_at": email.updated_at.isoformat(),
                    }
                )

            return result

    except Exception as e:
        logger.error(f"Failed to get emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/{email_id}")
async def get_email_details(email_id: str):
    try:
        with get_db_session() as session:
            email = session.query(EmailModel).filter(EmailModel.id == email_id).first()

            if not email:
                raise HTTPException(status_code=404, detail="Email not found")

            return {
                "id": email.id,
                "message_id": email.message_id,
                "subject": email.subject,
                "sender": email.sender,
                "sender_name": email.sender_name,
                "recipient": email.recipient,
                "content_text": email.content_text,
                "content_html": email.content_html,
                "received_date": email.received_date.isoformat(),
                "account_source": email.account_source,
                "status": email.status,
                "is_newsletter": email.is_newsletter,
                "is_processed": email.is_processed,
                "thread_id": email.thread_id,
                "labels": email.labels,
                "attachments": email.attachments,
                "headers": email.headers,
                "raw_size": email.raw_size,
                "created_at": email.created_at.isoformat(),
                "updated_at": email.updated_at.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/stats")
async def get_email_stats():
    try:
        with get_db_session() as session:
            total_emails = session.query(EmailModel).count()
            newsletters = (
                session.query(EmailModel)
                .filter(EmailModel.is_newsletter == True)
                .count()
            )
            processed = (
                session.query(EmailModel)
                .filter(EmailModel.is_processed == True)
                .count()
            )
            unread = (
                session.query(EmailModel).filter(EmailModel.status == "unread").count()
            )

            by_account = {}
            accounts = (
                session.query(
                    EmailModel.account_source,
                    session.query(EmailModel)
                    .filter(EmailModel.account_source == EmailModel.account_source)
                    .count()
                    .label("count"),
                )
                .group_by(EmailModel.account_source)
                .all()
            )

            for account, count in accounts:
                by_account[account] = count

            return {
                "total_emails": total_emails,
                "newsletters": newsletters,
                "processed": processed,
                "unread": unread,
                "by_account": by_account,
                "newsletter_percentage": round(
                    (newsletters / total_emails * 100) if total_emails > 0 else 0, 2
                ),
                "processed_percentage": round(
                    (processed / total_emails * 100) if total_emails > 0 else 0, 2
                ),
            }

    except Exception as e:
        logger.error(f"Failed to get email stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/emails/{email_id}")
async def delete_email(email_id: str):
    try:
        with get_db_session() as session:
            email = session.query(EmailModel).filter(EmailModel.id == email_id).first()

            if not email:
                raise HTTPException(status_code=404, detail="Email not found")

            session.delete(email)
            session.commit()

            return {"message": "Email deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
