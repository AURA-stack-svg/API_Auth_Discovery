"""
FastAPI web application for the API Discovery Service.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import time
import os
from typing import List, Dict, Any, Optional

from loguru import logger

from ..core.service import APIDiscoveryService
from ..models.api_result import (
    DiscoveryRequest, DiscoveryResponse, APIResult,
    AuthStrategy, APICategory
)
from ..core.config import settings


# Global service instance
service: Optional[APIDiscoveryService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global service
    
    # Startup
    logger.info("Starting API Discovery Service")
    service = APIDiscoveryService()
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Discovery Service")
    if service and service.cache_manager:
        await service.cache_manager.close()


# Create FastAPI app
app = FastAPI(
    title="API Discovery & Auth Service",
    description="The missing link between AI app builders and the real world",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def get_service() -> APIDiscoveryService:
    """Dependency to get the service instance."""
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return service


@app.get("/")
async def root():
    """Serve the demo interface."""
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    
    # Fallback to API info
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "API Discovery & Authentication Service",
        "docs_url": "/docs",
        "health_url": "/health",
        "status": "running"
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "API Discovery & Authentication Service",
        "docs_url": "/docs",
        "health_url": "/health",
        "status": "running"
    }


@app.get("/health")
async def health_check(service: APIDiscoveryService = Depends(get_service)):
    """Health check endpoint."""
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "cache_healthy": True
    }
    
    # Check cache health
    if service.cache_manager:
        cache_healthy = await service.cache_manager.health_check()
        health_status["cache_healthy"] = cache_healthy
        
        if not cache_healthy:
            health_status["status"] = "degraded"
    
    return health_status


@app.post("/discover", response_model=DiscoveryResponse)
async def discover_apis(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    service: APIDiscoveryService = Depends(get_service)
):
    """
    Discover and authenticate APIs based on a natural language query.
    
    This is the main endpoint that:
    1. Searches for relevant APIs using Tavily
    2. Automates authentication using browser automation
    3. Returns ready-to-use API configurations
    """
    
    try:
        logger.info(f"API discovery request: {request.query}")
        
        response = await service.discover(
            query=request.query,
            preferred_providers=request.preferred_providers,
            auth_strategy=request.auth_strategy,
            category=request.category,
            max_results=request.max_results,
            include_documentation=request.include_documentation,
            test_endpoint=request.test_endpoint,
            cache_duration=request.cache_duration
        )
        
        logger.info(f"Discovery completed: {response.total_found} APIs found")
        return response
        
    except Exception as e:
        logger.error(f"Error in API discovery: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/search", response_model=List[Dict[str, Any]])
async def search_apis(
    query: str,
    category: Optional[APICategory] = None,
    preferred_providers: Optional[List[str]] = None,
    max_results: int = 10,
    service: APIDiscoveryService = Depends(get_service)
):
    """
    Search for APIs without authentication.
    
    This endpoint only discovers APIs but doesn't handle authentication.
    Useful for exploring available APIs before committing to authentication.
    """
    
    try:
        results = await service.search_apis(
            query=query,
            category=category,
            preferred_providers=preferred_providers,
            max_results=max_results
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in API search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/batch-discover", response_model=Dict[str, DiscoveryResponse])
async def batch_discover_apis(
    queries: List[str],
    max_results_per_query: int = 3,
    service: APIDiscoveryService = Depends(get_service)
):
    """
    Discover APIs for multiple queries in parallel.
    
    Useful for discovering multiple types of APIs at once.
    Results are returned as a dictionary with queries as keys.
    """
    
    if len(queries) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 queries allowed per batch request"
        )
    
    try:
        results = await service.batch_discover(
            queries=queries,
            max_results_per_query=max_results_per_query
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch discovery: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/categories", response_model=List[str])
async def get_api_categories():
    """Get list of available API categories."""
    return [category.value for category in APICategory]


@app.get("/auth-strategies", response_model=List[str])
async def get_auth_strategies():
    """Get list of supported authentication strategies."""
    return [strategy.value for strategy in AuthStrategy]


@app.get("/cache/stats")
async def get_cache_stats(service: APIDiscoveryService = Depends(get_service)):
    """Get cache statistics."""
    
    if not service.cache_manager:
        return {"cache_enabled": False}
    
    try:
        stats = await service.cache_manager.get_cache_stats()
        stats["cache_enabled"] = True
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache stats: {str(e)}"
        )


@app.delete("/cache")
async def clear_cache(service: APIDiscoveryService = Depends(get_service)):
    """Clear all cached entries."""
    
    if not service.cache_manager:
        raise HTTPException(
            status_code=404,
            detail="Cache not enabled"
        )
    
    try:
        success = await service.cache_manager.clear()
        
        if success:
            return {"message": "Cache cleared successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear cache"
            )
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )


@app.get("/api/{api_name}/status")
async def get_api_status(
    api_name: str,
    service: APIDiscoveryService = Depends(get_service)
):
    """Get the status of a previously discovered API."""
    
    try:
        status = await service.get_api_status(api_name)
        return status
        
    except Exception as e:
        logger.error(f"Error getting API status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting API status: {str(e)}"
        )


@app.post("/api/{api_name}/refresh-credentials")
async def refresh_api_credentials(
    api_name: str,
    service: APIDiscoveryService = Depends(get_service)
):
    """Refresh credentials for a specific API."""
    
    try:
        auth_info = await service.refresh_api_credentials(api_name)
        return {
            "api_name": api_name,
            "authentication": auth_info.model_dump(),
            "refreshed_at": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing credentials: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing credentials: {str(e)}"
        )


@app.get("/examples")
async def get_usage_examples():
    """Get usage examples for the API."""
    
    return {
        "llm_integration": {
            "description": "Integrate with LLM providers",
            "endpoint": "POST /discover",
            "example": {
                "query": "OpenAI GPT-4 API for text completion",
                "category": "ai_ml",
                "max_results": 3,
                "include_documentation": True,
                "test_endpoint": False
            }
        },
        "payment_processing": {
            "description": "Payment and billing APIs",
            "endpoint": "POST /discover",
            "example": {
                "query": "Stripe payment processing API",
                "preferred_providers": ["stripe", "paypal", "square"],
                "auth_strategy": "api_key",
                "category": "finance",
                "max_results": 3,
                "include_documentation": True,
                "test_endpoint": True
            }
        },
        "cloud_infrastructure": {
            "description": "Cloud service APIs",
            "endpoint": "POST /discover",
            "example": {
                "query": "AWS S3 storage API",
                "category": "developer_tools",
                "max_results": 5,
                "include_documentation": True,
                "test_endpoint": False
            }
        },
        "business_intelligence": {
            "description": "Analytics and CRM APIs",
            "endpoint": "POST /discover",
            "example": {
                "query": "Salesforce CRM API",
                "category": "data_analytics",
                "max_results": 3,
                "include_documentation": True,
                "test_endpoint": True
            }
        },
        "batch_discovery": {
            "description": "Discover multiple business APIs at once",
            "endpoint": "POST /batch-discover",
            "example": {
                "queries": [
                    "OpenAI GPT API for text generation",
                    "Stripe payment processing API",
                    "GitHub repository management API",
                    "Slack team communication API"
                ],
                "max_results_per_query": 2
            }
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "docs_url": "/docs"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "docs_url": "/docs"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "gallely.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
        log_level=settings.log_level.lower()
    ) 