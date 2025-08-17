import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class MessageType(Enum):
    EMAIL_COLLECTED = "email_collected"
    NEWSLETTER_DETECTED = "newsletter_detected"
    SUMMARY_GENERATED = "summary_generated"
    EMAILS_MARKED_READ = "emails_marked_read"
    TASK_COMPLETED = "task_completed"
    ERROR_OCCURRED = "error_occurred"
    AGENT_STATUS = "agent_status"


@dataclass
class AgentMessage:
    id: str
    type: MessageType
    sender: str
    recipient: Optional[str]
    data: Any
    timestamp: datetime
    correlation_id: Optional[str] = None

    @classmethod
    def create(
        self,
        msg_type: MessageType,
        sender: str,
        data: Any,
        recipient: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "AgentMessage":
        return AgentMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            sender=sender,
            recipient=recipient,
            data=data,
            timestamp=datetime.now(),
            correlation_id=correlation_id,
        )


class MessageBroker:
    def __init__(self):
        self._subscribers: Dict[MessageType, List[callable]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, message_type: MessageType, callback: callable):
        if message_type not in self._subscribers:
            self._subscribers[message_type] = []
        # Prevent duplicate subscriptions by checking if callback already exists
        if callback not in self._subscribers[message_type]:
            self._subscribers[message_type].append(callback)
            logger.debug(
                f"Subscribed to {message_type.value}, total callbacks: {len(self._subscribers[message_type])}"
            )
        else:
            logger.debug(
                f"Callback already subscribed to {message_type.value}, skipping duplicate"
            )

    def unsubscribe(self, message_type: MessageType, callback: callable):
        if message_type in self._subscribers:
            if callback in self._subscribers[message_type]:
                self._subscribers[message_type].remove(callback)

    async def publish(self, message: AgentMessage):
        await self._message_queue.put(message)
        logger.debug(f"Published message {message.type.value} from {message.sender}")

    async def start(self):
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                await self._process_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def stop(self):
        self._running = False

    def get_subscription_count(self, message_type: MessageType) -> int:
        """Get the number of callbacks subscribed to a message type"""
        return len(self._subscribers.get(message_type, []))

    async def _process_message(self, message: AgentMessage):
        if message.type in self._subscribers:
            for callback in self._subscribers[message.type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in message callback: {e}")


message_broker = MessageBroker()


class BaseAgent(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logger.bind(agent=name)
        self._running = False
        self._broker = message_broker

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass

    async def start(self):
        self.logger.info(f"Starting agent {self.name}")
        self._running = True
        await self._setup_subscriptions()

    async def stop(self):
        self.logger.info(f"Stopping agent {self.name}")
        self._running = False

    async def _setup_subscriptions(self):
        pass

    async def publish_message(
        self,
        msg_type: MessageType,
        data: Any,
        recipient: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        message = AgentMessage.create(
            msg_type=msg_type,
            sender=self.name,
            data=data,
            recipient=recipient,
            correlation_id=correlation_id,
        )
        await self._broker.publish(message)

    def subscribe_to_message(self, msg_type: MessageType, callback: callable):
        self._broker.subscribe(msg_type, callback)

    @property
    def is_running(self) -> bool:
        return self._running

    async def health_check(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "status": "running" if self._running else "stopped",
            "timestamp": datetime.now().isoformat(),
        }
