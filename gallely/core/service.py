"""
Main API Discovery Service that orchestrates the entire process.
"""

import asyncio
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger

from ..models.api_result import (
    APIResult, DiscoveryRequest, DiscoveryResponse,
    AuthStrategy, APICategory, AuthenticationInfo,
    EndpointInfo, CodeExample, TestResult, RateLimitInfo
)
from ..core.discovery import APIDiscoveryEngine
from ..core.browser_automation import BrowserAuthAgent
from ..core.code_generator import CodeGenerator
from ..core.cache import CacheManager
from ..core.config import settings


class APIDiscoveryService:
    """Main service for API discovery and authentication."""
    
    def __init__(self):
        self.discovery_engine = APIDiscoveryEngine()
        self.browser_agent = BrowserAuthAgent()
        self.code_generator = CodeGenerator()
        self.cache_manager = CacheManager() if settings.cache_enabled else None
        
    async def discover(
        self,
        query: str,
        preferred_providers: Optional[List[str]] = None,
        auth_strategy: Optional[AuthStrategy] = None,
        category: Optional[APICategory] = None,
        max_results: int = 5,
        include_documentation: bool = True,
        test_endpoint: bool = False,
        cache_duration: int = 3600
    ) -> DiscoveryResponse:
        """
        Main method to discover APIs and handle authentication.
        
        Args:
            query: Natural language description of needed API
            preferred_providers: List of preferred API providers
            auth_strategy: Preferred authentication strategy
            category: API category filter
            max_results: Maximum number of results to return
            include_documentation: Whether to include API documentation
            test_endpoint: Whether to test API endpoints
            cache_duration: Cache duration in seconds
            
        Returns:
            DiscoveryResponse with discovered and authenticated APIs
        """
        
        start_time = time.time()
        logger.info(f"Starting API discovery for query: {query}")
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(
                query, preferred_providers, auth_strategy, category, max_results
            )
            
            if self.cache_manager:
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info("Returning cached result")
                    cached_result.cached = True
                    return cached_result
            
            # Step 1: Discover APIs using Tavily
            discovered_apis = await self.discovery_engine.search_apis(
                query=query,
                max_results=max_results * 2,  # Get more to filter later
                category=category,
                preferred_providers=preferred_providers
            )
            
            if not discovered_apis:
                logger.warning("No APIs discovered")
                return DiscoveryResponse(
                    results=[],
                    total_found=0,
                    search_time=time.time() - start_time,
                    query=query
                )
            
            # Step 2: Process each discovered API
            api_results = []
            for api_info in discovered_apis[:max_results]:
                try:
                    api_result = await self._process_api(
                        api_info=api_info,
                        query=query,
                        auth_strategy=auth_strategy,
                        include_documentation=include_documentation,
                        test_endpoint=test_endpoint
                    )
                    
                    if api_result:
                        api_results.append(api_result)
                        
                except Exception as e:
                    logger.warning(f"Error processing API {api_info.get('api_name', 'Unknown')}: {str(e)}")
                    continue
            
            # Step 3: Build response
            response = DiscoveryResponse(
                results=api_results,
                total_found=len(api_results),
                search_time=time.time() - start_time,
                query=query,
                cached=False
            )
            
            # Cache the result
            if self.cache_manager and api_results:
                await self.cache_manager.set(cache_key, response, cache_duration)
            
            logger.info(f"Discovery completed. Found {len(api_results)} APIs in {response.search_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Error in API discovery: {str(e)}")
            return DiscoveryResponse(
                results=[],
                total_found=0,
                search_time=time.time() - start_time,
                query=query
            )
    
    async def search_apis(
        self,
        query: str,
        category: Optional[APICategory] = None,
        preferred_providers: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for APIs without authentication."""
        
        return await self.discovery_engine.search_apis(
            query=query,
            max_results=max_results,
            category=category,
            preferred_providers=preferred_providers
        )
    
    async def authenticate_api(
        self,
        api_info: Dict[str, Any],
        auth_strategy: Optional[AuthStrategy] = None
    ) -> AuthenticationInfo:
        """Handle authentication for a specific API."""
        
        return await self.browser_agent.authenticate_api(
            api_info=api_info,
            auth_strategy=auth_strategy
        )
    
    async def batch_discover(
        self,
        queries: List[str],
        max_results_per_query: int = 3
    ) -> Dict[str, DiscoveryResponse]:
        """Discover APIs for multiple queries in parallel."""
        
        logger.info(f"Starting batch discovery for {len(queries)} queries")
        
        # Create tasks for parallel execution
        tasks = []
        for query in queries:
            task = self.discover(
                query=query,
                max_results=max_results_per_query,
                test_endpoint=False  # Skip testing for batch operations
            )
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build response dictionary
        response_dict = {}
        for i, (query, result) in enumerate(zip(queries, results)):
            if isinstance(result, Exception):
                logger.error(f"Error in batch discovery for query '{query}': {str(result)}")
                response_dict[query] = DiscoveryResponse(
                    results=[],
                    total_found=0,
                    search_time=0,
                    query=query
                )
            else:
                response_dict[query] = result
        
        logger.info(f"Batch discovery completed for {len(queries)} queries")
        return response_dict
    
    async def _process_api(
        self,
        api_info: Dict[str, Any],
        query: str,
        auth_strategy: Optional[AuthStrategy] = None,
        include_documentation: bool = True,
        test_endpoint: bool = False
    ) -> Optional[APIResult]:
        """Process a single discovered API."""
        
        api_name = api_info.get("api_name", "Unknown API")
        logger.info(f"Processing API: {api_name}")
        
        try:
            # Step 1: Authenticate with the API
            auth_info = await self.browser_agent.authenticate_api(
                api_info=api_info,
                auth_strategy=auth_strategy
            )
            
            # Step 2: Generate code examples
            code_examples = await self.code_generator.generate_code_examples(
                api_info=api_info,
                auth_info=auth_info
            )
            
            # Step 3: Build endpoints list
            endpoints = self._build_endpoints(api_info)
            
            # Step 4: Test endpoint if requested
            test_result = None
            if test_endpoint and endpoints:
                test_result = await self._test_first_endpoint(endpoints[0], auth_info)
            
            # Step 5: Extract rate limiting info
            rate_limits = self._build_rate_limits(api_info)
            
            # Step 6: Build the complete API result
            api_result = APIResult(
                api_name=api_name,
                api_endpoint=api_info.get("base_url", ""),
                provider=api_info.get("provider", "Unknown Provider"),
                category=api_info.get("category", APICategory.OTHER),
                description=api_info.get("description", ""),
                authentication=auth_info,
                documentation_url=api_info.get("documentation_url"),
                documentation=api_info.get("description", "") if include_documentation else None,
                endpoints=endpoints,
                sample_code=code_examples,
                rate_limits=rate_limits,
                pricing_info=api_info.get("pricing_info"),
                test_results=test_result,
                confidence_score=api_info.get("relevance_score", 0.0),
                source_urls=[api_info.get("source_url", "")],
                search_query=query,
                metadata={
                    "discovery_method": "tavily_search",
                    "auth_method": "browser_automation",
                    "processed_at": datetime.utcnow().isoformat()
                }
            )
            
            return api_result
            
        except Exception as e:
            logger.error(f"Error processing API {api_name}: {str(e)}")
            return None
    
    def _build_endpoints(self, api_info: Dict[str, Any]) -> List[EndpointInfo]:
        """Build endpoint information from API info."""
        
        endpoints = []
        raw_endpoints = api_info.get("endpoints", [])
        
        for endpoint_data in raw_endpoints:
            try:
                endpoint = EndpointInfo(
                    url=endpoint_data.get("url", ""),
                    method=endpoint_data.get("method", "GET"),
                    description=endpoint_data.get("description", ""),
                    parameters={},
                    response_format="json"
                )
                endpoints.append(endpoint)
            except Exception as e:
                logger.warning(f"Error building endpoint: {str(e)}")
                continue
        
        # If no endpoints found, create a default one
        if not endpoints and api_info.get("base_url"):
            endpoints.append(EndpointInfo(
                url=api_info["base_url"],
                method="GET",
                description="Base API endpoint",
                parameters={},
                response_format="json"
            ))
        
        return endpoints
    
    def _build_rate_limits(self, api_info: Dict[str, Any]) -> Optional[RateLimitInfo]:
        """Build rate limiting information from API info."""
        
        rate_data = api_info.get("rate_limits")
        if not rate_data:
            return None
        
        try:
            return RateLimitInfo(
                requests_per_minute=rate_data.get("requests_per_minute"),
                requests_per_hour=rate_data.get("requests_per_hour"),
                requests_per_day=rate_data.get("requests_per_day"),
                requests_per_month=rate_data.get("requests_per_month"),
                pricing_tier=rate_data.get("pricing_tier")
            )
        except Exception as e:
            logger.warning(f"Error building rate limits: {str(e)}")
            return None
    
    async def _test_first_endpoint(
        self,
        endpoint: EndpointInfo,
        auth_info: AuthenticationInfo
    ) -> Optional[TestResult]:
        """Test the first endpoint of an API."""
        
        try:
            test_data = await self.browser_agent.test_api_endpoint(
                endpoint_url=str(endpoint.url),
                auth_info=auth_info,
                method=endpoint.method
            )
            
            return TestResult(
                success=test_data.get("success", False),
                status_code=test_data.get("status_code"),
                response_time=test_data.get("response_time"),
                error_message=test_data.get("error_message")
            )
            
        except Exception as e:
            logger.warning(f"Error testing endpoint: {str(e)}")
            return TestResult(
                success=False,
                error_message=str(e)[:200]
            )
    
    def _generate_cache_key(
        self,
        query: str,
        preferred_providers: Optional[List[str]],
        auth_strategy: Optional[AuthStrategy],
        category: Optional[APICategory],
        max_results: int
    ) -> str:
        """Generate a cache key for the request."""
        
        import hashlib
        
        key_parts = [
            query.lower().strip(),
            str(sorted(preferred_providers) if preferred_providers else ""),
            str(auth_strategy.value if auth_strategy else ""),
            str(category.value if category else ""),
            str(max_results)
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get_api_status(self, api_name: str) -> Dict[str, Any]:
        """Get the status of a previously discovered API."""
        
        # This would typically query a database of discovered APIs
        # For now, return a placeholder
        return {
            "api_name": api_name,
            "status": "unknown",
            "last_tested": None,
            "success_rate": None
        }
    
    async def refresh_api_credentials(self, api_name: str) -> AuthenticationInfo:
        """Refresh credentials for a specific API."""
        
        # This would re-run the authentication process
        # For now, return a placeholder
        return AuthenticationInfo(
            strategy=AuthStrategy.API_KEY,
            headers={"X-API-Key": "refreshed_key"},
            query_params={}
        ) 