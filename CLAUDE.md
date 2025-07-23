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
- **Pydantic** for data validation
- **SQLAlchemy + SQLite** for persistence
- **FastAPI** for REST interface
- **Gmail API** with `google-auth` and `google-api-python-client`
- **Microsoft Graph API** with `msal` and `requests`
- **OpenAI API** for content summarization
- **APScheduler** for task scheduling
- **Loguru** for advanced logging

## Project Structure

When implementing, follow this structure:

```
src/
├── agents/
│   ├── base_agent.py           # Abstract base class for all agents
│   ├── email_collector.py      # Email collection agent
│   ├── newsletter_detector.py  # Newsletter detection agent  
│   ├── content_summarizer.py   # Content summarization agent
│   ├── scheduler.py            # Scheduling agent
│   └── orchestrator.py         # Orchestration agent
├── services/
│   ├── gmail_service.py        # Gmail API service
│   ├── outlook_service.py      # Microsoft Graph service
│   ├── ai_service.py           # OpenAI service
│   └── email_service.py        # Email sending service
├── models/
│   ├── email.py               # Email data models
│   ├── newsletter.py          # Newsletter data models
│   └── summary.py             # Summary data models
├── utils/
│   ├── config.py              # Centralized configuration
│   ├── logger.py              # Logging configuration
│   └── exceptions.py          # Custom exceptions
├── api/
│   ├── main.py                # FastAPI entry point
│   └── routes/
│       ├── emails.py          # Email routes
│       └── summaries.py       # Summary routes
└── db/
    ├── models.py              # SQLAlchemy models
    └── database.py            # Database configuration
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
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run the scheduler (for automatic daily processing)
python -m src.agents.scheduler

# Manual newsletter collection and summarization
python -m src.agents.orchestrator --manual
```

### Development and Testing
```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run linting
flake8 src/ tests/
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## Key Implementation Patterns

### Base Agent Pattern
All agents must inherit from `BaseAgent` and implement the `execute()` method:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict
import asyncio

class BaseAgent(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = get_logger(self.name)
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass
```

### Agent-to-Agent Communication
Use structured messages for inter-agent communication:

```python
from dataclasses import dataclass
from typing import Any
from enum import Enum

class MessageType(Enum):
    EMAIL_COLLECTED = "email_collected"
    NEWSLETTER_DETECTED = "newsletter_detected"
    SUMMARY_GENERATED = "summary_generated"

@dataclass
class AgentMessage:
    type: MessageType
    sender: str
    data: Any
    timestamp: datetime
```

### Configuration Management
Use Pydantic for centralized configuration:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Email APIs
    gmail_credentials_path: str
    outlook_client_id: str
    outlook_client_secret: str
    
    # OpenAI
    openai_api_key: str
    
    # Database
    database_url: str = "sqlite:///newsletters.db"
    
    # Scheduling
    daily_summary_time: str = "08:00"
    
    class Config:
        env_file = ".env"
```

## API Endpoints

### Core Endpoints
- `GET /api/emails` - List collected emails
- `POST /api/summarize` - Trigger manual summarization
- `GET /api/summaries` - Get summary history
- `GET /api/status` - Get system and agent status

### CLI Commands
```bash
newsletters collect          # Manual email collection
newsletters summarize        # Generate summary
newsletters status          # System status
newsletters config          # Configuration management
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
# Gmail API
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json

# Microsoft Graph
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_client_secret

# OpenAI
OPENAI_API_KEY=your_api_key

# Database
DATABASE_URL=sqlite:///newsletters.db

# Scheduling
DAILY_SUMMARY_TIME=08:00
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

