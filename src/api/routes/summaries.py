from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...db.database import get_db_session
from ...db.models import SummaryModel
from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/summaries", response_model=List[Dict[str, Any]])
async def get_summaries(
    limit: int = Query(20, ge=1, le=100, description="Number of summaries to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    try:
        with get_db_session() as session:
            query = session.query(SummaryModel).order_by(
                SummaryModel.generation_date.desc()
            )

            if status:
                query = query.filter(SummaryModel.status == status)

            summaries = query.limit(limit).all()

            result = []
            for summary in summaries:
                result.append(
                    {
                        "id": summary.id,
                        "title": summary.title,
                        "format": summary.format,
                        "status": summary.status,
                        "newsletters_count": summary.newsletters_count,
                        "total_emails_processed": summary.total_emails_processed,
                        "generation_date": summary.generation_date.isoformat(),
                        "processing_duration": summary.processing_duration,
                        "ai_model_used": summary.ai_model_used,
                        "word_count": summary.word_count,
                        "error_message": summary.error_message,
                        "created_at": summary.created_at.isoformat(),
                        "updated_at": summary.updated_at.isoformat(),
                    }
                )

            return result

    except Exception as e:
        logger.error(f"Failed to get summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{summary_id}")
async def get_summary_details(summary_id: str):
    try:
        with get_db_session() as session:
            summary = (
                session.query(SummaryModel)
                .filter(SummaryModel.id == summary_id)
                .first()
            )

            if not summary:
                raise HTTPException(status_code=404, detail="Summary not found")

            return {
                "id": summary.id,
                "title": summary.title,
                "content": summary.content,
                "format": summary.format,
                "status": summary.status,
                "newsletters_count": summary.newsletters_count,
                "total_emails_processed": summary.total_emails_processed,
                "generation_date": summary.generation_date.isoformat(),
                "newsletters_summaries": summary.newsletters_summaries,
                "metadata": summary.metadata,
                "error_message": summary.error_message,
                "processing_duration": summary.processing_duration,
                "ai_model_used": summary.ai_model_used,
                "word_count": summary.word_count,
                "created_at": summary.created_at.isoformat(),
                "updated_at": summary.updated_at.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{summary_id}/content")
async def get_summary_content(summary_id: str):
    try:
        with get_db_session() as session:
            summary = (
                session.query(SummaryModel)
                .filter(SummaryModel.id == summary_id)
                .first()
            )

            if not summary:
                raise HTTPException(status_code=404, detail="Summary not found")

            from fastapi.responses import HTMLResponse

            if summary.format == "html":
                return HTMLResponse(content=summary.content)
            else:
                return {"content": summary.content, "format": summary.format}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/stats")
async def get_summary_stats():
    try:
        with get_db_session() as session:
            total_summaries = session.query(SummaryModel).count()
            completed = (
                session.query(SummaryModel)
                .filter(SummaryModel.status == "completed")
                .count()
            )
            failed = (
                session.query(SummaryModel)
                .filter(SummaryModel.status == "failed")
                .count()
            )
            sent = (
                session.query(SummaryModel)
                .filter(SummaryModel.status == "sent")
                .count()
            )

            avg_newsletters = (
                session.query(session.func.avg(SummaryModel.newsletters_count)).scalar()
                or 0
            )
            avg_duration = (
                session.query(
                    session.func.avg(SummaryModel.processing_duration)
                ).scalar()
                or 0
            )

            recent_summary = (
                session.query(SummaryModel)
                .order_by(SummaryModel.generation_date.desc())
                .first()
            )

            return {
                "total_summaries": total_summaries,
                "completed": completed,
                "failed": failed,
                "sent": sent,
                "success_rate": round(
                    (completed / total_summaries * 100) if total_summaries > 0 else 0, 2
                ),
                "average_newsletters_per_summary": round(avg_newsletters, 1),
                "average_processing_duration": round(avg_duration, 2),
                "last_summary_date": recent_summary.generation_date.isoformat()
                if recent_summary
                else None,
            }

    except Exception as e:
        logger.error(f"Failed to get summary stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/summaries/{summary_id}")
async def delete_summary(summary_id: str):
    try:
        with get_db_session() as session:
            summary = (
                session.query(SummaryModel)
                .filter(SummaryModel.id == summary_id)
                .first()
            )

            if not summary:
                raise HTTPException(status_code=404, detail="Summary not found")

            session.delete(summary)
            session.commit()

            return {"message": "Summary deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
