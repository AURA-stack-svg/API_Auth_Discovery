"""
Data models for API discovery results and related structures.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class AuthStrategy(str, Enum):
    """Supported authentication strategies."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"


class APICategory(str, Enum):
    """API categories for classification."""
    SPORTS = "sports"
    WEATHER = "weather"
    FINANCE = "finance"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    E_COMMERCE = "e_commerce"
    ENTERTAINMENT = "entertainment"
    PRODUCTIVITY = "productivity"
    DEVELOPER_TOOLS = "developer_tools"
    DATA_ANALYTICS = "data_analytics"
    AI_ML = "ai_ml"
    OTHER = "other"


class RateLimitInfo(BaseModel):
    """Rate limiting information for an API."""
    requests_per_minute: Optional[int] = Field(None, description="Requests per minute limit")
    requests_per_hour: Optional[int] = Field(None, description="Requests per hour limit")
    requests_per_day: Optional[int] = Field(None, description="Requests per day limit")
    requests_per_month: Optional[int] = Field(None, description="Requests per month limit")
    burst_limit: Optional[int] = Field(None, description="Burst request limit")
    reset_time: Optional[str] = Field(None, description="Rate limit reset time")
    pricing_tier: Optional[str] = Field(None, description="Pricing tier (free, basic, premium)")


class AuthenticationInfo(BaseModel):
    """Authentication information for an API."""
    strategy: AuthStrategy = Field(..., description="Authentication strategy")
    headers: Dict[str, str] = Field(default_factory=dict, description="Required headers")
    query_params: Dict[str, str] = Field(default_factory=dict, description="Required query parameters")
    api_key: Optional[str] = Field(None, description="API key if available")
    token: Optional[str] = Field(None, description="Bearer token if available")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    oauth_config: Optional[Dict[str, Any]] = Field(None, description="OAuth2 configuration")
    custom_auth: Optional[Dict[str, Any]] = Field(None, description="Custom authentication details")


class EndpointInfo(BaseModel):
    """Information about a specific API endpoint."""
    url: HttpUrl = Field(..., description="Endpoint URL")
    method: str = Field(default="GET", description="HTTP method")
    description: Optional[str] = Field(None, description="Endpoint description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Required parameters")
    response_format: Optional[str] = Field(None, description="Response format (json, xml, etc.)")
    example_response: Optional[Dict[str, Any]] = Field(None, description="Example response")


class CodeExample(BaseModel):
    """Code example for using the API."""
    language: str = Field(..., description="Programming language")
    code: str = Field(..., description="Code snippet")
    description: Optional[str] = Field(None, description="Code description")


class TestResult(BaseModel):
    """Result of API endpoint testing."""
    success: bool = Field(..., description="Whether the test was successful")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    tested_at: datetime = Field(default_factory=datetime.utcnow, description="Test timestamp")


class APIResult(BaseModel):
    """Complete result of API discovery and authentication."""
    
    # Basic API Information
    api_name: str = Field(..., description="Name of the API")
    api_endpoint: HttpUrl = Field(..., description="Base API URL")
    provider: str = Field(..., description="API provider/company name")
    category: APICategory = Field(..., description="API category")
    description: str = Field(..., description="API description")
    
    # Authentication
    authentication: AuthenticationInfo = Field(..., description="Authentication details")
    
    # Documentation and Usage
    documentation_url: Optional[HttpUrl] = Field(None, description="API documentation URL")
    documentation: Optional[str] = Field(None, description="Extracted documentation")
    endpoints: List[EndpointInfo] = Field(default_factory=list, description="Available endpoints")
    
    # Code Examples
    sample_code: List[CodeExample] = Field(default_factory=list, description="Code examples")
    
    # Rate Limiting and Pricing
    rate_limits: Optional[RateLimitInfo] = Field(None, description="Rate limiting information")
    pricing_info: Optional[str] = Field(None, description="Pricing information")
    
    # Testing Results
    test_results: Optional[TestResult] = Field(None, description="API test results")
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp")
    confidence_score: float = Field(default=0.0, description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Source Information
    source_urls: List[HttpUrl] = Field(default_factory=list, description="Source URLs used for discovery")
    search_query: Optional[str] = Field(None, description="Original search query")


class DiscoveryRequest(BaseModel):
    """Request model for API discovery."""
    query: str = Field(..., description="Natural language query for API discovery")
    preferred_providers: Optional[List[str]] = Field(None, description="Preferred API providers")
    auth_strategy: Optional[AuthStrategy] = Field(None, description="Preferred authentication strategy")
    category: Optional[APICategory] = Field(None, description="Preferred API category")
    max_results: int = Field(default=5, description="Maximum number of results to return")
    include_documentation: bool = Field(default=True, description="Include API documentation")
    test_endpoint: bool = Field(default=False, description="Test API endpoints")
    cache_duration: int = Field(default=3600, description="Cache duration in seconds")


class DiscoveryResponse(BaseModel):
    """Response model for API discovery."""
    results: List[APIResult] = Field(..., description="Discovered APIs")
    total_found: int = Field(..., description="Total number of APIs found")
    search_time: float = Field(..., description="Search time in seconds")
    cached: bool = Field(default=False, description="Whether results were cached")
    query: str = Field(..., description="Original search query")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp") 