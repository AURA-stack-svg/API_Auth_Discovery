"""
Browser automation module for API signup and authentication key extraction.
"""

import asyncio
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from browser_use import Agent
from langchain_openai import ChatOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.api_result import AuthStrategy, AuthenticationInfo
from ..core.config import settings


class BrowserAuthAgent:
    """Browser automation agent for API authentication."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
            temperature=0.1  # Low temperature for consistent behavior
        )
        self.signup_patterns = self._load_signup_patterns()
        
    def _load_signup_patterns(self) -> Dict[str, Any]:
        """Load patterns for identifying signup and API key elements."""
        return {
            "signup_indicators": [
                "sign up", "register", "create account", "get started",
                "join", "signup", "registration", "free trial"
            ],
            "api_key_indicators": [
                "api key", "api token", "access token", "secret key",
                "client id", "client secret", "bearer token", "auth token"
            ],
            "dashboard_indicators": [
                "dashboard", "console", "developer", "api", "keys",
                "settings", "account", "profile", "credentials"
            ],
            "form_fields": {
                "email": ["email", "e-mail", "mail"],
                "password": ["password", "pass", "pwd"],
                "username": ["username", "user", "name"],
                "company": ["company", "organization", "org"],
                "first_name": ["first name", "firstname", "fname"],
                "last_name": ["last name", "lastname", "lname"]
            }
        }
    
    @retry(
        stop=stop_after_attempt(settings.max_signup_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def authenticate_api(
        self,
        api_info: Dict[str, Any],
        auth_strategy: Optional[AuthStrategy] = None
    ) -> AuthenticationInfo:
        """Authenticate with an API by automating the signup process."""
        
        api_name = api_info.get("api_name", "Unknown API")
        base_url = api_info.get("base_url", "")
        doc_url = api_info.get("documentation_url", "")
        
        logger.info(f"Starting authentication for {api_name}")
        
        try:
            # Determine the best URL to start with
            start_url = self._determine_start_url(api_info)
            
            # Create browser agent with specific task
            task = self._create_task(api_info, auth_strategy)
            
            agent = Agent(
                task=task,
                llm=self.llm,
                browser_config={
                    "headless": settings.browser_headless,
                    "timeout": settings.browser_timeout * 1000,  # Convert to milliseconds
                    "user_agent": settings.browser_user_agent
                }
            )
            
            # Run the authentication process
            result = await agent.run()
            
            # Extract authentication information from the result
            auth_info = await self._extract_auth_info(result, api_info)
            
            logger.info(f"Successfully authenticated with {api_name}")
            return auth_info
            
        except Exception as e:
            logger.error(f"Failed to authenticate with {api_name}: {str(e)}")
            # Return a fallback authentication info
            return self._create_fallback_auth_info(api_info, auth_strategy)
    
    def _determine_start_url(self, api_info: Dict[str, Any]) -> str:
        """Determine the best URL to start the authentication process."""
        
        # Priority order for URLs
        urls_to_try = [
            api_info.get("documentation_url"),
            api_info.get("base_url"),
            api_info.get("source_url")
        ]
        
        for url in urls_to_try:
            if url and isinstance(url, str):
                # Prefer developer/docs URLs
                if any(term in url.lower() for term in ["developer", "docs", "api"]):
                    return url
        
        # Fallback to first available URL
        for url in urls_to_try:
            if url:
                return str(url)
        
        raise ValueError("No valid URL found for authentication")
    
    def _create_task(
        self,
        api_info: Dict[str, Any],
        auth_strategy: Optional[AuthStrategy] = None
    ) -> str:
        """Create a detailed task description for the browser agent."""
        
        api_name = api_info.get("api_name", "Unknown API")
        provider = api_info.get("provider", "Unknown Provider")
        detected_auth = api_info.get("auth_strategy", AuthStrategy.API_KEY)
        
        # Use provided strategy or fall back to detected one
        target_auth = auth_strategy or detected_auth
        
        task_parts = [
            f"I need to sign up for the {api_name} by {provider} and get API credentials.",
            f"The authentication method appears to be {target_auth.value}.",
            "",
            "Please follow these steps:",
            "1. Navigate to the website and look for signup/registration options",
            "2. If there's a 'Sign Up', 'Register', 'Get Started', or 'Free Trial' button, click it",
            "3. Fill out the registration form with these details:",
            "   - Email: test.developer.api@gmail.com",
            "   - Password: TestAPI123!",
            "   - Name: API Test Developer",
            "   - Company: API Discovery Service",
            "4. Complete the signup process (verify email if needed)",
            "5. Navigate to the dashboard, developer console, or API section",
            "6. Look for API keys, tokens, or credentials",
            "7. Copy any API keys, client IDs, secrets, or tokens you find",
            "",
            "Important notes:",
            "- If email verification is required, mention it in your response",
            "- Look for free tier or trial options",
            "- Take note of any rate limits or pricing information",
            "- If you encounter captchas or other blocks, describe them",
            "- Be thorough in exploring the dashboard for API credentials",
            "",
            f"Target authentication type: {target_auth.value}",
            "Please provide the API credentials you find in a clear format."
        ]
        
        return "\n".join(task_parts)
    
    async def _extract_auth_info(
        self,
        browser_result: Any,
        api_info: Dict[str, Any]
    ) -> AuthenticationInfo:
        """Extract authentication information from browser automation result."""
        
        try:
            # Get the result text/content
            result_text = str(browser_result) if browser_result else ""
            
            # Extract different types of credentials
            api_key = self._extract_api_key(result_text)
            client_id = self._extract_client_id(result_text)
            client_secret = self._extract_client_secret(result_text)
            bearer_token = self._extract_bearer_token(result_text)
            
            # Determine the authentication strategy based on what we found
            auth_strategy = self._get_auth_strategy(
                api_key, client_id, client_secret, bearer_token
            )
            
            # Build authentication info
            auth_info = AuthenticationInfo(
                strategy=auth_strategy,
                headers={},
                query_params={},
                api_key=api_key,
                token=bearer_token
            )
            
            # Configure headers based on strategy
            if auth_strategy == AuthStrategy.API_KEY and api_key:
                auth_info.headers = {
                    "X-API-Key": api_key,
                    "Authorization": f"Bearer {api_key}"
                }
            elif auth_strategy == AuthStrategy.BEARER_TOKEN and bearer_token:
                auth_info.headers = {
                    "Authorization": f"Bearer {bearer_token}"
                }
            elif auth_strategy == AuthStrategy.OAUTH2 and client_id:
                auth_info.oauth_config = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_url": self._extract_auth_url(result_text),
                    "token_url": self._extract_token_url(result_text)
                }
            
            return auth_info
            
        except Exception as e:
            logger.warning(f"Error extracting auth info: {str(e)}")
            return self._create_fallback_auth_info(api_info)
    
    def _extract_api_key(self, text: str) -> Optional[str]:
        """Extract API key from text."""
        
        # Common API key patterns
        patterns = [
            r'api[_\s]?key[:\s]*([a-zA-Z0-9_-]{20,})',
            r'key[:\s]*([a-zA-Z0-9_-]{20,})',
            r'token[:\s]*([a-zA-Z0-9_-]{20,})',
            r'secret[:\s]*([a-zA-Z0-9_-]{20,})',
            # Specific formats
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI style
            r'pk_[a-zA-Z0-9]{20,}',  # Stripe style
            r'[a-zA-Z0-9]{32,64}'    # Generic long strings
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                key = match.group(1) if match.groups() else match.group(0)
                if len(key) >= 20:  # Minimum length for API keys
                    return key
        
        return None
    
    def _extract_client_id(self, text: str) -> Optional[str]:
        """Extract OAuth2 client ID from text."""
        
        patterns = [
            r'client[_\s]?id[:\s]*([a-zA-Z0-9_-]{10,})',
            r'app[_\s]?id[:\s]*([a-zA-Z0-9_-]{10,})',
            r'application[_\s]?id[:\s]*([a-zA-Z0-9_-]{10,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_client_secret(self, text: str) -> Optional[str]:
        """Extract OAuth2 client secret from text."""
        
        patterns = [
            r'client[_\s]?secret[:\s]*([a-zA-Z0-9_-]{20,})',
            r'app[_\s]?secret[:\s]*([a-zA-Z0-9_-]{20,})',
            r'application[_\s]?secret[:\s]*([a-zA-Z0-9_-]{20,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_bearer_token(self, text: str) -> Optional[str]:
        """Extract bearer token from text."""
        
        patterns = [
            r'bearer[_\s]?token[:\s]*([a-zA-Z0-9_.-]{20,})',
            r'access[_\s]?token[:\s]*([a-zA-Z0-9_.-]{20,})',
            r'jwt[:\s]*([a-zA-Z0-9_.-]{20,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_auth_url(self, text: str) -> Optional[str]:
        """Extract OAuth2 authorization URL from text."""
        
        patterns = [
            r'auth[a-z]*[_\s]?url[:\s]*(https?://[^\s<>"]+)',
            r'authorization[_\s]?endpoint[:\s]*(https?://[^\s<>"]+)',
            r'oauth[_\s]?url[:\s]*(https?://[^\s<>"]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_token_url(self, text: str) -> Optional[str]:
        """Extract OAuth2 token URL from text."""
        
        patterns = [
            r'token[_\s]?url[:\s]*(https?://[^\s<>"]+)',
            r'token[_\s]?endpoint[:\s]*(https?://[^\s<>"]+)',
            r'access[_\s]?token[_\s]?url[:\s]*(https?://[^\s<>"]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_auth_strategy(
        self,
        api_key: Optional[str],
        client_id: Optional[str],
        client_secret: Optional[str],
        bearer_token: Optional[str]
    ) -> AuthStrategy:
        """Determine authentication strategy based on available credentials."""
        
        if client_id and client_secret:
            return AuthStrategy.OAUTH2
        elif bearer_token:
            return AuthStrategy.BEARER_TOKEN
        elif api_key:
            return AuthStrategy.API_KEY
        else:
            return AuthStrategy.API_KEY  # Default fallback
    
    def _create_fallback_auth_info(
        self,
        api_info: Dict[str, Any],
        auth_strategy: Optional[AuthStrategy] = None
    ) -> AuthenticationInfo:
        """Create fallback authentication info when automation fails."""
        
        strategy = auth_strategy or api_info.get("auth_strategy", AuthStrategy.API_KEY)
        
        auth_info = AuthenticationInfo(
            strategy=strategy,
            headers={},
            query_params={}
        )
        
        # Add common headers based on strategy
        if strategy == AuthStrategy.API_KEY:
            auth_info.headers = {
                "X-API-Key": "YOUR_API_KEY_HERE",
                "Authorization": "Bearer YOUR_API_KEY_HERE"
            }
        elif strategy == AuthStrategy.BEARER_TOKEN:
            auth_info.headers = {
                "Authorization": "Bearer YOUR_TOKEN_HERE"
            }
        elif strategy == AuthStrategy.OAUTH2:
            auth_info.oauth_config = {
                "client_id": "YOUR_CLIENT_ID",
                "client_secret": "YOUR_CLIENT_SECRET",
                "auth_url": "https://api.example.com/oauth/authorize",
                "token_url": "https://api.example.com/oauth/token"
            }
        elif strategy == AuthStrategy.BASIC_AUTH:
            auth_info.username = "YOUR_USERNAME"
            auth_info.password = "YOUR_PASSWORD"
            auth_info.headers = {
                "Authorization": "Basic YOUR_ENCODED_CREDENTIALS"
            }
        
        return auth_info
    
    async def test_api_endpoint(
        self,
        endpoint_url: str,
        auth_info: AuthenticationInfo,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """Test an API endpoint with the provided authentication."""
        
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare request parameters
                headers = auth_info.headers.copy()
                params = auth_info.query_params.copy()
                
                # Add API key to query params if needed
                if auth_info.api_key and not headers:
                    params["api_key"] = auth_info.api_key
                
                start_time = datetime.utcnow()
                
                # Make the request
                response = await client.request(
                    method=method,
                    url=endpoint_url,
                    headers=headers,
                    params=params
                )
                
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "headers": dict(response.headers),
                    "content_type": response.headers.get("content-type"),
                    "response_size": len(response.content),
                    "error_message": None if response.status_code < 400 else response.text[:200]
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time": None,
                "error_message": str(e)[:200]
            } 