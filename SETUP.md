# Newsletter Manager - Setup Guide

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Gmail API Configuration (3 accounts)
GMAIL_CREDENTIALS_PATH_1=/path/to/gmail1_credentials.json
GMAIL_CREDENTIALS_PATH_2=/path/to/gmail2_credentials.json
GMAIL_CREDENTIALS_PATH_3=/path/to/gmail3_credentials.json

# Microsoft Graph API Configuration
OUTLOOK_CLIENT_ID=your_outlook_client_id
OUTLOOK_CLIENT_SECRET=your_outlook_client_secret
OUTLOOK_TENANT_ID=your_tenant_id
OUTLOOK_EMAIL=your_hotmail_email@hotmail.com

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key

# Email Configuration for sending summaries
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SUMMARY_RECIPIENT=your_email@gmail.com
```

### 3. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create credentials (OAuth 2.0 Client IDs)
5. Download the credentials JSON files
6. Place them in your project directory and update the paths in `.env`

### 4. Microsoft Graph API Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application in Azure AD
3. Add the following API permissions:
   - Mail.Read
   - Mail.ReadWrite
   - Mail.Send
4. Create a client secret
5. Update the `.env` file with your credentials

### 5. OpenAI API Setup

1. Sign up at [OpenAI](https://platform.openai.com/)
2. Generate an API key
3. Add it to your `.env` file

## 🖥️ Running the Application

### CLI Interface

```bash
# Show available commands
python main.py --help

# Run full pipeline
python main.py pipeline

# Collect emails only
python main.py collect

# Detect newsletters only
python main.py detect

# Generate summary only
python main.py summarize

# Check system status
python main.py status

# Show recent summaries
python main.py summaries

# Show configuration
python main.py config
```

### Web API Interface

```bash
# Start the FastAPI server
python run_api.py
```

The API will be available at:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

### API Endpoints

- `GET /api/health` - System health check
- `POST /api/collect` - Collect emails
- `POST /api/detect` - Detect newsletters  
- `POST /api/summarize` - Generate summary
- `POST /api/pipeline` - Run full pipeline
- `POST /api/manual-summary` - Trigger manual summary
- `GET /api/emails` - List emails
- `GET /api/summaries` - List summaries
- `GET /api/status` - System status

## 🏗️ Architecture Overview

The system follows a multi-agent architecture with these components:

### Agents
- **EmailCollectorAgent**: Collects emails from 4 accounts
- **NewsletterDetectorAgent**: Detects and classifies newsletters
- **ContentSummarizerAgent**: Generates AI-powered summaries
- **SchedulerAgent**: Manages scheduled tasks (daily 8:00 AM)
- **OrchestratorAgent**: Coordinates all other agents

### Services
- **GmailService**: Gmail API integration
- **OutlookService**: Microsoft Graph API integration  
- **AIService**: OpenAI integration for summarization

### Database
- SQLite database for storing emails, newsletters, and summaries
- Automatic schema creation on first run

## 📋 Daily Workflow

1. **8:00 AM Daily Trigger**: Scheduler automatically starts the pipeline
2. **Email Collection**: Connects to all 4 email accounts and collects unread emails
3. **Newsletter Detection**: Uses AI and pattern matching to identify newsletters
4. **Content Summarization**: Generates intelligent summaries in French
5. **Email Delivery**: Sends HTML summary email to configured recipient
6. **Mark as Read**: Automatically marks processed emails as read

## 🛠️ Development

### Project Structure

```
src/
├── agents/          # Multi-agent system components
├── services/        # External service integrations
├── models/          # Data models
├── utils/           # Utilities and configuration
├── api/             # FastAPI web interface
└── db/              # Database models and management
```

### Key Features

- **Multi-Account Support**: 3 Gmail + 1 Hotmail/Outlook
- **Intelligent Detection**: AI-powered newsletter classification
- **French Summarization**: Generates summaries in French
- **Automated Scheduling**: Daily processing at 8:00 AM
- **Web Interface**: FastAPI-based REST API
- **CLI Interface**: Rich command-line interface
- **Health Monitoring**: Comprehensive system health checks

### Configuration Options

Key settings in `.env`:

```env
DAILY_SUMMARY_TIME=08:00
TIMEZONE=Europe/Paris
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000
MIN_CONFIDENCE_SCORE=0.7
MAX_EMAILS_PER_RUN=100
SUMMARY_MAX_NEWSLETTERS=50
LOG_LEVEL=INFO
```

## 🔧 Troubleshooting

### Common Issues

1. **Gmail Authentication Issues**
   - Ensure OAuth credentials are correctly configured
   - Check that Gmail API is enabled in Google Cloud Console
   - Verify the credentials JSON files are accessible

2. **Outlook Authentication Issues**  
   - Confirm Azure AD app permissions are granted
   - Check client ID and secret are correct
   - Ensure the redirect URI is properly configured

3. **OpenAI API Errors**
   - Verify API key is valid and has sufficient credits
   - Check rate limits and token usage
   - Ensure the model name is correct

4. **Database Issues**
   - Check database file permissions
   - Verify SQLite is properly installed
   - Review database logs for schema issues

### Logs

Logs are stored in `logs/newsletters.log` with rotation:
- Daily rotation
- 30-day retention
- Configurable log level

### Health Checks

Use the health endpoint or CLI command to monitor:
- Agent status
- Service connectivity
- Database health
- Scheduler status

## 📄 License

Personal project - Private use only