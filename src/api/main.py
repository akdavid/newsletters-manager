from contextlib import asynccontextmanager
from typing import Any, Dict, List

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..agents.orchestrator import OrchestratorAgent
from ..utils.config import get_settings
from ..utils.logger import get_logger
from .routes import emails, summaries

logger = get_logger(__name__)
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator

    settings = get_settings()
    orchestrator = OrchestratorAgent({})

    try:
        await orchestrator.start()
        logger.info("Newsletter Manager API started")
        yield
    finally:
        if orchestrator:
            await orchestrator.stop()
        logger.info("Newsletter Manager API stopped")


app = FastAPI(
    title="Newsletter Manager API",
    description="Multi-agent newsletter processing and summarization system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router, prefix="/api", tags=["emails"])
app.include_router(summaries.router, prefix="/api", tags=["summaries"])


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Newsletter Manager</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #f8f9fa; padding: 20px; border-radius: 8px; }
                .section { margin: 20px 0; }
                .button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📧 Newsletter Manager</h1>
                <p>Multi-agent newsletter processing and summarization system</p>
            </div>
            
            <div class="section">
                <h2>Quick Actions</h2>
                <a href="/api/health" class="button">System Health</a>
                <a href="/api/emails" class="button">Recent Emails</a>
                <a href="/api/summaries" class="button">Recent Summaries</a>
                <a href="/docs" class="button">API Documentation</a>
            </div>
        </body>
    </html>
    """


@app.get("/api/health")
async def get_health():
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        health_info = await orchestrator.get_system_health()
        return health_info
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/collect")
async def collect_emails(background_tasks: BackgroundTasks):
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        background_tasks.add_task(orchestrator.collect_emails_only)
        return {
            "status": "started",
            "message": "Email collection started in background",
        }
    except Exception as e:
        logger.error(f"Email collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detect")
async def detect_newsletters(background_tasks: BackgroundTasks):
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        background_tasks.add_task(orchestrator.detect_newsletters_only)
        return {
            "status": "started",
            "message": "Newsletter detection started in background",
        }
    except Exception as e:
        logger.error(f"Newsletter detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
async def generate_summary(background_tasks: BackgroundTasks):
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        result = await orchestrator.generate_summary_only()
        return result
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline")
async def run_full_pipeline(background_tasks: BackgroundTasks):
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        background_tasks.add_task(orchestrator.run_full_pipeline)
        return {"status": "started", "message": "Full pipeline started in background"}
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/manual-summary")
async def trigger_manual_summary():
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        result = await orchestrator.trigger_manual_summary()
        return result
    except Exception as e:
        logger.error(f"Manual summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    try:
        if not orchestrator:
            return {"status": "not_running", "message": "Orchestrator not initialized"}

        return {
            "status": "running",
            "agents": {
                name: agent.is_running if hasattr(agent, "is_running") else True
                for name, agent in orchestrator.agents.items()
            },
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.log_level.lower(),
    )
