#!/usr/bin/env python3
"""
Outlook/Microsoft Graph connection test script.
Tests authentication and basic connectivity for the configured Outlook account.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

load_dotenv()

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.services.outlook_service import OutlookService
from src.utils.logger import get_logger

logger = get_logger("outlook_connection_test")

async def test_outlook_connection():
    """Test connection to the configured Outlook account."""
    print("🔐 Outlook Connection Test")
    print("=" * 50)
    print("Testing authentication and basic connectivity for Microsoft Graph API")
    print()
    
    # Get configuration from environment
    client_id = os.getenv("OUTLOOK_CLIENT_ID")
    client_secret = os.getenv("OUTLOOK_CLIENT_SECRET") 
    tenant_id = os.getenv("OUTLOOK_TENANT_ID")
    outlook_email = os.getenv("OUTLOOK_EMAIL")
    
    print(f"📧 Email: {outlook_email}")
    print(f"🆔 Client ID: {client_id[:8]}...{client_id[-8:] if client_id else 'Not set'}")
    print(f"🔑 Client Secret: {'✅ Set' if client_secret and client_secret != 'your_outlook_client_secret' else '❌ Not configured'}")
    print(f"🏢 Tenant ID: {tenant_id[:8]}...{tenant_id[-8:] if tenant_id else 'Not set'}")
    print()
    
    # Check if all required variables are configured
    if not all([client_id, client_secret, tenant_id, outlook_email]):
        missing = []
        if not client_id or client_id == 'your_outlook_client_id':
            missing.append('OUTLOOK_CLIENT_ID')
        if not client_secret or client_secret == 'your_outlook_client_secret':
            missing.append('OUTLOOK_CLIENT_SECRET')
        if not tenant_id or tenant_id == 'your_tenant_id':
            missing.append('OUTLOOK_TENANT_ID')
        if not outlook_email or outlook_email == 'your_hotmail_email@hotmail.com':
            missing.append('OUTLOOK_EMAIL')
            
        print("❌ Outlook configuration incomplete!")
        print(f"Missing or invalid variables: {', '.join(missing)}")
        print("\nPlease update your .env file with valid values from Azure Portal")
        return False
    
    try:
        print("🔌 Initializing Outlook service...")
        outlook_service = OutlookService(client_id, client_secret, tenant_id)
        
        print("🔑 Authenticating with Microsoft Graph...")
        await outlook_service.authenticate()
        
        print("✅ Authentication successful!")
        
        print("📊 Testing API access...")
        
        # First test basic user info (simpler API call)
        print("🔍 Testing user profile access...")
        try:
            # Test a simple Graph API call first
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {outlook_service.access_token}",
                    "Content-Type": "application/json"
                }
                async with session.get("https://graph.microsoft.com/v1.0/me", headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        mail_address = user_data.get('mail', user_data.get('userPrincipalName', 'No email'))
                        print(f"✅ User: {user_data.get('displayName', 'Unknown')} ({mail_address})")
                        
                        # Check if this account has mail capabilities
                        if not user_data.get('mail') and 'hotmail' in str(user_data.get('userPrincipalName', '')).lower():
                            print("⚠️  Note: Personal accounts sometimes have limited Graph API mail access")
                            print("💡 Your account might need to be accessed differently")
                    else:
                        error_text = await response.text()
                        print(f"❌ User profile error {response.status}: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ User profile test failed: {e}")
            return False
        
        # Test mail access
        print("📧 Testing mail access...")
        
        # Try a simpler mail API call first
        print("🔍 Testing basic mail folder access...")
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {outlook_service.access_token}",
                    "Content-Type": "application/json"
                }
                # Try to access mailFolders first (simpler call)
                async with session.get("https://graph.microsoft.com/v1.0/me/mailFolders", headers=headers) as response:
                    if response.status == 200:
                        folders_data = await response.json()
                        print(f"✅ Found {len(folders_data.get('value', []))} mail folders")
                    else:
                        error_text = await response.text()
                        print(f"❌ Mail folders error {response.status}: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Mail folders test failed: {e}")
            return False
        
        # Now try to get messages
        print("📨 Testing message access (Inbox only)...")
        try:
            messages = await outlook_service.get_unread_messages(max_results=10)
        except Exception as e:
            # Try a simpler messages call manually
            print("🔍 Trying basic messages API call...")
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {outlook_service.access_token}",
                        "Content-Type": "application/json"
                    }
                    # Simple messages call without complex filters
                    async with session.get("https://graph.microsoft.com/v1.0/me/messages?$top=3", headers=headers) as response:
                        if response.status == 200:
                            msgs_data = await response.json()
                            messages = msgs_data.get('value', [])
                            print(f"✅ Manual API call successful: Found {len(messages)} messages")
                        else:
                            error_text = await response.text()
                            print(f"❌ Messages API error {response.status}: {error_text}")
                            print("🔧 This might be a permissions issue in Azure Portal")
                            return False
            except Exception as manual_e:
                print(f"❌ Manual messages test failed: {manual_e}")
                return False
        
        print(f"📨 Found {len(messages)} recent unread messages")
        
        if messages:
            print("\n📋 Sample messages:")
            for i, msg in enumerate(messages[:3], 1):
                subject = msg.get('subject', 'No subject')[:50]
                sender = msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown sender')
                print(f"  {i}. {subject}... (from: {sender})")
        
        print("\n✅ Outlook connection test successful!")
        print("🎉 Microsoft Graph API is working correctly!")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Connection error: {error_msg}")
        
        # Provide specific guidance for common errors
        if "AADSTS" in error_msg:
            print("\n🔧 Azure AD Error - Possible solutions:")
            if "invalid_client" in error_msg:
                print("- Double-check your Client ID and Client Secret in .env file")
                print("- Verify the client secret hasn't expired in Azure Portal")
            elif "unauthorized_client" in error_msg:
                print("- Check API permissions in Azure Portal (Mail.Read, Mail.ReadWrite)")
                print("- Make sure admin consent was granted")
            elif "invalid_scope" in error_msg:
                print("- Verify Microsoft Graph API permissions are configured")
                
        elif "DeviceCodeCredential" in error_msg or "device flow" in error_msg:
            print("\n🔧 Device Flow Authentication:")
            print("- You may need to complete authentication in your browser")
            print("- Check if a browser window opened for authentication")
            
        elif "timeout" in error_msg.lower():
            print("\n🔧 Network/Timeout Error:")
            print("- Check your internet connection")
            print("- Try again in a few minutes")
            
        print(f"\n💡 For detailed error information, check the logs or Azure Portal")
        return False

async def main():
    success = await test_outlook_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎯 RESULT: ✅ Outlook connection working!")
        print("You can now use the Outlook service in your newsletter pipeline.")
    else:
        print("🎯 RESULT: ❌ Outlook connection failed")
        print("Please fix the configuration and try again.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())