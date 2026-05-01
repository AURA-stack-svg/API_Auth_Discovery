#!/usr/bin/env python3
"""
Business API Integration Examples

This script demonstrates how to discover and integrate with powerful business APIs
using the API Discovery & Auth Service.
"""

import asyncio
import os
from gallely import APIDiscoveryService


async def discover_llm_apis():
    """Discover and integrate with LLM providers."""
    print("🤖 Discovering LLM APIs...")
    
    service = APIDiscoveryService()
    
    # Discover OpenAI API
    result = await service.discover(
        query="OpenAI GPT-4 API for text completion",
        category="ai_ml",
        max_results=3,
        include_documentation=True
    )
    
    print(f"Found {len(result.results)} LLM APIs:")
    for api in result.results:
        print(f"  • {api.api_name} - {api.provider}")
        print(f"    Endpoint: {api.api_endpoint}")
        print(f"    Auth: {api.authentication.strategy}")
        if api.sample_code:
            print(f"    Sample: {api.sample_code[0].code[:100]}...")
        print()


async def discover_payment_apis():
    """Discover payment processing APIs."""
    print("💳 Discovering Payment APIs...")
    
    service = APIDiscoveryService()
    
    result = await service.discover(
        query="Stripe payment processing API",
        preferred_providers=["stripe", "paypal", "square"],
        category="finance",
        max_results=3,
        include_documentation=True,
        test_endpoint=True
    )
    
    print(f"Found {len(result.results)} payment APIs:")
    for api in result.results:
        print(f"  • {api.api_name} - {api.provider}")
        print(f"    Endpoint: {api.api_endpoint}")
        if api.rate_limits:
            print(f"    Rate Limits: {api.rate_limits.requests_per_day}/day")
        if api.test_results:
            print(f"    Test: {'✅ Passed' if api.test_results.success else '❌ Failed'}")
        print()


async def discover_cloud_apis():
    """Discover cloud infrastructure APIs."""
    print("☁️ Discovering Cloud APIs...")
    
    service = APIDiscoveryService()
    
    result = await service.discover(
        query="AWS S3 storage API",
        category="developer_tools",
        max_results=3,
        include_documentation=True
    )
    
    print(f"Found {len(result.results)} cloud APIs:")
    for api in result.results:
        print(f"  • {api.api_name} - {api.provider}")
        print(f"    Category: {api.category}")
        print(f"    Description: {api.description[:100]}...")
        print()


async def discover_productivity_apis():
    """Discover productivity and collaboration APIs."""
    print("📢 Discovering Productivity APIs...")
    
    service = APIDiscoveryService()
    
    queries = [
        "Slack team communication API",
        "GitHub repository management API",
        "Notion workspace API",
        "Salesforce CRM API"
    ]
    
    results = await service.batch_discover(
        queries=queries,
        max_results_per_query=2
    )
    
    for query, result in results.items():
        print(f"\n📋 {query}:")
        for api in result.results:
            print(f"  • {api.api_name}")
            print(f"    Auth: {api.authentication.strategy}")
            if api.authentication.headers:
                print(f"    Headers: {list(api.authentication.headers.keys())}")


async def enterprise_integration_example():
    """Example of enterprise API integration workflow."""
    print("\n🏢 Enterprise Integration Workflow")
    print("=" * 50)
    
    service = APIDiscoveryService()
    
    # Step 1: Discover CRM API
    print("Step 1: Discovering CRM API...")
    crm_result = await service.discover(
        query="Salesforce CRM API for customer data",
        category="data_analytics",
        max_results=1,
        include_documentation=True,
        test_endpoint=True
    )
    
    if crm_result.results:
        crm_api = crm_result.results[0]
        print(f"✅ Found: {crm_api.api_name}")
        print(f"   Endpoint: {crm_api.api_endpoint}")
        print(f"   Auth: {crm_api.authentication.strategy}")
    
    # Step 2: Discover Payment API
    print("\nStep 2: Discovering Payment API...")
    payment_result = await service.discover(
        query="Stripe subscription billing API",
        category="finance",
        max_results=1,
        include_documentation=True
    )
    
    if payment_result.results:
        payment_api = payment_result.results[0]
        print(f"✅ Found: {payment_api.api_name}")
        print(f"   Endpoint: {payment_api.api_endpoint}")
        print(f"   Rate Limits: {payment_api.rate_limits.requests_per_day if payment_api.rate_limits else 'Unknown'}/day")
    
    # Step 3: Discover Analytics API
    print("\nStep 3: Discovering Analytics API...")
    analytics_result = await service.discover(
        query="Google Analytics reporting API",
        category="data_analytics",
        max_results=1,
        include_documentation=True
    )
    
    if analytics_result.results:
        analytics_api = analytics_result.results[0]
        print(f"✅ Found: {analytics_api.api_name}")
        print(f"   Endpoint: {analytics_api.api_endpoint}")
    
    print("\n🎉 Enterprise integration stack ready!")
    print("   • CRM: Customer data management")
    print("   • Payments: Subscription billing")
    print("   • Analytics: Performance tracking")


async def main():
    """Run all business API discovery examples."""
    print("🚀 Business API Discovery Examples")
    print("=" * 50)
    
    try:
        # Check if API keys are configured
        if not os.getenv("TAVILY_API_KEY") or not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: API keys not configured")
            print("Please set TAVILY_API_KEY and OPENAI_API_KEY environment variables")
            return
        
        # Run discovery examples
        await discover_llm_apis()
        await discover_payment_apis()
        await discover_cloud_apis()
        await discover_productivity_apis()
        await enterprise_integration_example()
        
        print("\n✅ All examples completed successfully!")
        print("\n💡 Next steps:")
        print("   • Use the discovered APIs in your applications")
        print("   • Check the web interface at http://localhost:8000")
        print("   • Explore the API documentation at http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the API Discovery Service is running and API keys are configured")


if __name__ == "__main__":
    asyncio.run(main()) 