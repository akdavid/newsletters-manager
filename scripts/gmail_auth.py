#!/usr/bin/env python3
"""
Simple Gmail authentication script using localhost redirect.
This should work better than the 'oob' flow.
"""

import os
import pickle
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

def authenticate_gmail(credentials_path: str):
    """Authenticate Gmail using the simpler InstalledAppFlow."""
    
    token_path = credentials_path.replace('.json', '_token.pickle')
    
    print(f"🔐 Authenticating Gmail with: {credentials_path}")
    print("=" * 60)
    
    creds = None
    
    # Load existing token
    if os.path.exists(token_path):
        print("📋 Loading existing credentials...")
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired credentials...")
            try:
                creds.refresh(Request())
                print("✅ Credentials refreshed successfully!")
            except Exception as e:
                print(f"❌ Refresh failed: {e}")
                print("🔄 Starting new authentication...")
                creds = None
        
        if not creds:
            print("🚀 Starting OAuth2 authentication...")
            print("📋 This will open a web browser for authentication...")
            
            # Use InstalledAppFlow which handles the redirect better
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            
            # This will open a browser and handle the callback
            creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
            print("✅ Authentication completed!")
        
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
            print(f"💾 Credentials saved to: {token_path}")
    else:
        print("✅ Using existing valid credentials")
    
    # Test the credentials
    try:
        print("\n🧪 Testing Gmail API access...")
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        print(f"✅ Successfully connected to Gmail: {email_address}")
        
        # Test basic functionality
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        message_count = len(results.get('messages', []))
        print(f"📧 Found {message_count} recent messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        return False

def main():
    """Set up Gmail authentication."""
    
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH_1')
    
    if not credentials_path or credentials_path == '/path/to/gmail1_credentials.json':
        # Fallback to the actual file we found
        credentials_path = 'client_secret_158365814465-81kq7i54gcsfg3gq266nh491mh6fee6j.apps.googleusercontent.com.json'
    
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        print("💡 Make sure your Gmail credentials JSON file is in the project root")
        return
    
    print("🚀 Gmail Authentication Setup")
    print("=" * 40)
    print("This will:")
    print("1. Open your web browser")
    print("2. Ask you to log in to Gmail")
    print("3. Save credentials for automated daily use")
    print()
    
    if authenticate_gmail(credentials_path):
        print("\n🎉 Gmail authentication setup completed successfully!")
        print("\n💡 Next steps:")
        print("1. Test the integration: python tests/test_gmail_integration.py")
        print("2. Run daily processing: python src/main.py pipeline")
    else:
        print("\n❌ Gmail authentication setup failed!")

if __name__ == "__main__":
    main()