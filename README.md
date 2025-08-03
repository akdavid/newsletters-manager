# Newsletter Manager

<div align="center">
  <img src="assets/logo.png" alt="Newsletter Manager Logo" width="300"/>
  
  An intelligent newsletter management system using AI-powered detection and multi-agent architecture to automate email processing and generate smart daily summaries.
</div>

## 🎯 Overview

Newsletter Manager is a sophisticated multi-agent system that automatically:
- **Connects to multiple email accounts** (Gmail + Outlook support)
- **Intelligently detects newsletters** using AI classification
- **Generates daily summaries** with OpenAI integration
- **Automatically marks processed emails** as read
- **Provides REST API** for manual control and monitoring

## ✨ Features

### 🤖 AI-Powered Newsletter Detection
- Advanced content analysis using OpenAI GPT models
- Pattern recognition for newsletter identification
- Confidence scoring and detailed classification reasons
- Support for multiple newsletter types (tech, business, education, etc.)

### 📧 Multi-Account Email Integration
- **Gmail API** integration with OAuth2 authentication
- **Microsoft Graph API** for Outlook/Hotmail accounts
- Parallel processing of multiple email accounts
- Secure credential management

### 🕐 Automated Scheduling
- Daily summary generation at configurable times
- Manual triggering via API endpoints
- Persistent task scheduling with APScheduler

### 🏗️ Multi-Agent Architecture
- **EmailCollectorAgent**: Fetches emails from configured accounts
- **NewsletterDetectorAgent**: AI-powered newsletter classification
- **ContentSummarizerAgent**: Generates intelligent summaries
- **SchedulerAgent**: Manages automated tasks
- **OrchestratorAgent**: Coordinates all system components

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (optimized for Apple Silicon M2)
- Gmail API credentials
- OpenAI API key
- (Optional) Microsoft Graph API credentials for Outlook

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/newsletters-manager.git
   cd newsletters-manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\\Scripts\\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and credentials
   ```

5. **Set up Gmail credentials**
   
   **For each Gmail account you want to connect:**
   
   a) **Create OAuth2 Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Desktop application"
   - Name: "Newsletter Manager Gmail X" (where X is 1, 2, 3)
   - Download the credentials JSON file
   - Place it in the project root with descriptive names
   
   b) **Configure OAuth Consent Screen:**
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" user type
   - Fill in app information (name: "Newsletter Manager")
   - Add scopes: `https://www.googleapis.com/auth/gmail.readonly` and `https://www.googleapis.com/auth/gmail.modify`
   
   c) **Add Test Users (IMPORTANT):**
   - In the OAuth consent screen, scroll to "Test users"
   - Click "ADD USERS"
   - Add ALL Gmail account emails you want to connect
   - Click "SAVE"
   
   **Alternative:** Publish your app to avoid test user limitations
   
   d) **Update `.env` file:**
   ```bash
   GMAIL_CREDENTIALS_PATH_1=path/to/gmail1_credentials.json
   GMAIL_CREDENTIALS_PATH_2=path/to/gmail2_credentials.json
   GMAIL_CREDENTIALS_PATH_3=path/to/gmail3_credentials.json
   ```

6. **Set up Microsoft Graph API** (Optional for Outlook)
   - Go to [Azure Portal](https://portal.azure.com/)
   - Register a new application in Azure AD
   - Add API permissions: Mail.Read, Mail.ReadWrite, Mail.Send
   - Create a client secret
   - Update the `.env` file with your credentials

7. **Set up OpenAI API**
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key
   - Add it to your `.env` file

### Configuration

Edit your `.env` file:

```env
# Gmail API Configuration
GMAIL_CREDENTIALS_PATH_1=your_gmail_credentials.json

# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Optional: Microsoft Graph API
OUTLOOK_CLIENT_ID=your_outlook_client_id
OUTLOOK_CLIENT_SECRET=your_outlook_client_secret

# Database Configuration
DATABASE_URL=sqlite:///newsletters.db

# Scheduling Configuration
DAILY_SUMMARY_TIME=08:00
TIMEZONE=Europe/Paris
```

## 🧪 Testing

### Run Tests

Test Gmail connections (all configured accounts):
```bash
python tests/test_gmail_connection.py
```

Test configuration:
```bash
python tests/test_config.py
```

Test email sending (SMTP configuration):
```bash
python tests/test_email_sending.py
```


### Expected Output

**Gmail Connection Test:**
1. ✅ Test authentication for all configured Gmail accounts
2. 📊 Verify API access and basic functionality
3. 📈 Display summary of working/failed accounts

**Configuration Test:**
1. ✅ Validate all environment variables
2. 🔧 Check file paths and credentials existence

**Email Sending Test:**
1. ✅ Verify SMTP configuration
2. 📧 Send test email to configured recipient
3. 🔧 Provide troubleshooting guidance if issues occur

## 🏃‍♂️ Usage

### Command Line Interface

The system provides a rich CLI interface for all operations:

**Run the complete newsletter processing pipeline:**
```bash
python main.py pipeline
```

**Individual processing steps:**
```bash
# Collect emails from all configured accounts
python main.py collect

# Detect newsletters in collected emails
python main.py detect

# Generate AI summaries for detected newsletters
python main.py summarize
```

**View results:**
```bash
# View recent newsletter summaries
python main.py summaries

# Show system status and health
python main.py status

# Show current configuration
python main.py config
```

### View Generated Summaries

**Option 1: CLI Command**
```bash
python main.py summaries --limit 5
```

**Option 2: Export to HTML File**
```bash
# Export the latest summary to an HTML file
sqlite3 newsletters.db "SELECT content FROM summaries ORDER BY generation_date DESC LIMIT 1;" > latest_summary.html

# Open in your browser
open latest_summary.html  # macOS
```

**Option 3: Direct Database Query**
```bash
# View summary metadata
sqlite3 newsletters.db "SELECT id, title, status, newsletters_count, generation_date FROM summaries;"

# View summary content
sqlite3 newsletters.db "SELECT content FROM summaries WHERE id='your_summary_id';"
```

### Summary Format

Generated summaries include:
- **📊 Categorized newsletters** by type (TECH, BUSINESS, EDUCATION, HEALTH, etc.)
- **🇫🇷 French summaries** of each newsletter (2-3 sentences)
- **🎨 Styled HTML output** with responsive design
- **📈 Processing statistics** and metadata
- **🔗 Source tracking** with sender information

**Example categories detected:**
- **TECH**: AI frameworks, research labs, technology companies
- **BUSINESS**: Professional updates, job opportunities, industry news  
- **EDUCATION**: Online courses, cybersecurity training, MOOCs
- **HEALTH**: Medical research, scientific breakthroughs
- **NEWS**: Current events, scientific advances
- **ENTERTAINMENT**: Humor, lifestyle content

### Start the FastAPI Server
```bash
# Using the provided script
python src/run_api.py

# Or directly with uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

Core endpoints:
- `GET /api/health` - System health check
- `GET /api/status` - System and agent status
- `GET /api/emails` - List collected emails
- `GET /api/summaries` - Get summary history

Processing endpoints:
- `POST /api/collect` - Collect emails from all accounts
- `POST /api/detect` - Detect newsletters in collected emails
- `POST /api/summarize` - Generate AI summaries
- `POST /api/pipeline` - Run full processing pipeline

The API documentation is available at `http://localhost:8000/docs` when the server is running.

## 📁 Project Structure

```
newsletters-manager/
├── assets/                     # Static assets (logo, etc.)
├── src/
│   ├── agents/                # Multi-agent system components
│   │   ├── base_agent.py      # Abstract base class
│   │   ├── email_collector.py # Email collection logic
│   │   ├── newsletter_detector.py # AI newsletter detection
│   │   ├── content_summarizer.py # Summary generation
│   │   ├── scheduler.py       # Task scheduling
│   │   └── orchestrator.py    # Agent coordination
│   ├── services/              # External service integrations
│   │   ├── gmail_service.py   # Gmail API integration
│   │   ├── outlook_service.py # Microsoft Graph API
│   │   └── ai_service.py      # OpenAI integration
│   ├── models/                # Data models
│   │   ├── email.py          # Email data structures
│   │   ├── newsletter.py     # Newsletter models
│   │   └── summary.py        # Summary models
│   ├── utils/                 # Utility functions
│   │   ├── config.py         # Configuration management
│   │   ├── logger.py         # Logging setup
│   │   └── helpers.py        # Helper functions
│   ├── api/                   # FastAPI REST interface
│   └── db/                    # Database models and setup
├── tests/                     # Test scripts
│   ├── test_gmail_integration.py # Gmail integration test
│   └── test_config.py        # Configuration test
├── docs/                      # Documentation
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── CLAUDE.md                 # Development guidelines
```

## 🔧 Development

### Code Quality
```bash
# Run linting
flake8 src/ tests/
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 🤖 AI Integration

### Newsletter Detection
The system uses OpenAI's language models to intelligently classify emails:

- **Content Analysis**: Examines email content, structure, and metadata
- **Pattern Recognition**: Identifies newsletter-specific patterns
- **Type Classification**: Categorizes newsletters (tech, business, education, etc.)
- **Confidence Scoring**: Provides reliability metrics for classifications

### Summary Generation
AI-powered summarization provides:
- **Concise Summaries**: 2-3 sentence summaries in French
- **Key Points Extraction**: Bullet-point highlights
- **HTML Output**: Formatted daily digest emails
- **Multi-Newsletter Aggregation**: Grouped by category

## 📊 Monitoring

### Logging
Structured logging with Loguru:
- Email processing events
- AI classification results
- API request/response logs
- Error tracking and debugging

### Health Checks
- Agent status monitoring
- Database connectivity
- External API availability
- Processing statistics

## 🛡️ Security

- **OAuth2 Authentication** for email APIs
- **Environment-based** credential management
- **Token Refresh** handling
- **No credential storage** in repository
- **Encrypted** sensitive data handling

## 🔧 Troubleshooting

### Common Issues

**Gmail Authentication Issues**

*Error: "Accès bloqué : la demande de Newsletter Manager n'est pas valide" or "Error 400: invalid_request"*
- **Root cause:** Gmail account not added as test user in Google Cloud Console
- **Solution 1:** Add test users:
  1. Go to Google Cloud Console → APIs & Services → OAuth consent screen
  2. Scroll to "Test users" section
  3. Click "ADD USERS" and add all Gmail accounts you want to connect
  4. Click "SAVE"
- **Solution 2:** Publish your app:
  1. In OAuth consent screen, click "PUBLISH APP"
  2. Confirm publishing (makes app available to any Google account)

*Other authentication issues:*
- Ensure OAuth credentials are correctly configured in Google Cloud Console
- Check that Gmail API is enabled
- Verify the credentials JSON file path in `.env`
- Make sure you're using the correct Gmail account during OAuth flow

**OpenAI API Errors**  
- Verify API key is valid and has sufficient credits
- Check rate limits and token usage
- Ensure the model name is correct (gpt-4o-mini)

**Configuration Issues**
- Run `python tests/test_config.py` to verify configuration
- Check all required environment variables are set
- Ensure file paths are correct and accessible

### Logs
Logs are automatically created in `logs/newsletters.log` with structured JSON format for easy debugging.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

<div align="center">
  <strong>Newsletter Manager</strong> - Intelligent Email Processing with AI
</div>