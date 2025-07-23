import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, MessageType, message_broker
from .email_collector import EmailCollectorAgent
from .newsletter_detector import NewsletterDetectorAgent
from .content_summarizer import ContentSummarizerAgent
from .scheduler import SchedulerAgent
from ..db.database import init_database
from ..utils.config import get_settings
from ..utils.exceptions import NewsletterManagerException
from ..utils.logger import get_logger, setup_logger

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Orchestrator", config)
        self.settings = get_settings()
        
        self.email_collector = None
        self.newsletter_detector = None
        self.content_summarizer = None
        self.scheduler = None
        
        self.agents = {}
        self.message_broker_task = None

    async def start(self):
        await super().start()
        
        setup_logger(self.settings.log_level, self.settings.log_file)
        
        try:
            init_database()
            
            await self._initialize_agents()
            await self._setup_message_broker()
            
            self.logger.info("Orchestrator started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start orchestrator: {e}")
            raise NewsletterManagerException(f"Orchestrator startup failed: {e}")

    async def stop(self):
        try:
            if self.message_broker_task:
                self.message_broker_task.cancel()
                try:
                    await self.message_broker_task
                except asyncio.CancelledError:
                    pass
            
            await message_broker.stop()
            
            for agent in self.agents.values():
                await agent.stop()
            
            self.logger.info("Orchestrator stopped successfully")
            await super().stop()
            
        except Exception as e:
            self.logger.error(f"Error stopping orchestrator: {e}")

    async def _initialize_agents(self):
        self.email_collector = EmailCollectorAgent(self.config)
        self.newsletter_detector = NewsletterDetectorAgent(self.config)
        self.content_summarizer = ContentSummarizerAgent(self.config)
        self.scheduler = SchedulerAgent(self.config)
        
        self.agents = {
            "email_collector": self.email_collector,
            "newsletter_detector": self.newsletter_detector,
            "content_summarizer": self.content_summarizer,
            "scheduler": self.scheduler
        }
        
        for agent in self.agents.values():
            await agent.start()
        
        self.scheduler.set_orchestrator_agent(self)
        
        self.logger.info("All agents initialized successfully")

    async def _setup_message_broker(self):
        self.message_broker_task = asyncio.create_task(message_broker.start())
        
        message_broker.subscribe(MessageType.ERROR_OCCURRED, self._handle_error_message)
        message_broker.subscribe(MessageType.TASK_COMPLETED, self._handle_task_completed)

    async def _handle_error_message(self, message):
        self.logger.error(f"Error from {message.sender}: {message.data}")

    async def _handle_task_completed(self, message):
        self.logger.info(f"Task completed by {message.sender}: {message.data}")

    async def execute(self, operation: str = "full_pipeline", **kwargs) -> Dict[str, Any]:
        if operation == "full_pipeline":
            return await self.run_full_pipeline()
        elif operation == "collect_emails":
            return await self.collect_emails_only()
        elif operation == "detect_newsletters":
            return await self.detect_newsletters_only()
        elif operation == "generate_summary":
            return await self.generate_summary_only()
        elif operation == "health_check":
            return await self.get_system_health()
        else:
            raise NewsletterManagerException(f"Unknown operation: {operation}")

    async def run_full_pipeline(self) -> Dict[str, Any]:
        self.logger.info("Starting full newsletter processing pipeline")
        
        start_time = datetime.now()
        pipeline_result = {
            "status": "started",
            "start_time": start_time.isoformat(),
            "steps": {}
        }
        
        try:
            step_start = datetime.now()
            email_result = await self.email_collector.execute()
            pipeline_result["steps"]["email_collection"] = {
                "status": "completed",
                "duration": (datetime.now() - step_start).total_seconds(),
                "collected_count": email_result.get("collected_count", 0),
                "errors": email_result.get("errors", [])
            }
            
            if email_result.get("collected_count", 0) == 0:
                pipeline_result["status"] = "completed"
                pipeline_result["message"] = "No emails to process"
                return pipeline_result
            
            await asyncio.sleep(1)
            
            step_start = datetime.now()
            detection_result = await self.newsletter_detector.execute(email_result["emails"])
            pipeline_result["steps"]["newsletter_detection"] = {
                "status": "completed",
                "duration": (datetime.now() - step_start).total_seconds(),
                "detected_count": detection_result.get("detected_count", 0),
                "processed_count": detection_result.get("processed_count", 0)
            }
            
            if detection_result.get("detected_count", 0) == 0:
                pipeline_result["status"] = "completed"
                pipeline_result["message"] = "No newsletters detected"
                return pipeline_result
            
            await asyncio.sleep(1)
            
            step_start = datetime.now()
            summary = await self.content_summarizer.execute(detection_result["newsletters"])
            
            if summary:
                summary_sent = await self.content_summarizer.send_summary_email(summary)
                
                pipeline_result["steps"]["content_summarization"] = {
                    "status": "completed",
                    "duration": (datetime.now() - step_start).total_seconds(),
                    "summary_id": summary.id,
                    "newsletters_count": summary.newsletters_count,
                    "email_sent": summary_sent
                }
                
                if summary_sent:
                    email_ids = [newsletter.email_id for newsletter in detection_result["newsletters"]]
                    mark_results = await self.email_collector.mark_emails_as_read(email_ids)
                    
                    pipeline_result["steps"]["mark_as_read"] = {
                        "status": "completed",
                        "marked_count": sum(1 for success in mark_results.values() if success),
                        "total_count": len(mark_results)
                    }
            
            total_duration = (datetime.now() - start_time).total_seconds()
            pipeline_result["status"] = "completed"
            pipeline_result["total_duration"] = total_duration
            pipeline_result["end_time"] = datetime.now().isoformat()
            
            self.logger.info(f"Full pipeline completed in {total_duration:.2f} seconds")
            return pipeline_result
            
        except Exception as e:
            pipeline_result["status"] = "failed"
            pipeline_result["error"] = str(e)
            pipeline_result["end_time"] = datetime.now().isoformat()
            
            self.logger.error(f"Pipeline failed: {e}")
            return pipeline_result

    async def collect_emails_only(self) -> Dict[str, Any]:
        self.logger.info("Running email collection only")
        try:
            return await self.email_collector.execute()
        except Exception as e:
            self.logger.error(f"Email collection failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def detect_newsletters_only(self) -> Dict[str, Any]:
        self.logger.info("Running newsletter detection only")
        try:
            unprocessed_emails = await self.email_collector.get_unprocessed_emails()
            if not unprocessed_emails:
                return {"status": "completed", "message": "No unprocessed emails found"}
            
            return await self.newsletter_detector.execute(unprocessed_emails)
        except Exception as e:
            self.logger.error(f"Newsletter detection failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def generate_summary_only(self) -> Dict[str, Any]:
        self.logger.info("Running summary generation only")
        try:
            summary = await self.content_summarizer.execute()
            if summary:
                summary_sent = await self.content_summarizer.send_summary_email(summary)
                return {
                    "status": "completed",
                    "summary_id": summary.id,
                    "newsletters_count": summary.newsletters_count,
                    "email_sent": summary_sent
                }
            else:
                return {"status": "completed", "message": "No newsletters to summarize"}
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def get_system_health(self) -> Dict[str, Any]:
        health_info = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator": await self.health_check(),
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            try:
                health_info["agents"][name] = await agent.health_check()
            except Exception as e:
                health_info["agents"][name] = {"status": "error", "error": str(e)}
        
        return health_info

    async def get_recent_summaries(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            summaries = await self.content_summarizer.get_recent_summaries(limit)
            return [summary.to_dict() for summary in summaries]
        except Exception as e:
            self.logger.error(f"Failed to get recent summaries: {e}")
            return []

    async def trigger_manual_summary(self) -> Dict[str, Any]:
        self.logger.info("Manual summary triggered via orchestrator")
        return await self.scheduler.trigger_manual_summary()

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self.agents.get(agent_name)

    async def health_check(self) -> Dict[str, Any]:
        base_health = await super().health_check()
        
        orchestrator_health = {
            "agents_count": len(self.agents),
            "message_broker_running": self.message_broker_task is not None and not self.message_broker_task.done(),
            "database_initialized": True
        }
        
        return {**base_health, **orchestrator_health}