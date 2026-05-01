#!/usr/bin/env python3
"""
Web API client example for the API Discovery Service.

This script demonstrates how to interact with the FastAPI web service.
"""

import asyncio
import httpx
import json
from typing import Dict, Any


class APIDiscoveryClient:
    """Client for the API Discovery Service web API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def discover_apis(
        self,
        query: str,
        max_results: int = 5,
        preferred_providers: list = None,
        auth_strategy: str = None,
        category: str = None,
        include_documentation: bool = True,
        test_endpoint: bool = False
    ) -> Dict[str, Any]:
        """Discover APIs using the web API."""
        
        payload = {
            "query": query,
            "max_results": max_results,
            "include_documentation": include_documentation,
            "test_endpoint": test_endpoint
        }
        
        if preferred_providers:
            payload["preferred_providers"] = preferred_providers
        if auth_strategy:
            payload["auth_strategy"] = auth_strategy
        if category:
            payload["category"] = category
        
        response = await self.client.post(
            f"{self.base_url}/discover",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def search_apis(
        self,
        query: str,
        max_results: int = 10,
        category: str = None,
        preferred_providers: list = None
    ) -> list:
        """Search for APIs without authentication."""
        
        params = {
            "query": query,
            "max_results": max_results
        }
        
        if category:
            params["category"] = category
        if preferred_providers:
            params["preferred_providers"] = preferred_providers
        
        response = await self.client.post(
            f"{self.base_url}/search",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def batch_discover(
        self,
        queries: list,
        max_results_per_query: int = 3
    ) -> Dict[str, Any]:
        """Discover APIs for multiple queries."""
        
        payload = {
            "queries": queries,
            "max_results_per_query": max_results_per_query
        }
        
        response = await self.client.post(
            f"{self.base_url}/batch-discover",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_categories(self) -> list:
        """Get available API categories."""
        
        response = await self.client.get(f"{self.base_url}/categories")
        response.raise_for_status()
        return response.json()
    
    async def get_auth_strategies(self) -> list:
        """Get supported authentication strategies."""
        
        response = await self.client.get(f"{self.base_url}/auth-strategies")
        response.raise_for_status()
        return response.json()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        
        response = await self.client.get(f"{self.base_url}/cache/stats")
        response.raise_for_status()
        return response.json()
    
    async def clear_cache(self) -> Dict[str, Any]:
        """Clear the cache."""
        
        response = await self.client.delete(f"{self.base_url}/cache")
        response.raise_for_status()
        return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def get_examples(self) -> Dict[str, Any]:
        """Get usage examples."""
        
        response = await self.client.get(f"{self.base_url}/examples")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main example function."""
    
    print("🌐 API Discovery Service - Web API Client Example")
    print("=" * 60)
    
    client = APIDiscoveryClient()
    
    try:
        # Health check
        print("\n🏥 Health Check")
        print("-" * 20)
        health = await client.health_check()
        print(f"Status: {health['status']}")
        print(f"Version: {health['version']}")
        print(f"Cache Healthy: {health['cache_healthy']}")
        
        # Get available categories and auth strategies
        print("\n📋 Available Options")
        print("-" * 20)
        categories = await client.get_categories()
        auth_strategies = await client.get_auth_strategies()
        
        print(f"Categories: {', '.join(categories)}")
        print(f"Auth Strategies: {', '.join(auth_strategies)}")
        
        # Example 1: Basic API Discovery
        print("\n🔍 Example 1: Basic Discovery")
        print("-" * 30)
        
        result = await client.discover_apis(
            query="NBA live scores API",
            max_results=2,
            category="sports"
        )
        
        print(f"Found {result['total_found']} APIs in {result['search_time']:.2f}s")
        print(f"Cached: {result['cached']}")
        
        for i, api in enumerate(result['results'], 1):
            print(f"\n{i}. {api['api_name']}")
            print(f"   Provider: {api['provider']}")
            print(f"   Category: {api['category']}")
            print(f"   Auth: {api['authentication']['strategy']}")
            print(f"   Confidence: {api['confidence_score']:.2f}")
            
            # Show sample code languages
            if api['sample_code']:
                languages = [code['language'] for code in api['sample_code']]
                print(f"   Sample Code: {', '.join(languages)}")
        
        # Example 2: Search Only
        print("\n\n🔎 Example 2: Search Only")
        print("-" * 30)
        
        search_results = await client.search_apis(
            query="cryptocurrency API",
            max_results=3,
            category="finance"
        )
        
        print(f"Found {len(search_results)} APIs:")
        for i, api in enumerate(search_results, 1):
            print(f"{i}. {api.get('api_name', 'Unknown')}")
            print(f"   Provider: {api.get('provider', 'Unknown')}")
            print(f"   Relevance: {api.get('relevance_score', 0):.2f}")
        
        # Example 3: Batch Discovery
        print("\n\n📦 Example 3: Batch Discovery")
        print("-" * 30)
        
        batch_queries = [
            "weather forecast API",
            "news headlines API"
        ]
        
        batch_results = await client.batch_discover(
            queries=batch_queries,
            max_results_per_query=1
        )
        
        for query, response in batch_results.items():
            print(f"\nQuery: '{query}'")
            if response['results']:
                api = response['results'][0]
                print(f"  Found: {api['api_name']} by {api['provider']}")
                print(f"  Auth: {api['authentication']['strategy']}")
            else:
                print("  No results found")
        
        # Cache statistics
        print("\n\n💾 Cache Statistics")
        print("-" * 20)
        
        cache_stats = await client.get_cache_stats()
        print(json.dumps(cache_stats, indent=2))
        
        # Usage examples
        print("\n\n📖 Usage Examples")
        print("-" * 20)
        
        examples = await client.get_examples()
        for name, example in examples.items():
            print(f"\n{name}:")
            print(f"  Description: {example['description']}")
            print(f"  Endpoint: {example['endpoint']}")
    
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
    
    finally:
        await client.close()
    
    print("\n" + "=" * 60)
    print("✅ Web API examples completed!")
    print("\nTo start the web service:")
    print("python -m gallely.api.main")
    print("\nThen visit: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main()) 