"""
API Discovery & Auth Service

The missing link between AI app builders and the real world.
Automatically discovers APIs and handles authentication for LLMs.
"""

__version__ = "1.0.0"
__author__ = "API Discovery Team"
__email__ = "team@api-discovery.dev"

from .core.service import APIDiscoveryService
from .models.api_result import APIResult
from .core.config import Settings

__all__ = [
    "APIDiscoveryService",
    "APIResult", 
    "Settings",
] 