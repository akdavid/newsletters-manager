from pydantic import BaseSettings, Field
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Gmail API Configuration
    gmail_credentials_path_1: str = Field(..., env="GMAIL_CREDENTIALS_PATH_1")
    gmail_credentials_path_2: str = Field(..., env="GMAIL_CREDENTIALS_PATH_2")
    gmail_credentials_path_3: str = Field(..., env="GMAIL_CREDENTIALS_PATH_3")
    
    # Microsoft Graph API Configuration
    outlook_client_id: str = Field(..., env="OUTLOOK_CLIENT_ID")
    outlook_client_secret: str = Field(..., env="OUTLOOK_CLIENT_SECRET")
    outlook_tenant_id: str = Field("common", env="OUTLOOK_TENANT_ID")
    outlook_email: str = Field(..., env="OUTLOOK_EMAIL")
    
    # OpenAI API Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(1000, env="OPENAI_MAX_TOKENS")
    
    # Database Configuration
    database_url: str = Field("sqlite:///newsletters.db", env="DATABASE_URL")
    
    # Scheduling Configuration
    daily_summary_time: str = Field("08:00", env="DAILY_SUMMARY_TIME")
    timezone: str = Field("Europe/Paris", env="TIMEZONE")
    
    # Email Configuration for sending summaries
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: str = Field(..., env="SMTP_USERNAME")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    summary_recipient: str = Field(..., env="SUMMARY_RECIPIENT")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/newsletters.log", env="LOG_FILE")
    
    # Processing Configuration
    max_emails_per_run: int = Field(100, env="MAX_EMAILS_PER_RUN")
    summary_max_newsletters: int = Field(50, env="SUMMARY_MAX_NEWSLETTERS")
    
    # Newsletter Detection Configuration
    min_confidence_score: float = Field(0.7, env="MIN_CONFIDENCE_SCORE")
    
    # API Rate Limiting
    gmail_requests_per_minute: int = Field(100, env="GMAIL_REQUESTS_PER_MINUTE")
    outlook_requests_per_minute: int = Field(60, env="OUTLOOK_REQUESTS_PER_MINUTE")
    openai_requests_per_minute: int = Field(20, env="OPENAI_REQUESTS_PER_MINUTE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def gmail_credentials_paths(self) -> List[str]:
        return [
            self.gmail_credentials_path_1,
            self.gmail_credentials_path_2,
            self.gmail_credentials_path_3
        ]

    @property
    def all_credentials_exist(self) -> bool:
        return all(os.path.exists(path) for path in self.gmail_credentials_paths)

    def get_gmail_credentials_path(self, account_index: int) -> str:
        if account_index < 0 or account_index >= len(self.gmail_credentials_paths):
            raise ValueError(f"Invalid Gmail account index: {account_index}")
        return self.gmail_credentials_paths[account_index]


def get_settings() -> Settings:
    return Settings()