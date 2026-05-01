"""
Core API discovery module using Tavily search.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from tavily import TavilyClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.api_result import APIResult, APICategory, AuthStrategy, EndpointInfo
from ..core.config import settings


class APIDiscoveryEngine:
    """Engine for discovering APIs using Tavily search."""
    
    def __init__(self):
        self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        self.api_patterns = self._load_api_patterns()
        
    def _load_api_patterns(self) -> Dict[str, Any]:
        """Load patterns for identifying API-related content."""
        return {
            "api_indicators": [
                r"api\..*\.com",
                r"developer\..*\.com",
                r"docs\..*\.com/api",
                r".*\.com/api",
                r"rest api",
                r"graphql",
                r"webhook",
                r"endpoint",
                r"api key",
                r"authentication",
                r"rate limit"
            ],
            "auth_patterns": {
                "api_key": [
                    r"api[_\s]?key",
                    r"x-api-key",
                    r"authorization.*key",
                    r"token.*header"
                ],
                "oauth2": [
                    r"oauth\s?2",
                    r"client[_\s]?id",
                    r"client[_\s]?secret",
                    r"access[_\s]?token",
                    r"refresh[_\s]?token"
                ],
                "bearer_token": [
                    r"bearer\s?token",
                    r"authorization.*bearer",
                    r"jwt\s?token"
                ]
            },
            "endpoint_patterns": [
                r"https?://[^\s]+/api[^\s]*",
                r"https?://api\.[^\s]+",
                r"GET|POST|PUT|DELETE|PATCH\s+/[^\s]+"
            ]
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_apis(
        self,
        query: str,
        max_results: int = 10,
        category: Optional[APICategory] = None,
        preferred_providers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for APIs using Tavily."""
        
        # Enhance query for better API discovery
        enhanced_query = self._enhance_query(query, category, preferred_providers)
        
        logger.info(f"Searching for APIs with query: {enhanced_query}")
        
        try:
            # Use Tavily's advanced search with API-specific parameters
            search_params = {
                "query": enhanced_query,
                "search_depth": settings.default_search_depth,
                "max_results": max_results,
                "include_raw_content": settings.include_raw_content,
                "include_images": False,  # Not needed for API discovery
                "include_answer": True,   # Get AI-generated answer
            }
            
            # Add domain filtering for better API results
            api_domains = [
                "*.com/api*",
                "api.*",
                "developer.*",
                "docs.*",
                "rapidapi.com",
                "postman.com",
                "github.com"
            ]
            search_params["include_domains"] = api_domains
            
            response = self.tavily_client.search(**search_params)
            
            # Process and filter results
            processed_results = await self._process_search_results(
                response, query, category, preferred_providers
            )
            
            logger.info(f"Found {len(processed_results)} relevant API results")
            return processed_results
            
        except Exception as e:
            logger.error(f"Error searching APIs: {str(e)}")
            raise
    
    def _enhance_query(
        self,
        query: str,
        category: Optional[APICategory] = None,
        preferred_providers: Optional[List[str]] = None
    ) -> str:
        """Enhance the search query for better API discovery."""
        
        enhanced_parts = [query]
        
        # Add API-specific terms
        if "api" not in query.lower():
            enhanced_parts.append("API")
        
        # Add category-specific terms
        if category:
            category_terms = {
                APICategory.SPORTS: ["sports", "games", "scores", "statistics"],
                APICategory.WEATHER: ["weather", "forecast", "climate", "meteorology"],
                APICategory.FINANCE: ["finance", "stock", "trading", "market", "crypto"],
                APICategory.NEWS: ["news", "articles", "headlines", "media"],
                APICategory.SOCIAL_MEDIA: ["social", "posts", "followers", "engagement"],
                APICategory.E_COMMERCE: ["ecommerce", "products", "shopping", "inventory"],
                APICategory.ENTERTAINMENT: ["entertainment", "movies", "music", "games"],
                APICategory.PRODUCTIVITY: ["productivity", "tasks", "calendar", "notes"],
                APICategory.DEVELOPER_TOOLS: ["developer", "tools", "code", "repository"],
                APICategory.DATA_ANALYTICS: ["analytics", "data", "metrics", "insights"],
                APICategory.AI_ML: ["ai", "machine learning", "ml", "artificial intelligence"]
            }
            
            if category in category_terms:
                enhanced_parts.extend(category_terms[category][:2])  # Add top 2 terms
        
        # Add preferred providers
        if preferred_providers:
            for provider in preferred_providers[:3]:  # Limit to top 3
                enhanced_parts.append(f"{provider} API")
        
        # Add common API terms for better discovery
        enhanced_parts.extend(["REST API", "documentation", "developer"])
        
        return " ".join(enhanced_parts)
    
    async def _process_search_results(
        self,
        search_response: Dict[str, Any],
        original_query: str,
        category: Optional[APICategory] = None,
        preferred_providers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Process and filter Tavily search results for API relevance."""
        
        results = search_response.get("results", [])
        processed_results = []
        
        for result in results:
            try:
                # Extract basic information
                url = result.get("url", "")
                title = result.get("title", "")
                content = result.get("content", "")
                raw_content = result.get("raw_content", "")
                
                # Check if this looks like an API-related result
                api_score = self._calculate_api_relevance_score(
                    url, title, content, raw_content, original_query
                )
                
                if api_score < 0.3:  # Skip low-relevance results
                    continue
                
                # Extract API information
                api_info = await self._extract_api_info(
                    url, title, content, raw_content, original_query
                )
                
                if api_info:
                    api_info["relevance_score"] = api_score
                    api_info["source_url"] = url
                    processed_results.append(api_info)
                    
            except Exception as e:
                logger.warning(f"Error processing search result: {str(e)}")
                continue
        
        # Sort by relevance score
        processed_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return processed_results
    
    def _calculate_api_relevance_score(
        self,
        url: str,
        title: str,
        content: str,
        raw_content: str,
        query: str
    ) -> float:
        """Calculate how relevant a search result is to API discovery."""
        
        score = 0.0
        text_to_analyze = f"{url} {title} {content} {raw_content}".lower()
        
        # URL-based scoring
        if any(pattern in url.lower() for pattern in ["api.", "/api", "developer.", "docs."]):
            score += 0.3
        
        # Title-based scoring
        if "api" in title.lower():
            score += 0.2
        
        # Content-based scoring using patterns
        for pattern in self.api_patterns["api_indicators"]:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                score += 0.1
        
        # Authentication method detection
        for auth_type, patterns in self.api_patterns["auth_patterns"].items():
            for pattern in patterns:
                if re.search(pattern, text_to_analyze, re.IGNORECASE):
                    score += 0.05
        
        # Endpoint detection
        for pattern in self.api_patterns["endpoint_patterns"]:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                score += 0.1
        
        # Query relevance
        query_words = query.lower().split()
        for word in query_words:
            if word in text_to_analyze:
                score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def _extract_api_info(
        self,
        url: str,
        title: str,
        content: str,
        raw_content: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Extract structured API information from search results."""
        
        try:
            # Combine all text for analysis
            full_text = f"{title} {content} {raw_content}"
            
            # Extract API name
            api_name = self._extract_api_name(title, url, content)
            
            # Extract provider/company name
            provider = self._extract_provider_name(url, title, content)
            
            # Detect authentication strategy
            auth_strategy = self._detect_auth_strategy(full_text)
            
            # Extract endpoints
            endpoints = self._extract_endpoints(full_text, url)
            
            # Categorize the API
            category = self._categorize_api(full_text, query)
            
            # Extract rate limiting info
            rate_limits = self._extract_rate_limits(full_text)
            
            # Extract documentation URL
            doc_url = self._extract_documentation_url(url, full_text)
            
            return {
                "api_name": api_name,
                "provider": provider,
                "category": category,
                "description": content[:500],  # Truncate description
                "auth_strategy": auth_strategy,
                "endpoints": endpoints,
                "rate_limits": rate_limits,
                "documentation_url": doc_url,
                "base_url": self._extract_base_url(url, full_text),
                "pricing_info": self._extract_pricing_info(full_text)
            }
            
        except Exception as e:
            logger.warning(f"Error extracting API info: {str(e)}")
            return None
    
    def _extract_api_name(self, title: str, url: str, content: str) -> str:
        """Extract the API name from various sources."""
        
        # Try to extract from title first
        title_clean = re.sub(r'\s*-\s*.*$', '', title)  # Remove subtitle
        title_clean = re.sub(r'\s*\|\s*.*$', '', title_clean)  # Remove site name
        
        if "api" in title_clean.lower():
            return title_clean.strip()
        
        # Try to extract from URL
        url_parts = url.split('/')
        for part in url_parts:
            if 'api' in part.lower() and len(part) > 3:
                return part.replace('-', ' ').replace('_', ' ').title()
        
        # Fallback to title
        return title_clean.strip() or "Unknown API"
    
    def _extract_provider_name(self, url: str, title: str, content: str) -> str:
        """Extract the provider/company name."""
        
        # Extract from domain
        domain_match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            # Remove common prefixes
            domain = re.sub(r'^(api|developer|docs)\.', '', domain)
            return domain.replace('-', ' ').title()
        
        return "Unknown Provider"
    
    def _detect_auth_strategy(self, text: str) -> AuthStrategy:
        """Detect the authentication strategy from text."""
        
        text_lower = text.lower()
        
        # Check for OAuth2
        if any(pattern in text_lower for pattern in ["oauth", "client_id", "client_secret"]):
            return AuthStrategy.OAUTH2
        
        # Check for API key
        if any(pattern in text_lower for pattern in ["api key", "x-api-key", "apikey"]):
            return AuthStrategy.API_KEY
        
        # Check for Bearer token
        if any(pattern in text_lower for pattern in ["bearer token", "jwt", "access token"]):
            return AuthStrategy.BEARER_TOKEN
        
        # Check for basic auth
        if any(pattern in text_lower for pattern in ["basic auth", "username", "password"]):
            return AuthStrategy.BASIC_AUTH
        
        return AuthStrategy.API_KEY  # Default assumption
    
    def _extract_endpoints(self, text: str, base_url: str) -> List[Dict[str, Any]]:
        """Extract API endpoints from text."""
        
        endpoints = []
        
        # Look for URL patterns
        url_patterns = re.findall(r'https?://[^\s<>"]+', text)
        for url in url_patterns:
            if '/api' in url.lower():
                endpoints.append({
                    "url": url,
                    "method": "GET",  # Default
                    "description": "Discovered endpoint"
                })
        
        # Look for path patterns
        path_patterns = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s<>"]+)', text, re.IGNORECASE)
        for method, path in path_patterns:
            full_url = f"{base_url.rstrip('/')}{path}"
            endpoints.append({
                "url": full_url,
                "method": method.upper(),
                "description": f"{method.upper()} endpoint"
            })
        
        return endpoints[:5]  # Limit to 5 endpoints
    
    def _categorize_api(self, text: str, query: str) -> APICategory:
        """Categorize the API based on content and query."""
        
        text_lower = f"{text} {query}".lower()
        
        category_keywords = {
            APICategory.AI_ML: [
                "openai", "anthropic", "claude", "gpt", "llm", "language model", 
                "machine learning", "artificial intelligence", "neural", "embedding",
                "completion", "chat", "vision", "speech", "text generation"
            ],
            APICategory.FINANCE: [
                "finance", "stock", "trading", "market", "crypto", "currency", "price",
                "payment", "stripe", "paypal", "banking", "investment", "portfolio",
                "forex", "blockchain", "wallet", "transaction", "billing"
            ],
            APICategory.DEVELOPER_TOOLS: [
                "github", "gitlab", "bitbucket", "repository", "code", "deployment",
                "ci/cd", "docker", "kubernetes", "aws", "azure", "gcp", "cloud",
                "monitoring", "logging", "analytics", "database", "api gateway"
            ],
            APICategory.DATA_ANALYTICS: [
                "analytics", "data", "metric", "insight", "report", "dashboard",
                "business intelligence", "visualization", "tracking", "conversion",
                "segment", "mixpanel", "amplitude", "google analytics"
            ],
            APICategory.E_COMMERCE: [
                "ecommerce", "product", "shop", "cart", "order", "payment", "inventory",
                "shopify", "woocommerce", "magento", "fulfillment", "shipping",
                "customer", "subscription", "marketplace"
            ],
            APICategory.PRODUCTIVITY: [
                "productivity", "task", "calendar", "note", "todo", "project",
                "slack", "teams", "notion", "airtable", "trello", "asana",
                "document", "collaboration", "workflow", "automation"
            ],
            APICategory.SOCIAL_MEDIA: [
                "social", "post", "follow", "like", "share", "tweet", "instagram",
                "facebook", "linkedin", "tiktok", "youtube", "influencer",
                "engagement", "content", "media", "viral"
            ],
            APICategory.SPORTS: ["sport", "game", "score", "team", "player", "match", "nba", "nfl", "soccer"],
            APICategory.WEATHER: ["weather", "forecast", "temperature", "climate", "rain", "snow"],
            APICategory.NEWS: ["news", "article", "headline", "media", "press", "journalism"],
            APICategory.ENTERTAINMENT: ["entertainment", "movie", "music", "video", "streaming"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return APICategory.OTHER
    
    def _extract_rate_limits(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract rate limiting information from text."""
        
        rate_info = {}
        
        # Look for rate limit patterns
        rate_patterns = [
            (r'(\d+)\s*requests?\s*per\s*minute', 'requests_per_minute'),
            (r'(\d+)\s*requests?\s*per\s*hour', 'requests_per_hour'),
            (r'(\d+)\s*requests?\s*per\s*day', 'requests_per_day'),
            (r'(\d+)\s*requests?\s*per\s*month', 'requests_per_month'),
        ]
        
        for pattern, key in rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_info[key] = int(match.group(1))
        
        # Look for pricing tiers
        if any(term in text.lower() for term in ["free", "basic", "premium", "enterprise"]):
            if "free" in text.lower():
                rate_info["pricing_tier"] = "free"
            elif "premium" in text.lower():
                rate_info["pricing_tier"] = "premium"
            else:
                rate_info["pricing_tier"] = "basic"
        
        return rate_info if rate_info else None
    
    def _extract_documentation_url(self, source_url: str, text: str) -> Optional[str]:
        """Extract documentation URL."""
        
        # If the source URL looks like documentation, use it
        if any(term in source_url.lower() for term in ["docs", "documentation", "api"]):
            return source_url
        
        # Look for documentation links in text
        doc_patterns = [
            r'https?://[^\s<>"]*docs[^\s<>"]*',
            r'https?://[^\s<>"]*documentation[^\s<>"]*',
            r'https?://[^\s<>"]*api[^\s<>"]*'
        ]
        
        for pattern in doc_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return source_url  # Fallback to source URL
    
    def _extract_base_url(self, source_url: str, text: str) -> str:
        """Extract the base API URL."""
        
        # Look for API URLs in text
        api_urls = re.findall(r'https?://api\.[^\s<>"]+', text)
        if api_urls:
            return api_urls[0].split('/')[0] + '//' + api_urls[0].split('/')[2]
        
        # Look for URLs with /api path
        api_path_urls = re.findall(r'https?://[^\s<>"]*/api', text)
        if api_path_urls:
            return api_path_urls[0]
        
        # Fallback to domain from source URL
        domain_match = re.search(r'https?://[^/]+', source_url)
        if domain_match:
            return domain_match.group(0)
        
        return source_url
    
    def _extract_pricing_info(self, text: str) -> Optional[str]:
        """Extract pricing information from text."""
        
        pricing_keywords = ["free", "paid", "subscription", "tier", "plan", "pricing", "$", "cost"]
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in pricing_keywords):
                return sentence.strip()[:200]  # Return first relevant sentence, truncated
        
        return None 