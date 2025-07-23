# Tests

This directory contains test scripts for the Newsletter Manager project.

## Test Scripts

### `test_gmail_integration.py`
Complete integration test for Gmail functionality including:
- Gmail API authentication
- Email collection and processing  
- AI-powered newsletter detection
- Displays results with newsletter categorization

**Usage:**
```bash
cd tests/
python test_gmail_integration.py
```

### `test_config.py`
Configuration validation test to verify:
- Environment variables loading
- Settings configuration
- API keys validation

**Usage:**
```bash
cd tests/
python test_config.py
```

## Prerequisites

Before running tests, ensure you have:
1. Configured your `.env` file with required API keys
2. Set up Gmail OAuth credentials
3. Activated the Python virtual environment
4. Installed all dependencies

## Running Tests

From the project root:
```bash
# Activate virtual environment
source .venv/bin/activate

# Run Gmail integration test
python tests/test_gmail_integration.py

# Run configuration test
python tests/test_config.py
```