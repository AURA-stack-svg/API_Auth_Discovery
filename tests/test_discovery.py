"""
Tests for the API discovery engine.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from gallely.core.discovery import APIDiscoveryEngine
from gallely.models.api_result import APICategory


class TestAPIDiscoveryEngine:
    """Test cases for the API discovery engine."""
    
    @pytest.fixture
    def discovery_engine(self):
        """Create a discovery engine instance for testing."""
        return APIDiscoveryEngine()
    
    @pytest.fixture
    def mock_tavily_response(self):
        """Mock Tavily search response."""
        return {
            "results": [
                {
                    "url": "https://api.example.com/docs",
                    "title": "Example API Documentation",
                    "content": "This is a REST API for sports data with API key authentication.",
                    "raw_content": "API endpoint: https://api.example.com/v1/ Authentication: API key required"
                },
                {
                    "url": "https://developer.sportsapi.com",
                    "title": "Sports API - Developer Portal",
                    "content": "Real-time sports scores and statistics API. Free tier available.",
                    "raw_content": "Base URL: https://api.sportsapi.com Rate limit: 1000 requests per day"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_search_apis_success(self, discovery_engine, mock_tavily_response):
        """Test successful API search."""
        
        with patch.object(discovery_engine.tavily_client, 'search', return_value=mock_tavily_response):
            results = await discovery_engine.search_apis(
                query="NBA live scores API",
                max_results=5,
                category=APICategory.SPORTS
            )
            
            assert len(results) > 0
            assert all('api_name' in result for result in results)
            assert all('provider' in result for result in results)
            assert all('relevance_score' in result for result in results)
    
    @pytest.mark.asyncio
    async def test_search_apis_empty_results(self, discovery_engine):
        """Test API search with no results."""
        
        empty_response = {"results": []}
        
        with patch.object(discovery_engine.tavily_client, 'search', return_value=empty_response):
            results = await discovery_engine.search_apis(
                query="nonexistent API",
                max_results=5
            )
            
            assert len(results) == 0
    
    def test_enhance_query(self, discovery_engine):
        """Test query enhancement functionality."""
        
        enhanced = discovery_engine._enhance_query(
            query="basketball scores",
            category=APICategory.SPORTS,
            preferred_providers=["espn", "nba"]
        )
        
        assert "basketball scores" in enhanced
        assert "API" in enhanced
        assert "sports" in enhanced.lower()
        assert "espn API" in enhanced
    
    def test_calculate_api_relevance_score(self, discovery_engine):
        """Test API relevance scoring."""
        
        # High relevance case
        high_score = discovery_engine._calculate_api_relevance_score(
            url="https://api.sports.com/docs",
            title="Sports API Documentation",
            content="REST API for live sports scores with API key authentication",
            raw_content="Endpoint: GET /scores Rate limit: 1000/day",
            query="sports scores API"
        )
        
        # Low relevance case
        low_score = discovery_engine._calculate_api_relevance_score(
            url="https://example.com/blog",
            title="Random Blog Post",
            content="This is just a regular blog post about cooking",
            raw_content="No API content here",
            query="sports scores API"
        )
        
        assert high_score > low_score
        assert high_score > 0.5
        assert low_score < 0.3
    
    def test_extract_api_name(self, discovery_engine):
        """Test API name extraction."""
        
        # Test with clear API title
        name1 = discovery_engine._extract_api_name(
            title="Sports Data API - Documentation",
            url="https://api.sports.com",
            content="Sports API content"
        )
        assert "Sports Data API" in name1
        
        # Test with URL-based extraction
        name2 = discovery_engine._extract_api_name(
            title="Developer Portal",
            url="https://developer.weatherapi.com",
            content="Weather data"
        )
        assert "weatherapi" in name2.lower()
    
    def test_detect_auth_strategy(self, discovery_engine):
        """Test authentication strategy detection."""
        
        # Test API key detection
        api_key_text = "Authentication requires an API key in the X-API-Key header"
        auth_strategy = discovery_engine._detect_auth_strategy(api_key_text)
        assert auth_strategy.value == "api_key"
        
        # Test OAuth2 detection
        oauth_text = "Uses OAuth2 with client_id and client_secret"
        auth_strategy = discovery_engine._detect_auth_strategy(oauth_text)
        assert auth_strategy.value == "oauth2"
        
        # Test Bearer token detection
        bearer_text = "Send requests with Bearer token in Authorization header"
        auth_strategy = discovery_engine._detect_auth_strategy(bearer_text)
        assert auth_strategy.value == "bearer_token"
    
    def test_categorize_api(self, discovery_engine):
        """Test API categorization."""
        
        # Test sports categorization
        sports_category = discovery_engine._categorize_api(
            text="NBA basketball scores and player statistics",
            query="basketball API"
        )
        assert sports_category == APICategory.SPORTS
        
        # Test weather categorization
        weather_category = discovery_engine._categorize_api(
            text="Weather forecast and temperature data",
            query="weather API"
        )
        assert weather_category == APICategory.WEATHER
        
        # Test finance categorization
        finance_category = discovery_engine._categorize_api(
            text="Stock prices and cryptocurrency trading data",
            query="crypto API"
        )
        assert finance_category == APICategory.FINANCE
    
    def test_extract_rate_limits(self, discovery_engine):
        """Test rate limit extraction."""
        
        text_with_limits = """
        API Rate Limits:
        - 1000 requests per day
        - 100 requests per hour
        - Free tier available
        """
        
        rate_limits = discovery_engine._extract_rate_limits(text_with_limits)
        
        assert rate_limits is not None
        assert rate_limits.get("requests_per_day") == 1000
        assert rate_limits.get("requests_per_hour") == 100
        assert rate_limits.get("pricing_tier") == "free"
    
    @pytest.mark.asyncio
    async def test_process_search_results(self, discovery_engine, mock_tavily_response):
        """Test search results processing."""
        
        processed = await discovery_engine._process_search_results(
            search_response=mock_tavily_response,
            original_query="sports API",
            category=APICategory.SPORTS,
            preferred_providers=None
        )
        
        assert len(processed) > 0
        
        # Check that results are sorted by relevance
        if len(processed) > 1:
            assert processed[0]["relevance_score"] >= processed[1]["relevance_score"]
        
        # Check required fields
        for result in processed:
            assert "api_name" in result
            assert "provider" in result
            assert "relevance_score" in result
            assert "source_url" in result


@pytest.mark.asyncio
async def test_discovery_engine_integration():
    """Integration test for the discovery engine."""
    
    # This test requires actual API keys, so we'll mock it
    engine = APIDiscoveryEngine()
    
    mock_response = {
        "results": [
            {
                "url": "https://api.openweathermap.org/data/2.5/weather",
                "title": "OpenWeatherMap API",
                "content": "Weather data API with free tier",
                "raw_content": "API key required, 1000 calls/day free"
            }
        ]
    }
    
    with patch.object(engine.tavily_client, 'search', return_value=mock_response):
        results = await engine.search_apis(
            query="weather API",
            max_results=1,
            category=APICategory.WEATHER
        )
        
        assert len(results) == 1
        result = results[0]
        assert result["category"] == APICategory.WEATHER
        assert "weather" in result["api_name"].lower() or "weather" in result["description"].lower() 