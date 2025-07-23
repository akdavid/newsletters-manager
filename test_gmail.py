#!/usr/bin/env python3
"""
Test script for Gmail API integration with single account.
This script tests authentication and basic email collection functionality.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent / "src"))

from src.services.gmail_service import GmailService
from src.utils.logger import get_logger

logger = get_logger("gmail_test")

async def test_gmail_authentication():
    """Test Gmail API authentication."""
    logger.info("Testing Gmail authentication...")
    
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    if not credentials_path:
        logger.error("GMAIL_CREDENTIALS_PATH_1 not found in environment variables")
        return False
    
    if not os.path.exists(credentials_path):
        logger.error(f"Credentials file not found: {credentials_path}")
        return False
    
    try:
        from src.models.email import AccountType
        gmail_service = GmailService(credentials_path, AccountType.GMAIL_1)
        service = await gmail_service.authenticate()
        
        if service:
            logger.info("✅ Gmail authentication successful!")
            return True
        else:
            logger.error("❌ Gmail authentication failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Authentication error: {str(e)}")
        return False

async def test_email_collection():
    """Test basic email collection."""
    logger.info("Testing email collection...")
    
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    
    try:
        from src.models.email import AccountType
        gmail_service = GmailService(credentials_path, AccountType.GMAIL_1)
        
        # Get recent emails (last 5)
        logger.info("Fetching recent emails...")
        emails = await gmail_service.get_emails(max_results=5, query="newer_than:1d")
        
        if emails:
            logger.info(f"✅ Successfully collected {len(emails)} emails")
            
            # Show basic info about collected emails
            for i, email in enumerate(emails, 1):
                logger.info(f"Email {i}:")
                logger.info(f"  Subject: {email.subject[:50]}...")
                logger.info(f"  From: {email.sender}")
                logger.info(f"  Date: {email.date}")
                logger.info(f"  Is Newsletter: {email.is_newsletter}")
                logger.info(f"  ---")
            
            return True
        else:
            logger.warning("⚠️  No emails found (this might be normal if no recent emails)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Email collection error: {str(e)}")
        return False

async def test_newsletter_detection():
    """Test newsletter detection on collected emails."""
    logger.info("Testing newsletter detection...")
    
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    
    try:
        from src.models.email import AccountType
        gmail_service = GmailService(credentials_path, AccountType.GMAIL_1)
        
        # Get emails with broader query to find newsletters
        logger.info("Fetching emails for newsletter detection...")
        emails = await gmail_service.get_emails(
            max_results=10, 
            query="newer_than:7d"  # Last week to increase chances of finding newsletters
        )
        
        if emails:
            newsletters = [email for email in emails if email.is_newsletter]
            
            logger.info(f"Found {len(newsletters)} newsletters out of {len(emails)} emails")
            
            if newsletters:
                logger.info("Newsletter examples:")
                for newsletter in newsletters[:3]:  # Show first 3
                    logger.info(f"  📧 {newsletter.subject[:60]}...")
                    logger.info(f"     From: {newsletter.sender}")
                    logger.info(f"     ---")
            
            return True
        else:
            logger.warning("No emails found for newsletter detection test")
            return True
            
    except Exception as e:
        logger.error(f"❌ Newsletter detection error: {str(e)}")
        return False

async def main():
    """Run all Gmail tests."""
    logger.info("🚀 Starting Gmail API tests...")
    logger.info("=" * 50)
    
    # Test 1: Authentication
    auth_success = await test_gmail_authentication()
    if not auth_success:
        logger.error("Authentication failed - stopping tests")
        return
    
    print()  # Add spacing
    
    # Test 2: Email Collection
    collection_success = await test_email_collection()
    
    print()  # Add spacing
    
    # Test 3: Newsletter Detection
    detection_success = await test_newsletter_detection()
    
    print()  # Add spacing
    logger.info("=" * 50)
    
    if auth_success and collection_success and detection_success:
        logger.info("🎉 All Gmail tests completed successfully!")
        logger.info("Your Gmail integration is working correctly.")
    else:
        logger.warning("⚠️  Some tests had issues - check the logs above")

if __name__ == "__main__":
    asyncio.run(main())