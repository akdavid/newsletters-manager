import asyncio
from datetime import datetime, time
from typing import Any, Dict, List, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..utils.config import get_settings
from ..utils.exceptions import SchedulerException
from ..utils.logger import get_logger
from .base_agent import BaseAgent, MessageType

logger = get_logger(__name__)


class SchedulerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Scheduler", config)
        self.settings = get_settings()
        self.scheduler = None
        self.orchestrator_agent = None
        self.timezone = pytz.timezone(self.settings.timezone)

    async def start(self):
        await super().start()
        await self._initialize_scheduler()

    async def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
        await super().stop()

    async def _initialize_scheduler(self):
        try:
            self.scheduler = AsyncIOScheduler(timezone=self.timezone)

            daily_time = self._parse_daily_time(self.settings.daily_summary_time)

            self.scheduler.add_job(
                self._run_daily_summary,
                CronTrigger(
                    hour=daily_time.hour,
                    minute=daily_time.minute,
                    timezone=self.timezone,
                ),
                id="daily_summary",
                name="Daily Newsletter Summary",
                misfire_grace_time=300,
                coalesce=True,
                max_instances=1,
            )

            self.scheduler.add_job(
                self._health_check_job,
                CronTrigger(minute=0, timezone=self.timezone),
                id="health_check",
                name="Hourly Health Check",
                misfire_grace_time=60,
                coalesce=True,
                max_instances=1,
            )

            self.scheduler.start()
            self.logger.info(
                f"Scheduler started with daily summary at {self.settings.daily_summary_time}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            raise SchedulerException(f"Scheduler initialization failed: {e}")

    def _parse_daily_time(self, time_str: str) -> time:
        try:
            hour, minute = map(int, time_str.split(":"))
            return time(hour, minute)
        except ValueError:
            self.logger.warning(f"Invalid time format: {time_str}, using default 08:00")
            return time(8, 0)

    async def _run_daily_summary(self):
        self.logger.info("Starting scheduled daily summary process")

        try:
            if not self.orchestrator_agent:
                self.logger.error(
                    "Orchestrator agent not set, cannot run daily summary"
                )
                return

            start_time = datetime.now()

            result = await self.orchestrator_agent.run_full_pipeline()

            execution_time = (datetime.now() - start_time).total_seconds()

            await self.publish_message(
                MessageType.TASK_COMPLETED,
                {
                    "task": "daily_summary",
                    "status": "completed" if result else "failed",
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "result": result,
                },
            )

            self.logger.info(f"Daily summary completed in {execution_time:.2f} seconds")

        except Exception as e:
            self.logger.error(f"Daily summary failed: {e}")

            await self.publish_message(
                MessageType.ERROR_OCCURRED,
                {
                    "task": "daily_summary",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def _health_check_job(self):
        try:
            health_info = await self.health_check()

            self.logger.debug(f"Health check completed: {health_info}")

            await self.publish_message(
                MessageType.AGENT_STATUS,
                {
                    "agent": self.name,
                    "health": health_info,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")

    async def execute(self, task_type: str = "daily_summary") -> Dict[str, Any]:
        if task_type == "daily_summary":
            await self._run_daily_summary()
            return {"status": "completed", "task": task_type}
        else:
            raise SchedulerException(f"Unknown task type: {task_type}")

    def set_orchestrator_agent(self, orchestrator_agent):
        self.orchestrator_agent = orchestrator_agent
        self.logger.info("Orchestrator agent set for scheduler")

    def add_one_time_job(self, job_func, run_date: datetime, job_id: str, **kwargs):
        try:
            self.scheduler.add_job(
                job_func, "date", run_date=run_date, id=job_id, **kwargs
            )
            self.logger.info(f"One-time job '{job_id}' scheduled for {run_date}")

        except Exception as e:
            self.logger.error(f"Failed to add one-time job: {e}")
            raise SchedulerException(f"Failed to schedule job: {e}")

    def remove_job(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Job '{job_id}' removed")
        except Exception as e:
            self.logger.error(f"Failed to remove job '{job_id}': {e}")

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": job.next_run_time.isoformat()
                        if job.next_run_time
                        else None,
                        "trigger": str(job.trigger),
                        "func_name": job.func.__name__
                        if hasattr(job.func, "__name__")
                        else str(job.func),
                    }
                )
            return jobs
        except Exception as e:
            self.logger.error(f"Failed to get scheduled jobs: {e}")
            return []

    def pause_job(self, job_id: str):
        try:
            self.scheduler.pause_job(job_id)
            self.logger.info(f"Job '{job_id}' paused")
        except Exception as e:
            self.logger.error(f"Failed to pause job '{job_id}': {e}")

    def resume_job(self, job_id: str):
        try:
            self.scheduler.resume_job(job_id)
            self.logger.info(f"Job '{job_id}' resumed")
        except Exception as e:
            self.logger.error(f"Failed to resume job '{job_id}': {e}")

    def update_daily_summary_schedule(self, new_time: str):
        try:
            daily_time = self._parse_daily_time(new_time)

            self.scheduler.reschedule_job(
                "daily_summary",
                trigger=CronTrigger(
                    hour=daily_time.hour,
                    minute=daily_time.minute,
                    timezone=self.timezone,
                ),
            )

            self.logger.info(f"Daily summary schedule updated to {new_time}")

        except Exception as e:
            self.logger.error(f"Failed to update daily summary schedule: {e}")
            raise SchedulerException(f"Failed to update schedule: {e}")

    async def health_check(self) -> Dict[str, Any]:
        base_health = await super().health_check()

        scheduler_health = {
            "scheduler_running": self.scheduler.running if self.scheduler else False,
            "scheduled_jobs_count": len(self.scheduler.get_jobs())
            if self.scheduler
            else 0,
            "next_daily_summary": None,
            "orchestrator_connected": self.orchestrator_agent is not None,
        }

        if self.scheduler:
            daily_job = self.scheduler.get_job("daily_summary")
            if daily_job and daily_job.next_run_time:
                scheduler_health[
                    "next_daily_summary"
                ] = daily_job.next_run_time.isoformat()

        return {**base_health, **scheduler_health}

    async def trigger_manual_summary(self) -> Dict[str, Any]:
        self.logger.info("Manual summary triggered")

        try:
            start_time = datetime.now()

            if not self.orchestrator_agent:
                raise SchedulerException("Orchestrator agent not available")

            result = await self.orchestrator_agent.run_full_pipeline()

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "status": "completed" if result else "failed",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "trigger": "manual",
                "result": result,
            }

        except Exception as e:
            self.logger.error(f"Manual summary failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "trigger": "manual",
            }
