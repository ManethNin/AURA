"""
Application configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # Application
    APP_NAME: str = "AURA - Automated Dependency Repair"
    DEBUG: bool = False
    
    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "aura"
    
    # GitHub App
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_URL:str

    # LLM Configuration
    GROQ_API_KEY: str
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_MAX_RECURSION: int = 30
    LLM_TEMPERATURE: float = 0.0
    
    # App Config
    MAX_REPAIR_ATTEMPTS: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

# Global settings instance
settings = Settings()
