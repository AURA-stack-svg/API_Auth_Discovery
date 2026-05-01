"""
Code generator for creating sample code examples for discovered APIs.
"""

from typing import List, Dict, Any
from ..models.api_result import CodeExample, AuthenticationInfo, AuthStrategy


class CodeGenerator:
    """Generates code examples for discovered APIs."""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load code templates for different languages and auth strategies."""
        return {
            "python": {
                "api_key": '''import requests

# API Configuration
API_KEY = "{api_key}"
BASE_URL = "{base_url}"

# Headers
headers = {{
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}}

# Make a request
response = requests.get(f"{{BASE_URL}}/endpoint", headers=headers)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {{response.status_code}} - {{response.text}}")''',
                
                "bearer_token": '''import requests

# API Configuration
BEARER_TOKEN = "{bearer_token}"
BASE_URL = "{base_url}"

# Headers
headers = {{
    "Authorization": f"Bearer {{BEARER_TOKEN}}",
    "Content-Type": "application/json"
}}

# Make a request
response = requests.get(f"{{BASE_URL}}/endpoint", headers=headers)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {{response.status_code}} - {{response.text}}")''',
                
                "oauth2": '''import requests
from requests_oauthlib import OAuth2Session

# OAuth2 Configuration
CLIENT_ID = "{client_id}"
CLIENT_SECRET = "{client_secret}"
AUTH_URL = "{auth_url}"
TOKEN_URL = "{token_url}"
BASE_URL = "{base_url}"

# OAuth2 Flow
oauth = OAuth2Session(CLIENT_ID)
authorization_url, state = oauth.authorization_url(AUTH_URL)

print(f"Please go to {{authorization_url}} and authorize access.")
authorization_response = input("Enter the full callback URL: ")

token = oauth.fetch_token(
    TOKEN_URL,
    authorization_response=authorization_response,
    client_secret=CLIENT_SECRET
)

# Make authenticated request
response = oauth.get(f"{{BASE_URL}}/endpoint")

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {{response.status_code}} - {{response.text}}")'''
            },
            
            "javascript": {
                "api_key": '''const axios = require('axios');

// API Configuration
const API_KEY = '{api_key}';
const BASE_URL = '{base_url}';

// Headers
const headers = {{
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}};

// Make a request
async function fetchData() {{
    try {{
        const response = await axios.get(`${{BASE_URL}}/endpoint`, {{ headers }});
        console.log(response.data);
    }} catch (error) {{
        console.error('Error:', error.response?.status, error.response?.data);
    }}
}}

fetchData();''',
                
                "bearer_token": '''const axios = require('axios');

// API Configuration
const BEARER_TOKEN = '{bearer_token}';
const BASE_URL = '{base_url}';

// Headers
const headers = {{
    'Authorization': `Bearer ${{BEARER_TOKEN}}`,
    'Content-Type': 'application/json'
}};

// Make a request
async function fetchData() {{
    try {{
        const response = await axios.get(`${{BASE_URL}}/endpoint`, {{ headers }});
        console.log(response.data);
    }} catch (error) {{
        console.error('Error:', error.response?.status, error.response?.data);
    }}
}}

fetchData();''',
                
                "oauth2": '''const axios = require('axios');

// OAuth2 Configuration
const CLIENT_ID = '{client_id}';
const CLIENT_SECRET = '{client_secret}';
const AUTH_URL = '{auth_url}';
const TOKEN_URL = '{token_url}';
const BASE_URL = '{base_url}';

// OAuth2 Flow (simplified - you'll need to handle the full flow)
async function getAccessToken(authorizationCode) {{
    const tokenResponse = await axios.post(TOKEN_URL, {{
        grant_type: 'authorization_code',
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        code: authorizationCode
    }});
    
    return tokenResponse.data.access_token;
}}

// Make authenticated request
async function fetchData(accessToken) {{
    try {{
        const response = await axios.get(`${{BASE_URL}}/endpoint`, {{
            headers: {{
                'Authorization': `Bearer ${{accessToken}}`,
                'Content-Type': 'application/json'
            }}
        }});
        console.log(response.data);
    }} catch (error) {{
        console.error('Error:', error.response?.status, error.response?.data);
    }}
}}

// Usage: First get authorization code, then use it to get access token
// const accessToken = await getAccessToken('your_authorization_code');
// fetchData(accessToken);'''
            },
            
            "curl": {
                "api_key": '''# API Key Authentication
curl -X GET "{base_url}/endpoint" \\
  -H "X-API-Key: {api_key}" \\
  -H "Content-Type: application/json"''',
                
                "bearer_token": '''# Bearer Token Authentication
curl -X GET "{base_url}/endpoint" \\
  -H "Authorization: Bearer {bearer_token}" \\
  -H "Content-Type: application/json"''',
                
                "oauth2": '''# OAuth2 Authentication (Step 1: Get authorization code)
# Visit this URL in your browser:
# {auth_url}?client_id={client_id}&response_type=code&redirect_uri=YOUR_REDIRECT_URI

# Step 2: Exchange authorization code for access token
curl -X POST "{token_url}" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=authorization_code" \\
  -d "client_id={client_id}" \\
  -d "client_secret={client_secret}" \\
  -d "code=YOUR_AUTHORIZATION_CODE"

# Step 3: Use access token to make API calls
curl -X GET "{base_url}/endpoint" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json"'''
            }
        }
    
    async def generate_code_examples(
        self,
        api_info: Dict[str, Any],
        auth_info: AuthenticationInfo
    ) -> List[CodeExample]:
        """Generate code examples for the API."""
        
        examples = []
        
        # Get base information
        base_url = api_info.get("base_url", "https://api.example.com")
        api_name = api_info.get("api_name", "API")
        
        # Generate examples for each language
        for language in ["python", "javascript", "curl"]:
            try:
                code = self._generate_code_for_language(
                    language=language,
                    auth_info=auth_info,
                    base_url=base_url,
                    api_name=api_name
                )
                
                if code:
                    examples.append(CodeExample(
                        language=language,
                        code=code,
                        description=f"{language.title()} example for {api_name}"
                    ))
                    
            except Exception as e:
                # Skip this language if there's an error
                continue
        
        return examples
    
    def _generate_code_for_language(
        self,
        language: str,
        auth_info: AuthenticationInfo,
        base_url: str,
        api_name: str
    ) -> str:
        """Generate code for a specific language."""
        
        auth_strategy = auth_info.strategy.value
        
        # Get the template for this language and auth strategy
        if language not in self.templates:
            return ""
        
        if auth_strategy not in self.templates[language]:
            # Fallback to api_key template
            auth_strategy = "api_key"
        
        template = self.templates[language][auth_strategy]
        
        # Prepare template variables
        template_vars = {
            "base_url": base_url,
            "api_name": api_name,
            "api_key": auth_info.api_key or "YOUR_API_KEY_HERE",
            "bearer_token": auth_info.token or "YOUR_BEARER_TOKEN_HERE",
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "auth_url": "https://api.example.com/oauth/authorize",
            "token_url": "https://api.example.com/oauth/token"
        }
        
        # Update OAuth2 URLs if available
        if auth_info.oauth_config:
            template_vars.update({
                "client_id": auth_info.oauth_config.get("client_id", "YOUR_CLIENT_ID"),
                "client_secret": auth_info.oauth_config.get("client_secret", "YOUR_CLIENT_SECRET"),
                "auth_url": auth_info.oauth_config.get("auth_url", "https://api.example.com/oauth/authorize"),
                "token_url": auth_info.oauth_config.get("token_url", "https://api.example.com/oauth/token")
            })
        
        # Format the template
        try:
            return template.format(**template_vars)
        except KeyError as e:
            # If there's a missing variable, return a basic template
            return self._generate_basic_template(language, base_url, api_name)
    
    def _generate_basic_template(self, language: str, base_url: str, api_name: str) -> str:
        """Generate a basic template when the main template fails."""
        
        if language == "python":
            return f'''import requests

# {api_name} API
BASE_URL = "{base_url}"

# Make a request (add your authentication headers)
response = requests.get(f"{{BASE_URL}}/endpoint")
print(response.json())'''
        
        elif language == "javascript":
            return f'''const axios = require('axios');

// {api_name} API
const BASE_URL = '{base_url}';

// Make a request (add your authentication headers)
async function fetchData() {{
    const response = await axios.get(`${{BASE_URL}}/endpoint`);
    console.log(response.data);
}}

fetchData();'''
        
        elif language == "curl":
            return f'''# {api_name} API
curl -X GET "{base_url}/endpoint" \\
  -H "Content-Type: application/json"'''
        
        return ""
    
    def generate_custom_example(
        self,
        language: str,
        endpoint_url: str,
        method: str,
        auth_info: AuthenticationInfo,
        parameters: Dict[str, Any] = None
    ) -> str:
        """Generate a custom code example for a specific endpoint."""
        
        if language == "python":
            return self._generate_python_custom(endpoint_url, method, auth_info, parameters)
        elif language == "javascript":
            return self._generate_javascript_custom(endpoint_url, method, auth_info, parameters)
        elif language == "curl":
            return self._generate_curl_custom(endpoint_url, method, auth_info, parameters)
        
        return ""
    
    def _generate_python_custom(
        self,
        endpoint_url: str,
        method: str,
        auth_info: AuthenticationInfo,
        parameters: Dict[str, Any] = None
    ) -> str:
        """Generate custom Python code."""
        
        headers = auth_info.headers.copy()
        headers["Content-Type"] = "application/json"
        
        params_str = ""
        if parameters:
            params_str = f"params = {parameters}\n"
        
        method_call = f"requests.{method.lower()}"
        params_arg = ", params=params" if parameters and method.upper() == "GET" else ""
        data_arg = ", json=params" if parameters and method.upper() != "GET" else ""
        
        return f'''import requests

# API Configuration
headers = {headers}
{params_str}
# Make request
response = {method_call}("{endpoint_url}", headers=headers{params_arg}{data_arg})

if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {{response.status_code}} - {{response.text}}")'''
    
    def _generate_javascript_custom(
        self,
        endpoint_url: str,
        method: str,
        auth_info: AuthenticationInfo,
        parameters: Dict[str, Any] = None
    ) -> str:
        """Generate custom JavaScript code."""
        
        headers = auth_info.headers.copy()
        headers["Content-Type"] = "application/json"
        
        config = f"{{ headers: {headers}"
        
        if parameters:
            if method.upper() == "GET":
                config += f", params: {parameters}"
            else:
                config += f", data: {parameters}"
        
        config += " }"
        
        return f'''const axios = require('axios');

async function makeRequest() {{
    try {{
        const response = await axios.{method.lower()}('{endpoint_url}', {config});
        console.log(response.data);
    }} catch (error) {{
        console.error('Error:', error.response?.status, error.response?.data);
    }}
}}

makeRequest();'''
    
    def _generate_curl_custom(
        self,
        endpoint_url: str,
        method: str,
        auth_info: AuthenticationInfo,
        parameters: Dict[str, Any] = None
    ) -> str:
        """Generate custom cURL code."""
        
        headers_str = ""
        for key, value in auth_info.headers.items():
            headers_str += f' \\\n  -H "{key}: {value}"'
        
        data_str = ""
        if parameters and method.upper() != "GET":
            import json
            data_str = f' \\\n  -d \'{json.dumps(parameters)}\''
        
        return f'''curl -X {method.upper()} "{endpoint_url}"{headers_str}{data_str}''' 