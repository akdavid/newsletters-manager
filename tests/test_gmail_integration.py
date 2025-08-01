#!/usr/bin/env python3
"""
Simple interactive Gmail test script.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.services.gmail_service import GmailService
from src.models.email import AccountType
from src.utils.logger import get_logger

logger = get_logger("gmail_test")

async def main():
    print("🔐 Gmail Authentication Test")
    print("=" * 40)
    
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    print(f"Using credentials: {credentials_path}")
    
    try:
        gmail_service = GmailService(credentials_path, AccountType.GMAIL_1)
        
        print("\n📧 Authenticating with Gmail...")
        await gmail_service.authenticate()
        
        if gmail_service.service:
            print("✅ Authentication successful!")
            
            # Test basic email fetching
            print("\n📬 Fetching recent emails...")
            messages = await gmail_service.get_unread_messages(max_results=50)
            
            print(f"Found {len(messages)} unread messages")
            
            # Get details for first 10 messages
            emails = []
            print("Processing messages...")
            for i, msg in enumerate(messages[:10]):
                print(f"  Processing message {i+1}/{min(10, len(messages))}...")
                email = await gmail_service.get_message_details(msg['id'])
                if email:
                    emails.append(email)
            
            print(f"\n📋 Found {len(emails)} emails:")
            newsletters = []
            regular_emails = []
            
            for email in emails:
                if email.is_newsletter:
                    newsletters.append(email)
                else:
                    regular_emails.append(email)
            
            print(f"📰 Newsletters: {len(newsletters)}")
            for i, email in enumerate(newsletters, 1):
                print(f"  {i}. {email.subject[:60]}...")
                print(f"     From: {email.sender}")
            
            print(f"\n📧 Regular emails: {len(regular_emails)}")
            for i, email in enumerate(regular_emails, 1):
                print(f"  {i}. {email.subject[:60]}...")
                print(f"     From: {email.sender}")
            
            print(f"\n🎉 Gmail integration works! Total: {len(messages)} unread, processed: {len(emails)}")
            print(f"📊 Newsletter detection: {len(newsletters)}/{len(emails)} emails identified as newsletters")
            
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())