#!/usr/bin/env python3
"""
Basic usage example for the API Discovery Service.

This script demonstrates how to:
1. Discover APIs using natural language queries
2. Get authentication details automatically
3. Use the returned API configurations
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from gallely import APIDiscoveryService


async def main():
    """Main example function."""
    
    print("🔗 API Discovery & Auth Service - Basic Usage Example")
    print("=" * 60)
    
    # Initialize the service
    service = APIDiscoveryService()
    
    # Example 1: NBA Live Scoring API
    print("\n📊 Example 1: NBA Live Scoring API")
    print("-" * 40)
    
    try:
        result = await service.discover(
            query="NBA live scoring API",
            max_results=2,
            include_documentation=True,
            test_endpoint=False
        )
        
        print(f"Found {result.total_found} APIs in {result.search_time:.2f} seconds")
        
        for i, api in enumerate(result.results, 1):
            print(f"\n{i}. {api.api_name} by {api.provider}")
            print(f"   Category: {api.category}")
            print(f"   Endpoint: {api.api_endpoint}")
            print(f"   Auth Strategy: {api.authentication.strategy}")
            
            if api.authentication.headers:
                print(f"   Headers: {list(api.authentication.headers.keys())}")
            
            if api.sample_code:
                print(f"   Sample Code: {len(api.sample_code)} examples")
                # Show Python example if available
                python_example = next(
                    (code for code in api.sample_code if code.language == "python"),
                    None
                )
                if python_example:
                    print(f"\n   Python Example:")
                    print("   " + "\n   ".join(python_example.code.split("\n")[:10]))
                    if len(python_example.code.split("\n")) > 10:
                        print("   ...")
            
            print(f"   Confidence: {api.confidence_score:.2f}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Example 2: Weather API
    print("\n\n🌤️  Example 2: Weather Forecast API")
    print("-" * 40)
    
    try:
        result = await service.discover(
            query="weather forecast API",
            preferred_providers=["openweathermap", "weatherapi"],
            max_results=1,
            include_documentation=True
        )
        
        if result.results:
            api = result.results[0]
            print(f"Found: {api.api_name}")
            print(f"Provider: {api.provider}")
            print(f"Description: {api.description[:200]}...")
            
            if api.rate_limits:
                print(f"Rate Limits:")
                if api.rate_limits.requests_per_day:
                    print(f"  - {api.rate_limits.requests_per_day} requests/day")
                if api.rate_limits.pricing_tier:
                    print(f"  - Tier: {api.rate_limits.pricing_tier}")
        else:
            print("No weather APIs found")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Example 3: Batch Discovery
    print("\n\n🔄 Example 3: Batch Discovery")
    print("-" * 40)
    
    try:
        queries = [
            "cryptocurrency prices API",
            "news headlines API",
            "stock market data API"
        ]
        
        results = await service.batch_discover(
            queries=queries,
            max_results_per_query=1
        )
        
        for query, response in results.items():
            print(f"\nQuery: '{query}'")
            if response.results:
                api = response.results[0]
                print(f"  Found: {api.api_name} by {api.provider}")
                print(f"  Auth: {api.authentication.strategy}")
            else:
                print("  No APIs found")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Example 4: Search Only (No Authentication)
    print("\n\n🔍 Example 4: Search Only (No Auth)")
    print("-" * 40)
    
    try:
        search_results = await service.search_apis(
            query="social media API",
            max_results=3
        )
        
        print(f"Found {len(search_results)} APIs:")
        for i, api_info in enumerate(search_results, 1):
            print(f"{i}. {api_info.get('api_name', 'Unknown')}")
            print(f"   Provider: {api_info.get('provider', 'Unknown')}")
            print(f"   Category: {api_info.get('category', 'Unknown')}")
            print(f"   Relevance: {api_info.get('relevance_score', 0):.2f}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✅ Examples completed!")
    print("\nNext steps:")
    print("1. Check the generated API keys and test them")
    print("2. Integrate the sample code into your application")
    print("3. Monitor rate limits and usage")
    print("4. Explore the FastAPI docs at http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main()) 