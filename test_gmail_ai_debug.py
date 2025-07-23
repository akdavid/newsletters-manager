#!/usr/bin/env python3
"""
Test script for AI newsletter detection with debug.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(str(Path(__file__).parent / "src"))

from src.services.gmail_service import GmailService
from src.models.email import AccountType
from src.utils.logger import get_logger

# Configure logging
logger = get_logger("gmail_ai_test")

async def main():
    print("🤖 Gmail AI Classification Test")
    print("=" * 40)
    
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    print(f"Using credentials: {credentials_path}")
    
    try:
        gmail_service = GmailService(credentials_path, AccountType.GMAIL_1)
        
        print("\n📧 Authenticating with Gmail...")
        await gmail_service.authenticate()
        
        if gmail_service.service:
            print("✅ Authentication successful!")
            print(f"🤖 AI Service available: {'Yes' if gmail_service.ai_service else 'No'}")
            
            # Test on just one email for debugging
            print("\n📬 Fetching one email for AI test...")
            messages = await gmail_service.get_unread_messages(max_results=1)
            
            if messages:
                print("Processing 1 email...")
                email = await gmail_service.get_message_details(messages[0]['id'])
                
                if email:
                    print(f"\n📧 Email details:")
                    print(f"  Subject: {email.subject}")
                    print(f"  From: {email.sender}")
                    print(f"  Is Newsletter (AI): {'Yes' if email.is_newsletter else 'No'}")
                    print(f"  Content preview: {email.content_text[:200]}...")
                else:
                    print("❌ Failed to get email details")
            else:
                print("No emails found")
            
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())