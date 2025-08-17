#!/usr/bin/env python3
"""
Test script to verify configuration loading.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from src.utils.config import get_settings

    print("🔧 Testing configuration loading...")
    settings = get_settings()

    print(f"✅ Configuration loaded successfully!")
    print(f"📧 Gmail credentials path 1: {settings.gmail_credentials_path_1}")
    print(f"🤖 OpenAI model: {settings.openai_model}")
    print(
        f"🔑 OpenAI API key configured: {'Yes' if settings.openai_api_key != 'your_openai_api_key' else 'No - Please set real API key'}"
    )
    print(f"💾 Database URL: {settings.database_url}")

except Exception as e:
    print(f"❌ Configuration loading failed: {e}")
