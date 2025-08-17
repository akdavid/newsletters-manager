import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..db.database import init_database
from ..utils.config import get_settings
from ..utils.exceptions import NewsletterManagerException
from ..utils.logger import get_logger, setup_logger
from .base_agent import BaseAgent, MessageType, message_broker
from .content_summarizer import ContentSummarizerAgent
from .email_collector import EmailCollectorAgent
from .newsletter_detector import NewsletterDetectorAgent
from .scheduler import SchedulerAgent

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

        # Pipeline completion tracking
        self.pipeline_state = {
            "newsletter_detection_completed": False,
            "content_summarization_completed": False,
            "pipeline_result": None,
        }

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
            "scheduler": self.scheduler,
        }

        for agent in self.agents.values():
            await agent.start()

        self.scheduler.set_orchestrator_agent(self)

        self.logger.info("All agents initialized successfully")

    async def _setup_message_broker(self):
        self.message_broker_task = asyncio.create_task(message_broker.start())

        message_broker.subscribe(MessageType.ERROR_OCCURRED, self._handle_error_message)
        message_broker.subscribe(
            MessageType.TASK_COMPLETED, self._handle_task_completed
        )

        # Subscribe to pipeline completion events using the same message broker
        self.logger.info("🔔 Setting up message subscriptions for pipeline completion")
        message_broker.subscribe(
            MessageType.NEWSLETTER_DETECTED, self._handle_newsletter_detection_completed
        )
        message_broker.subscribe(
            MessageType.SUMMARY_GENERATED, self._handle_summarization_completed
        )
        message_broker.subscribe(
            MessageType.EMAILS_MARKED_READ, self._handle_emails_marked_read_completed
        )
        self.logger.info("🔔 Message subscriptions set up successfully")

    async def _handle_error_message(self, message):
        self.logger.error(f"Error from {message.sender}: {message.data}")

    async def _handle_task_completed(self, message):
        self.logger.info(f"Task completed by {message.sender}: {message.data}")

    async def _handle_newsletter_detection_completed(self, message):
        self.logger.info(
            "🎯 ORCHESTRATOR RECEIVED: Newsletter detection completed, updating pipeline state"
        )
        self.pipeline_state["newsletter_detection_completed"] = True
        if self.pipeline_state["pipeline_result"]:
            # Calculate duration from the step start time if available
            step_data = self.pipeline_state["pipeline_result"]["steps"].get(
                "newsletter_detection", {}
            )
            start_time = step_data.get("start_time")
            duration = 0.0
            if start_time:
                from datetime import datetime

                duration = (
                    datetime.now() - datetime.fromisoformat(start_time)
                ).total_seconds()

            self.pipeline_state["pipeline_result"]["steps"]["newsletter_detection"] = {
                "status": "completed",
                "duration": duration,
                "detected_count": message.data.get("detected_count", 0),
                "processed_count": message.data.get("processed_count", 0),
                "execution_time": message.data.get("execution_time", duration),
            }

            # Initialize content summarization step when detection completes
            if message.data.get("detected_count", 0) > 0:
                self.pipeline_state["pipeline_result"]["steps"][
                    "content_summarization"
                ] = {
                    "status": "in_progress",
                    "start_time": datetime.now().isoformat(),
                    "duration": 0.0,
                }

    async def _handle_summarization_completed(self, message):
        self.logger.info("Content summarization completed, updating pipeline state")
        self.pipeline_state["content_summarization_completed"] = True
        if self.pipeline_state["pipeline_result"]:
            # Calculate duration from the step start time if available
            step_data = self.pipeline_state["pipeline_result"]["steps"].get(
                "content_summarization", {}
            )
            start_time = step_data.get("start_time")
            duration = 0.0
            if start_time:
                from datetime import datetime

                duration = (
                    datetime.now() - datetime.fromisoformat(start_time)
                ).total_seconds()

            self.pipeline_state["pipeline_result"]["steps"]["content_summarization"] = {
                "status": "completed",
                "duration": duration,
                "summary_generated": message.data.get("summary_generated", False),
                "newsletters_count": message.data.get("newsletters_count", 0),
                "processing_duration": message.data.get(
                    "processing_duration", duration
                ),
                "email_sent": message.data.get("email_sent", False),
            }

            # Add email sending step if email was sent
            if message.data.get("email_sent", False):
                self.pipeline_state["pipeline_result"]["steps"]["email_sending"] = {
                    "status": "completed",
                    "duration": 1.0,  # Approximate time for email sending
                    "email_sent": True,
                    "recipients": 1,
                }

            # Add mark-as-read step tracking (will be updated when emails are marked)
            self.pipeline_state["pipeline_result"]["steps"]["mark_emails_read"] = {
                "status": "in_progress",
                "duration": 0.0,
                "emails_to_mark": message.data.get("newsletters_count", 0),
                "start_time": datetime.now().isoformat(),
            }

    async def _handle_emails_marked_read_completed(self, message):
        # Only process pipeline completion messages, ignore regular mark-as-read messages
        if not message.data.get("pipeline_completion", False):
            return

        self.logger.info("Emails marked as read completed, updating pipeline state")
        if self.pipeline_state["pipeline_result"]:
            # Calculate duration for mark-as-read step
            step_data = self.pipeline_state["pipeline_result"]["steps"].get(
                "mark_emails_read", {}
            )
            start_time = step_data.get("start_time")
            duration = 0.0
            if start_time:
                from datetime import datetime

                duration = (
                    datetime.now() - datetime.fromisoformat(start_time)
                ).total_seconds()

            results = message.data.get("results", {})
            successful_marks = sum(1 for success in results.values() if success)
            total_emails = len(results)

            self.pipeline_state["pipeline_result"]["steps"]["mark_emails_read"] = {
                "status": "completed",
                "duration": duration,
                "emails_marked": f"{successful_marks}/{total_emails}",
                "success_rate": f"{(successful_marks/total_emails*100):.1f}%"
                if total_emails > 0
                else "0%",
            }

    async def execute(
        self, operation: str = "full_pipeline", **kwargs
    ) -> Dict[str, Any]:
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
            "steps": {},
        }

        try:
            step_start = datetime.now()
            email_result = await self.email_collector.execute()
            pipeline_result["steps"]["email_collection"] = {
                "status": "completed",
                "duration": (datetime.now() - step_start).total_seconds(),
                "collected_count": email_result.get("collected_count", 0),
                "errors": email_result.get("errors", []),
            }

            if email_result.get("collected_count", 0) == 0:
                pipeline_result["status"] = "completed"
                pipeline_result["message"] = "No emails to process"
                return pipeline_result

            # Store pipeline result for message handlers to update
            self.pipeline_state["pipeline_result"] = pipeline_result
            self.pipeline_state["newsletter_detection_completed"] = False
            self.pipeline_state["content_summarization_completed"] = False

            # Initialize newsletter detection step tracking
            pipeline_result["steps"]["newsletter_detection"] = {
                "status": "in_progress",
                "start_time": datetime.now().isoformat(),
                "duration": 0.0,
            }

            # Newsletter detection will be triggered automatically via EMAIL_COLLECTED message
            # Wait for both newsletter detection and summarization to complete
            self.logger.info(
                "Waiting for newsletter detection and summarization to complete..."
            )

            max_wait_time = self.settings.pipeline_timeout_seconds
            check_interval = 2  # Check every 2 seconds
            elapsed = 0

            while elapsed < max_wait_time:
                if (
                    self.pipeline_state["newsletter_detection_completed"]
                    and self.pipeline_state["content_summarization_completed"]
                ):
                    self.logger.info("All pipeline steps completed successfully")
                    break

                await asyncio.sleep(check_interval)
                elapsed += check_interval

                # Log progress every 10 seconds
                if elapsed % 10 == 0:
                    detection_status = (
                        "✅"
                        if self.pipeline_state["newsletter_detection_completed"]
                        else "⏳"
                    )
                    summarization_status = (
                        "✅"
                        if self.pipeline_state["content_summarization_completed"]
                        else "⏳"
                    )
                    self.logger.info(
                        f"Pipeline progress: Detection {detection_status}, Summarization {summarization_status}"
                    )

            if elapsed >= max_wait_time:
                self.logger.warning(
                    "Pipeline timeout - some steps may not have completed"
                )
                pipeline_result["status"] = "timeout"
                pipeline_result[
                    "message"
                ] = "Some steps did not complete within the timeout period"

            # Ensure final status is set
            if not pipeline_result.get("status") == "timeout":
                pipeline_result["status"] = "completed"

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
                    "email_sent": summary_sent,
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
            "agents": {},
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
            "message_broker_running": self.message_broker_task is not None
            and not self.message_broker_task.done(),
            "database_initialized": True,
        }

        return {**base_health, **orchestrator_health}
