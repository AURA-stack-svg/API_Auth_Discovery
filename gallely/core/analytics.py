"""
Analytics and metrics collection for the API Discovery Service.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json

from loguru import logger


@dataclass
class DiscoveryEvent:
    """Represents a single API discovery event."""
    timestamp: datetime
    query: str
    category: Optional[str]
    results_found: int
    search_time: float
    cached: bool
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class UsageStats:
    """Usage statistics for a time period."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_search_time: float
    avg_results_per_query: float
    cache_hit_rate: float
    popular_queries: List[Dict[str, Any]]
    popular_categories: List[Dict[str, Any]]
    unique_users: int


class AnalyticsCollector:
    """Collects and analyzes usage analytics."""
    
    def __init__(self, max_events: int = 10000):
        self.events: deque = deque(maxlen=max_events)
        self.query_counts = defaultdict(int)
        self.category_counts = defaultdict(int)
        self.user_agents = set()
        self.ip_addresses = set()
        
    def record_discovery(
        self,
        query: str,
        category: Optional[str],
        results_found: int,
        search_time: float,
        cached: bool,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Record a discovery event."""
        
        event = DiscoveryEvent(
            timestamp=datetime.utcnow(),
            query=query,
            category=category,
            results_found=results_found,
            search_time=search_time,
            cached=cached,
            user_agent=user_agent,
            ip_address=ip_address,
            success=success,
            error_message=error_message
        )
        
        self.events.append(event)
        
        # Update counters
        if success:
            self.query_counts[query.lower().strip()] += 1
            if category:
                self.category_counts[category] += 1
        
        if user_agent:
            self.user_agents.add(user_agent)
        if ip_address:
            self.ip_addresses.add(ip_address)
        
        logger.info(f"Analytics: Recorded discovery event for query '{query}'")
    
    def get_stats(self, hours: int = 24) -> UsageStats:
        """Get usage statistics for the specified time period."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [
            event for event in self.events 
            if event.timestamp >= cutoff_time
        ]
        
        if not recent_events:
            return UsageStats(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_search_time=0.0,
                avg_results_per_query=0.0,
                cache_hit_rate=0.0,
                popular_queries=[],
                popular_categories=[],
                unique_users=0
            )
        
        # Calculate basic stats
        total_requests = len(recent_events)
        successful_requests = sum(1 for e in recent_events if e.success)
        failed_requests = total_requests - successful_requests
        
        # Calculate averages
        successful_events = [e for e in recent_events if e.success]
        avg_search_time = (
            sum(e.search_time for e in successful_events) / len(successful_events)
            if successful_events else 0.0
        )
        avg_results_per_query = (
            sum(e.results_found for e in successful_events) / len(successful_events)
            if successful_events else 0.0
        )
        
        # Calculate cache hit rate
        cached_requests = sum(1 for e in recent_events if e.cached)
        cache_hit_rate = cached_requests / total_requests if total_requests > 0 else 0.0
        
        # Get popular queries
        query_counts = defaultdict(int)
        for event in recent_events:
            if event.success:
                query_counts[event.query.lower().strip()] += 1
        
        popular_queries = [
            {"query": query, "count": count}
            for query, count in sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Get popular categories
        category_counts = defaultdict(int)
        for event in recent_events:
            if event.success and event.category:
                category_counts[event.category] += 1
        
        popular_categories = [
            {"category": category, "count": count}
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Count unique users (by IP address)
        unique_ips = set(e.ip_address for e in recent_events if e.ip_address)
        unique_users = len(unique_ips)
        
        return UsageStats(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_search_time=avg_search_time,
            avg_results_per_query=avg_results_per_query,
            cache_hit_rate=cache_hit_rate,
            popular_queries=popular_queries,
            popular_categories=popular_categories,
            unique_users=unique_users
        )
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly breakdown of usage statistics."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [
            event for event in self.events 
            if event.timestamp >= cutoff_time
        ]
        
        # Group events by hour
        hourly_data = defaultdict(lambda: {
            'requests': 0,
            'successful': 0,
            'failed': 0,
            'avg_search_time': 0.0,
            'cached': 0
        })
        
        for event in recent_events:
            hour_key = event.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_data[hour_key]['requests'] += 1
            
            if event.success:
                hourly_data[hour_key]['successful'] += 1
                hourly_data[hour_key]['avg_search_time'] += event.search_time
            else:
                hourly_data[hour_key]['failed'] += 1
            
            if event.cached:
                hourly_data[hour_key]['cached'] += 1
        
        # Calculate averages and format output
        result = []
        for hour, data in sorted(hourly_data.items()):
            if data['successful'] > 0:
                data['avg_search_time'] /= data['successful']
            
            result.append({
                'hour': hour.isoformat(),
                'requests': data['requests'],
                'successful': data['successful'],
                'failed': data['failed'],
                'avg_search_time': round(data['avg_search_time'], 2),
                'cache_hit_rate': round(data['cached'] / data['requests'], 2) if data['requests'] > 0 else 0.0
            })
        
        return result
    
    def export_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Export recent events as JSON-serializable data."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [
            event for event in self.events 
            if event.timestamp >= cutoff_time
        ]
        
        return [
            {
                **asdict(event),
                'timestamp': event.timestamp.isoformat()
            }
            for event in recent_events
        ]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics."""
        
        if not self.events:
            return {
                'total_events': 0,
                'memory_usage_mb': 0,
                'avg_events_per_minute': 0.0
            }
        
        # Calculate memory usage (rough estimate)
        import sys
        memory_usage_mb = sys.getsizeof(self.events) / (1024 * 1024)
        
        # Calculate events per minute
        if len(self.events) > 1:
            time_span = (self.events[-1].timestamp - self.events[0].timestamp).total_seconds()
            avg_events_per_minute = len(self.events) / (time_span / 60) if time_span > 0 else 0.0
        else:
            avg_events_per_minute = 0.0
        
        return {
            'total_events': len(self.events),
            'memory_usage_mb': round(memory_usage_mb, 2),
            'avg_events_per_minute': round(avg_events_per_minute, 2),
            'unique_queries': len(self.query_counts),
            'unique_categories': len(self.category_counts),
            'unique_user_agents': len(self.user_agents),
            'unique_ip_addresses': len(self.ip_addresses)
        }


# Global analytics collector instance
analytics = AnalyticsCollector()


def record_discovery_event(
    query: str,
    category: Optional[str],
    results_found: int,
    search_time: float,
    cached: bool,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Convenience function to record a discovery event."""
    
    analytics.record_discovery(
        query=query,
        category=category,
        results_found=results_found,
        search_time=search_time,
        cached=cached,
        user_agent=user_agent,
        ip_address=ip_address,
        success=success,
        error_message=error_message
    )


def get_analytics_stats(hours: int = 24) -> UsageStats:
    """Get analytics statistics for the specified time period."""
    return analytics.get_stats(hours=hours) 