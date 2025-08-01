# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Newsletter Manager is a multi-agent system using Agent-to-Agent (A2A) protocol to automate newsletter processing and summarization from multiple email accounts (3 Gmail + 1 Hotmail). The system runs daily at 8:00 AM to generate intelligent summaries and mark processed emails as read.

## Architecture

The system follows a multi-agent architecture with these core agents:
- **EmailCollectorAgent**: Collects emails from 4 email accounts
- **NewsletterDetectorAgent**: Classifies and detects newsletters 
- **ContentSummarizerAgent**: Generates AI-powered summaries
- **SchedulerAgent**: Manages scheduled tasks (daily 8:00 AM execution)
- **OrchestratorAgent**: Coordinates all other agents

## Technology Stack

- **Python 3.11+** (optimized for Apple Silicon M2)
- **AsyncIO** for asynchronous programming
- **Dataclasses** for data models (not Pydantic)
- **SQLAlchemy 2.0 + SQLite** for persistence
- **FastAPI 0.108** for REST interface with background tasks
- **Gmail API** with OAuth2 and AI integration
- **Microsoft Graph API** with MSAL authentication
- **OpenAI API 1.7** for content summarization and newsletter detection
- **APScheduler 3.10** for task scheduling
- **Loguru 0.7** for structured logging
- **Rich 13.7** for enhanced CLI interface
- **Click 8.1** for CLI commands
- **BeautifulSoup4** for HTML parsing
- **html2text** for content extraction

## Project Structure

Current implemented structure:

```
src/
├── agents/
│   ├── base_agent.py           # Abstract base class with message broker
│   ├── email_collector.py      # Email collection agent
│   ├── newsletter_detector.py  # Newsletter detection agent  
│   ├── content_summarizer.py   # Content summarization agent
│   ├── scheduler.py            # APScheduler-based scheduling agent
│   └── orchestrator.py         # Main orchestration agent
├── services/
│   ├── gmail_service.py        # Gmail API with AI integration
│   ├── outlook_service.py      # Microsoft Graph service
│   └── ai_service.py           # OpenAI service
├── models/
│   ├── email.py               # Email dataclass models
│   ├── newsletter.py          # Newsletter dataclass models
│   ├── summary.py             # Summary dataclass models
│   └── message.py             # Agent message models
├── utils/
│   ├── config.py              # Enhanced multi-account configuration
│   ├── logger.py              # Loguru-based logging
│   ├── exceptions.py          # Custom exceptions
│   └── message_broker.py      # Agent-to-agent communication
├── api/
│   ├── main.py                # FastAPI app with background tasks
│   └── routes/
│       ├── __init__.py
│       ├── emails.py          # Email collection routes
│       ├── summaries.py       # Summary routes
│       └── system.py          # System status routes
├── db/
│   ├── models.py              # SQLAlchemy ORM models
│   └── database.py            # Database configuration
├── cli/
│   └── main.py                # Rich CLI interface
├── main.py                    # CLI entry point
└── run_api.py                 # API server entry point
```

## Development Commands

### Setup and Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running the Application
```bash
# Start the FastAPI server
python src/run_api.py
# OR
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run the Rich CLI interface
python src/main.py

# Specific CLI commands
python src/main.py collect          # Email collection only
python src/main.py detect           # Newsletter detection only
python src/main.py summarize        # Summary generation only
python src/main.py pipeline         # Full processing pipeline
python src/main.py status           # System health with rich tables
python src/main.py summaries        # View recent summaries
python src/main.py config           # Show configuration
```

### Development and Testing
```bash
# Run integration tests (current approach)
python tests/test_gmail_integration.py
python tests/test_config.py

# Run linting and formatting (when available)
flake8 src/ tests/
black src/ tests/
isort src/ tests/

# Type checking (when configured)
mypy src/

# Development debugging
# Enable debug mode in config for detailed logging
# Use rich console output for better debugging experience
```

## Key Implementation Patterns

### Base Agent Pattern
All agents inherit from `BaseAgent` with message broker integration:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.utils.message_broker import MessageBroker
from src.models.message import AgentMessage
from src.utils.logger import get_logger

class BaseAgent(ABC):
    def __init__(self, name: str, config: Dict[str, Any], message_broker: Optional[MessageBroker] = None):
        self.name = name
        self.config = config  # Config dataclass
        self.message_broker = message_broker or MessageBroker()
        self.logger = get_logger(self.name)
        self._health_status = "healthy"
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Main execution method for the agent"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check method for monitoring"""
        return {
            "agent": self.name,
            "status": self._health_status,
            "last_execution": getattr(self, '_last_execution', None)
        }
    
    async def publish_message(self, message: AgentMessage):
        """Publish message to other agents"""
        await self.message_broker.publish(message)
```

### Agent-to-Agent Communication
Use structured messages with correlation IDs and comprehensive message types:

```python
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum
from datetime import datetime
import uuid

class MessageType(Enum):
    # Email Collection
    EMAIL_COLLECTION_STARTED = "email_collection_started"
    EMAIL_COLLECTED = "email_collected"
    EMAIL_COLLECTION_COMPLETED = "email_collection_completed"
    EMAIL_COLLECTION_FAILED = "email_collection_failed"
    
    # Newsletter Detection
    NEWSLETTER_DETECTION_STARTED = "newsletter_detection_started" 
    NEWSLETTER_DETECTED = "newsletter_detected"
    NEWSLETTER_DETECTION_COMPLETED = "newsletter_detection_completed"
    NEWSLETTER_DETECTION_FAILED = "newsletter_detection_failed"
    
    # Summary Generation
    SUMMARY_GENERATION_STARTED = "summary_generation_started"
    SUMMARY_GENERATED = "summary_generated"
    SUMMARY_GENERATION_COMPLETED = "summary_generation_completed"
    SUMMARY_GENERATION_FAILED = "summary_generation_failed"
    
    # System Events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    AGENT_HEALTH_CHECK = "agent_health_check"

@dataclass
class AgentMessage:
    type: MessageType
    sender: str
    data: Any
    timestamp: datetime
    correlation_id: str = None
    
    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())
```

### Configuration Management
Use dataclass-based configuration with environment variable support:

```python
from dataclasses import dataclass
from typing import List, Optional
import os

@dataclass
class Config:
    # Multi-Gmail API Configuration
    gmail_credentials_path_1: str
    gmail_credentials_path_2: str 
    gmail_credentials_path_3: str
    
    # Microsoft Graph API
    outlook_client_id: str
    outlook_client_secret: str
    outlook_tenant_id: str
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = 500
    
    # Database
    database_url: str = "sqlite:///newsletters.db"
    
    # Processing Limits
    max_emails_per_run: int = 100
    max_newsletters_to_summarize: int = 50
    
    # Rate Limiting (requests per minute)
    gmail_rate_limit: int = 250
    outlook_rate_limit: int = 60
    openai_rate_limit: int = 60
    
    # Scheduling & Email Summary
    daily_summary_time: str = "08:00"
    timezone: str = "Europe/Paris"
    summary_email_enabled: bool = True
    summary_email_recipients: List[str] = None
    
    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            gmail_credentials_path_1=os.getenv("GMAIL_CREDENTIALS_PATH_1"),
            gmail_credentials_path_2=os.getenv("GMAIL_CREDENTIALS_PATH_2"),
            gmail_credentials_path_3=os.getenv("GMAIL_CREDENTIALS_PATH_3"),
            # ... load all other env vars
        )
```

## API Endpoints

### Core Endpoints
- `GET /` - HTML homepage with quick action links
- `GET /api/emails` - List collected emails with pagination
- `POST /api/collect` - Trigger email collection
- `POST /api/detect` - Trigger newsletter detection
- `POST /api/summarize` - Trigger summary generation
- `POST /api/manual-summary` - Generate manual summary
- `POST /api/pipeline` - Run complete processing pipeline
- `GET /api/summaries` - Get summary history with filtering
- `GET /api/status` - Detailed system and agent health status
- `GET /docs` - Auto-generated OpenAPI documentation
- `GET /redoc` - Alternative API documentation

### CLI Commands (Rich Interface)
```bash
# Main CLI entry point
python src/main.py [COMMAND]

# Available commands:
collect          # Collect emails from all configured accounts
detect           # Run newsletter detection on collected emails
summarize        # Generate AI summaries for detected newsletters
pipeline         # Run complete processing pipeline (collect → detect → summarize)
status           # Show detailed system health with rich formatting
summaries        # Display recent summaries with rich tables
config           # Show current configuration settings

# Examples:
python src/main.py pipeline --verbose    # Full processing with detailed output
python src/main.py status               # Health check with colored tables
python src/main.py summaries --limit 10 # Show last 10 summaries
```

## Security Considerations

### Authentication
- Use OAuth2 flow with refresh tokens for Gmail
- Use MSAL (Microsoft Authentication Library) for Outlook
- Store credentials securely using environment variables
- Never commit API keys or credentials to repository

### Data Privacy
- Process emails locally only
- Encrypt sensitive content if stored
- No permanent storage of full email content
- Implement automatic token rotation

## Email Processing Logic

### Newsletter Detection Criteria
- Presence of "Unsubscribe" headers
- Sender patterns (noreply, newsletter, etc.)
- Recurring HTML structure
- Sender frequency analysis

### Content Summarization
Use structured prompts for OpenAI:

```python
SUMMARY_PROMPT = """
Résume cette newsletter en français de manière concise :
- 2-3 phrases maximum
- Mets en avant les points clés
- Garde un ton informatif
- Indique le type de newsletter (tech, business, etc.)

Contenu :
{content}
"""
```

## Environment Setup

### Required Environment Variables
```bash
# Multi-Gmail API Configuration
GMAIL_CREDENTIALS_PATH_1=/path/to/credentials1.json
GMAIL_CREDENTIALS_PATH_2=/path/to/credentials2.json
GMAIL_CREDENTIALS_PATH_3=/path/to/credentials3.json

# Microsoft Graph API
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_client_secret
OUTLOOK_TENANT_ID=your_tenant_id

# OpenAI Configuration
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=500

# Database
DATABASE_URL=sqlite:///newsletters.db

# Processing Limits
MAX_EMAILS_PER_RUN=100
MAX_NEWSLETTERS_TO_SUMMARIZE=50

# Rate Limiting (requests per minute)
GMAIL_RATE_LIMIT=250
OUTLOOK_RATE_LIMIT=60
OPENAI_RATE_LIMIT=60

# Scheduling & Summary Delivery
DAILY_SUMMARY_TIME=08:00
TIMEZONE=Europe/Paris
SUMMARY_EMAIL_ENABLED=true
SUMMARY_EMAIL_RECIPIENTS=email1@example.com,email2@example.com

# SMTP Configuration (for summary delivery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### macOS Apple Silicon Optimization 
- Use ARM64 native dependencies when possible
- Leverage native parallelization capabilities
- Optimize for low power consumption during scheduled runs

## API Rate Limits

### Gmail API
- 1 billion quota units per day
- Implement exponential backoff for rate limiting

### Microsoft Graph API  
- Variable rate limiting based on license
- Monitor and respect rate limit headers

### OpenAI API
- Monitor token usage per minute limits
- Implement request queuing for large batches

## Logging and Monitoring

### Structured Logging
```python
# Use JSON structured logs with context
logger.info("Email collected", 
    email_id=email.id, 
    account=account_name,
    is_newsletter=is_newsletter)
```

### Key Metrics to Track
- Number of emails processed per day
- Newsletter detection accuracy rate
- Average processing time per email
- API error rates by service
- Daily summary generation success rate

