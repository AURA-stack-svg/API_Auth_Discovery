"""
Cache manager for storing and retrieving API discovery results.
"""

import json
import asyncio
from typing import Optional, Any
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from loguru import logger
from ..core.config import settings
from ..models.api_result import DiscoveryResponse


class CacheManager:
    """Manages caching of API discovery results."""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.max_memory_cache_size = settings.max_cache_size
        
        if REDIS_AVAILABLE and settings.redis_url:
            self._init_redis()
        else:
            logger.warning("Redis not available, using in-memory cache")
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {str(e)}, falling back to memory cache")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[DiscoveryResponse]:
        """Get a cached discovery response."""
        
        try:
            # Try Redis first
            if self.redis_client:
                cached_data = await self.redis_client.get(f"api_discovery:{key}")
                if cached_data:
                    data = json.loads(cached_data)
                    return DiscoveryResponse(**data)
            
            # Fallback to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                
                # Check if expired
                if datetime.utcnow() < cache_entry["expires_at"]:
                    return cache_entry["data"]
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: DiscoveryResponse,
        ttl: int = None
    ) -> bool:
        """Set a discovery response in cache."""
        
        if ttl is None:
            ttl = settings.cache_ttl
        
        try:
            # Serialize the response
            serialized_data = value.model_dump_json()
            
            # Try Redis first
            if self.redis_client:
                await self.redis_client.setex(
                    f"api_discovery:{key}",
                    ttl,
                    serialized_data
                )
                return True
            
            # Fallback to memory cache
            # Clean up memory cache if it's getting too large
            if len(self.memory_cache) >= self.max_memory_cache_size:
                self._cleanup_memory_cache()
            
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            self.memory_cache[key] = {
                "data": value,
                "expires_at": expires_at
            }
            
            return True
            
        except Exception as e:
            logger.warning(f"Error setting cache: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a cached entry."""
        
        try:
            # Try Redis first
            if self.redis_client:
                await self.redis_client.delete(f"api_discovery:{key}")
            
            # Remove from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            return True
            
        except Exception as e:
            logger.warning(f"Error deleting from cache: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cached entries."""
        
        try:
            # Clear Redis cache
            if self.redis_client:
                keys = await self.redis_client.keys("api_discovery:*")
                if keys:
                    await self.redis_client.delete(*keys)
            
            # Clear memory cache
            self.memory_cache.clear()
            
            logger.info("Cache cleared successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Error clearing cache: {str(e)}")
            return False
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache."""
        
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, cache_entry in self.memory_cache.items():
            if current_time >= cache_entry["expires_at"]:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        # If still too large, remove oldest entries
        if len(self.memory_cache) >= self.max_memory_cache_size:
            # Sort by expiration time and remove oldest
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1]["expires_at"]
            )
            
            # Remove oldest 25% of entries
            remove_count = len(sorted_items) // 4
            for i in range(remove_count):
                key = sorted_items[i][0]
                del self.memory_cache[key]
    
    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        
        stats = {
            "cache_type": "redis" if self.redis_client else "memory",
            "memory_cache_size": len(self.memory_cache),
            "max_memory_cache_size": self.max_memory_cache_size
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    "redis_connected": True,
                    "redis_used_memory": info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": info.get("connected_clients", 0)
                })
            except Exception as e:
                stats["redis_connected"] = False
                stats["redis_error"] = str(e)
        else:
            stats["redis_connected"] = False
        
        return stats
    
    async def health_check(self) -> bool:
        """Check if cache is healthy."""
        
        try:
            # Test Redis connection
            if self.redis_client:
                await self.redis_client.ping()
                return True
            
            # Memory cache is always "healthy"
            return True
            
        except Exception as e:
            logger.warning(f"Cache health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Close cache connections."""
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


class InMemoryCache:
    """Simple in-memory cache for when Redis is not available."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Check if expired
            if datetime.utcnow() < entry["expires_at"]:
                return entry["value"]
            else:
                del self.cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        
        if ttl is None:
            ttl = self.default_ttl
        
        # Clean up if cache is full
        if len(self.cache) >= self.max_size:
            self._cleanup()
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        
        if key in self.cache:
            del self.cache[key]
            return True
        
        return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        
        self.cache.clear()
        return True
    
    def _cleanup(self):
        """Remove expired and oldest entries."""
        
        current_time = datetime.utcnow()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time >= entry["expires_at"]
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        # If still too large, remove oldest entries
        if len(self.cache) >= self.max_size:
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1]["created_at"]
            )
            
            # Remove oldest 25%
            remove_count = len(sorted_items) // 4
            for i in range(remove_count):
                key = sorted_items[i][0]
                del self.cache[key] 