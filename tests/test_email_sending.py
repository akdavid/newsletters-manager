#!/usr/bin/env python3
"""
Simple email test script to verify SMTP configuration.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def test_email_sending():
    """Test SMTP email sending with current configuration."""

    print("🧪 Testing Email Configuration")
    print("=" * 40)

    # Get SMTP settings from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("SUMMARY_RECIPIENT")

    print(f"📧 SMTP Host: {smtp_host}:{smtp_port}")
    print(f"👤 Username: {smtp_username}")
    print(f"📬 Recipient: {recipient}")
    print(
        f"🔐 Password: {'✅ Set' if smtp_password and smtp_password != 'your_app_password_here' else '❌ Not configured'}"
    )
    print()

    if (
        not smtp_username
        or not smtp_password
        or smtp_password == "your_app_password_here"
    ):
        print("❌ Email configuration incomplete!")
        print("Please update your .env file with:")
        print("- SMTP_USERNAME=your_gmail@gmail.com")
        print("- SMTP_PASSWORD=your_16_character_app_password")
        print("- SUMMARY_RECIPIENT=recipient@gmail.com")
        return False

    try:
        print("🔌 Connecting to SMTP server...")

        # Create message
        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = recipient
        msg["Subject"] = "🧪 Newsletter Manager - Email Test"

        body = (
            """
        <html>
        <body>
            <h2>✅ Email Test Successful!</h2>
            <p>Your Newsletter Manager email configuration is working correctly.</p>
            <p><strong>SMTP Configuration:</strong></p>
            <ul>
                <li>Host: """
            + smtp_host
            + """</li>
                <li>Port: """
            + str(smtp_port)
            + """</li>
                <li>Username: """
            + smtp_username
            + """</li>
            </ul>
            <p>🎉 You're ready to receive automated newsletter summaries!</p>
        </body>
        </html>
        """
        )

        msg.attach(MIMEText(body, "html"))

        # Connect and send
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)

        server.send_message(msg)
        server.quit()

        print("✅ Email sent successfully!")
        print(f"📬 Check your inbox at {recipient}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("🔧 Troubleshooting:")
        print(
            "1. Make sure you created a Gmail App Password (not your regular password)"
        )
        print("2. Enable 2-Factor Authentication on your Google account")
        print("3. Generate App Password at: https://myaccount.google.com/apppasswords")
        print("4. Use the 16-character app password in your .env file")
        return False

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False


if __name__ == "__main__":
    success = test_email_sending()
    if success:
        print("\n🎉 Email configuration is working!")
        print("You can now run the newsletter pipeline and receive summaries by email.")
    else:
        print("\n🔧 Please fix the email configuration and try again.")
