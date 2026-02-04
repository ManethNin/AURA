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
    
    # Operation Mode
    LOCAL_MODE: bool = True  # Set to True for local file system operations
    LOCAL_WORKSPACE_PATH: Optional[str] = None  # Base path for local repositories
    PIPELINE_LOG_PATH: Optional[str] = None  # Path for pipeline logs (default: ./logs/pipeline)
    
    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "aura"
    
    # GitHub App (Optional - only needed when LOCAL_MODE=False)
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_PRIVATE_KEY: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_URL: str

    # LLM Configuration
    LLM_PROVIDER: str = "groq"  # Options: "groq" or "gemini"
    
    # Groq Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Gemini Configuration
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    
    # General LLM Settings
    LLM_MAX_RECURSION: int = 30
    LLM_TEMPERATURE: float = 0.0

    # API Change Analysis (REVAPI / JApiCmp)
    API_CHANGE_TOOL: str = "revapi"  # Options: "revapi", "japicmp", "none"
    REVAPI_HOME: Optional[str] = None  # Path to REVAPI installation
    REVAPI_EXECUTABLE: Optional[str] = "revapi"  # Path or command to revapi
    REVAPI_ARGS_TEMPLATE: Optional[str] = "--configuration {config} analyze"
    JAPICMP_JAR_PATH: Optional[str] = None
    JAPICMP_ARGS_TEMPLATE: Optional[str] = "--old {old_jar} --new {new_jar} --output-format json"
    MAVEN_EXECUTABLE: str = "mvn"
    
    # App Config
    MAX_REPAIR_ATTEMPTS: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

# Global settings instance
settings = Settings()
