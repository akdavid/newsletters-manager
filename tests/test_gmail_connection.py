#!/usr/bin/env python3
"""
Gmail connection test script for all configured accounts.
Only tests authentication and basic connectivity, without newsletter detection.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.models.email import AccountType
from src.services.gmail_service import GmailService
from src.utils.logger import get_logger

logger = get_logger("gmail_connection_test")


async def test_gmail_account(
    credentials_path: str, account_type: AccountType, account_name: str
):
    """Test connection to a single Gmail account."""
    print(f"\n🔐 Testing {account_name}")
    print("-" * 40)

    if not credentials_path or not os.path.exists(credentials_path):
        print(f"⚠️  Credentials file not found: {credentials_path}")
        return False

    try:
        gmail_service = GmailService(credentials_path, account_type)

        print(f"📂 Using credentials: {os.path.basename(credentials_path)}")
        print("🔑 Authenticating...")

        await gmail_service.authenticate()

        if gmail_service.service:
            print("✅ Authentication successful!")

            # Test basic API call (get profile info)
            print("📊 Testing API access...")
            try:
                profile = (
                    gmail_service.service.users().getProfile(userId="me").execute()
                )
                email_address = profile.get("emailAddress", "Unknown")
                total_messages = profile.get("messagesTotal", 0)

                print(f"📧 Email: {email_address}")
                print(f"📬 Total messages: {total_messages}")

                # Test fetching a small number of messages (just to verify access)
                print("🔍 Testing message access...")
                messages = await gmail_service.get_unread_messages(max_results=5)
                print(f"📨 Found {len(messages)} recent unread messages")

                print("✅ Connection test successful!")
                return True

            except Exception as api_error:
                print(f"❌ API access failed: {api_error}")
                return False
        else:
            print("❌ Authentication failed")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Connection error: {error_msg}")

        # Provide specific guidance for common OAuth errors
        if "invalid_request" in error_msg or "Error 400" in error_msg:
            print("\n🔧 OAuth Error - Possible solutions:")
            print("1. Add this email as a test user in Google Cloud Console:")
            print("   - Go to APIs & Services > OAuth consent screen")
            print("   - Scroll to 'Test users' section")
            print("   - Add the Gmail account you're trying to connect")
            print("2. Or publish your app to make it available to all users")
            print(
                "3. Make sure you're using the same email that owns the Gmail account"
            )

        return False


async def main():
    print("🔐 Gmail Connection Test")
    print("=" * 50)
    print(
        "Testing authentication and basic connectivity for all configured Gmail accounts"
    )
    print("(This test does NOT perform newsletter detection)")
    print()

    # Test all configured Gmail accounts
    test_results = []

    # Gmail Account 1
    credentials_1 = os.getenv("GMAIL_CREDENTIALS_PATH_1")
    if credentials_1:
        result = await test_gmail_account(
            credentials_1, AccountType.GMAIL_1, "Gmail Account 1"
        )
        test_results.append(("Gmail Account 1", result))
    else:
        print("\n⚠️  GMAIL_CREDENTIALS_PATH_1 not configured")
        test_results.append(("Gmail Account 1", False))

    # Gmail Account 2
    credentials_2 = os.getenv("GMAIL_CREDENTIALS_PATH_2")
    if credentials_2:
        result = await test_gmail_account(
            credentials_2, AccountType.GMAIL_2, "Gmail Account 2"
        )
        test_results.append(("Gmail Account 2", result))
    else:
        print("\n⚠️  GMAIL_CREDENTIALS_PATH_2 not configured")
        test_results.append(("Gmail Account 2", False))

    # Gmail Account 3
    credentials_3 = os.getenv("GMAIL_CREDENTIALS_PATH_3")
    if credentials_3:
        result = await test_gmail_account(
            credentials_3, AccountType.GMAIL_3, "Gmail Account 3"
        )
        test_results.append(("Gmail Account 3", result))
    else:
        print("\n⚠️  GMAIL_CREDENTIALS_PATH_3 not configured")
        test_results.append(("Gmail Account 3", False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    successful_tests = 0
    for account_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{account_name}: {status}")
        if success:
            successful_tests += 1

    print(
        f"\n🎯 Result: {successful_tests}/{len(test_results)} accounts configured and working"
    )

    if successful_tests == 0:
        print("\n🔧 Setup required:")
        print("1. Configure at least one Gmail account in your .env file")
        print("2. Download OAuth2 credentials from Google Cloud Console")
        print("3. Update GMAIL_CREDENTIALS_PATH_X variables")
    elif successful_tests < len(
        [
            r
            for r in test_results
            if os.getenv(
                f"GMAIL_CREDENTIALS_PATH_{['1','2','3'][test_results.index(r)]}"
            )
        ]
    ):
        print("\n🔧 Some accounts need attention - check error messages above")
    else:
        print("\n🎉 All configured Gmail accounts are working correctly!")
        print("You can now run the full newsletter processing pipeline.")


if __name__ == "__main__":
    asyncio.run(main())
