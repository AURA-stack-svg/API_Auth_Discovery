"""
Configuration management for the API Discovery Service.
"""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys (Required)
    tavily_api_key: str = Field(..., description="Tavily API key for web search")
    openai_api_key: str = Field(..., description="OpenAI API key for LLM processing")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./api_discovery.db",
        description="Database connection URL"
    )
    
    # Redis Configuration (Optional)
    redis_url: Optional[str] = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    )
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Application Settings
    app_name: str = Field(default="API Discovery & Auth Service", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(..., description="Secret key for encryption")
    
    # Browser Automation Settings
    browser_headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_timeout: int = Field(default=60, description="Browser operation timeout in seconds")
    max_signup_attempts: int = Field(default=3, description="Maximum signup attempts per API")
    browser_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="Browser user agent string"
    )
    
    # API Discovery Settings
    max_search_results: int = Field(default=10, description="Maximum search results to return")
    search_timeout: int = Field(default=30, description="Search timeout in seconds")
    default_search_depth: str = Field(default="advanced", description="Default Tavily search depth")
    include_raw_content: bool = Field(default=True, description="Include raw content in search results")
    
    # Rate Limiting
    requests_per_minute: int = Field(default=60, description="Requests per minute limit")
    burst_limit: int = Field(default=10, description="Burst request limit")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    
    # Caching Settings
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    max_cache_size: int = Field(default=1000, description="Maximum cache size")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    
    # Security Settings
    encrypt_api_keys: bool = Field(default=True, description="Encrypt stored API keys")
    api_key_encryption_key: str = Field(..., description="Encryption key for API keys")
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    
    # Email Configuration (Optional)
    smtp_host: Optional[str] = Field(default=None, description="SMTP host for notifications")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    
    # Monitoring and Analytics
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=8001, description="Metrics server port")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Development Settings
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    workers: int = Field(default=1, description="Number of worker processes")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings() 