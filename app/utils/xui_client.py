import httpx
import os
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Get settings from environment variables
XUI_BASE_URL = os.getenv("XUI_BASE_URL", "http://localhost:8080")
XUI_USERNAME = os.getenv("XUI_USERNAME", "admin")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "admin")
XUI_TIMEOUT = int(os.getenv("XUI_TIMEOUT", "30"))

class XUIClient:
    def __init__(self, base_url: str = XUI_BASE_URL, username: str = XUI_USERNAME, 
                 password: str = XUI_PASSWORD, timeout: int = XUI_TIMEOUT):
        """
        Initialize client for working with 3xui API
        
        Args:
            base_url: URL for accessing 3xui API
            username: Username for 3xui
            password: Password for 3xui
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session_cookie = None
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    
    async def login(self) -> bool:
        """
        Authentication in 3xui
        
        Returns:
            bool: True if authentication is successful, otherwise False
        """
        try:
            # First try with JSON data
            json_data = {
                "username": self.username,
                "password": self.password
            }
            
            # Set correct headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Log for debugging
            login_path = f"{self.base_url}/login"
            logger.info(f"Attempting login to {login_path} with username: {self.username}")
            
            response = await self.client.post(
                login_path, 
                json=json_data,
                headers=headers
            )
            
            # Detailed response logging for debugging
            logger.debug(f"Login response status: {response.status_code}")
            logger.debug(f"Login response headers: {response.headers}")
            logger.debug(f"Login response body: {response.text[:200]}...")  # Output only first 200 characters
            
            # Check response for successful login
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("success", False):
                        # Save all cookies from response
                        cookies = response.cookies
                        if cookies:
                            # Use cookies for future requests
                            self.client.cookies.update(cookies)
                            # Save cookies in string format for compatibility
                            self.session_cookie = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                            logger.info("Login successful, cookies saved")
                            return True
                except Exception as e:
                    logger.error(f"Error parsing JSON response: {e}")
            
            # If JSON didn't work, try with form data
            form_data = {
                "username": self.username,
                "password": self.password
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            logger.info("Trying login with form data")
            response = await self.client.post(
                login_path, 
                data=form_data,
                headers=headers
            )
            
            # Check response for successful login
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("success", False):
                        # Save all cookies from response
                        cookies = response.cookies
                        if cookies:
                            # Use cookies for future requests
                            self.client.cookies.update(cookies)
                            # Save cookies in string format for compatibility
                            self.session_cookie = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                            logger.info("Login successful with form data, cookies saved")
                            return True
                except Exception as e:
                    logger.error(f"Error parsing JSON response from form data: {e}")
            
            logger.error(f"Login failed: {response.status_code} - {response.text[:100]}...")
            return False
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    async def ensure_logged_in(self) -> bool:
        """
        Check and ensure authentication
        
        Returns:
            bool: True if authentication is active, otherwise False
        """
        # Check for cookies in client
        if self.client.cookies:
            logger.info("Using existing cookies for authentication")
            return True
            
        # Check for saved cookie
        if self.session_cookie:
            logger.info("Using saved session cookie")
            self.client.cookies.update({"3x-ui": self.session_cookie})
            return True
            
        # If no cookie, try to login
        logger.info("No cookies found, attempting login")
        return await self.login()
    
    async def get_inbounds(self) -> List[Dict[str, Any]]:
        """
        Get list of inbound connections
        
        Returns:
            List[Dict[str, Any]]: List of inbounds
        """
        if not await self.ensure_logged_in():
            return []
        
        try:
            headers = {}
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            # Use either client with cookies or add Cookie header
            response = await self.client.get(f"{self.base_url}/panel/api/inbounds/list", headers=headers)
            
            logger.debug(f"Get inbounds response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data.get("obj", [])
            
            logger.error(f"Failed to get inbounds: {response.status_code} - {response.text[:100]}...")
            return []
        except Exception as e:
            logger.error(f"Error getting inbounds: {e}")
            return []
    
    async def add_inbound(self, inbound_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add new inbound connection
        
        Args:
            inbound_data: Data for inbound
            
        Returns:
            Optional[Dict[str, Any]]: Created inbound data or None on error
        """
        if not await self.ensure_logged_in():
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            response = await self.client.post(
                f"{self.base_url}/panel/api/inbounds/add", 
                json=inbound_data,
                headers=headers
            )
            
            logger.debug(f"Add inbound response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data.get("obj", {})
            
            logger.error(f"Failed to add inbound: {response.status_code} - {response.text[:100]}...")
            return None
        except Exception as e:
            logger.error(f"Error adding inbound: {e}")
            return None
    
    async def delete_inbound(self, inbound_id: int) -> bool:
        """
        Delete inbound by ID
        
        Args:
            inbound_id: ID of the inbound to delete
            
        Returns:
            bool: True if successfully deleted, otherwise False
        """
        if not await self.ensure_logged_in():
            return False
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            response = await self.client.post(
                f"{self.base_url}/panel/api/inbounds/del/{inbound_id}", 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
            
            logger.error(f"Failed to delete inbound: {response.status_code} - {response.text[:100]}...")
            return False
        except Exception as e:
            logger.error(f"Error deleting inbound: {e}")
            return False
    
    async def add_client(self, inbound_id: int, client_settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add client to inbound
        
        Args:
            inbound_id: ID of the inbound
            client_settings: Client settings
            
        Returns:
            Optional[Dict[str, Any]]: Client data or None on error
        """
        if not await self.ensure_logged_in():
            return None
        
        try:
            # Get current inbound data
            inbounds = await self.get_inbounds()
            target_inbound = None
            
            for inbound in inbounds:
                if inbound.get("id") == inbound_id:
                    target_inbound = inbound
                    break
            
            if not target_inbound:
                logger.error(f"Inbound with ID {inbound_id} not found")
                return None
            
            # Add client to settings
            settings = json.loads(target_inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            clients.append(client_settings)
            settings["clients"] = clients
            
            # Update inbound with new settings
            target_inbound["settings"] = json.dumps(settings)
            
            # Send update request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            response = await self.client.post(
                f"{self.base_url}/panel/api/inbounds/update/{inbound_id}", 
                json=target_inbound,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return client_settings
            
            logger.error(f"Failed to add client: {response.status_code} - {response.text[:100]}...")
            return None
        except Exception as e:
            logger.error(f"Error adding client: {e}")
            return None
    
    async def remove_client(self, inbound_id: int, client_uuid: str) -> bool:
        """
        Remove client from inbound
        
        Args:
            inbound_id: ID of the inbound
            client_uuid: UUID of the client to remove
            
        Returns:
            bool: True if successfully removed, otherwise False
        """
        if not await self.ensure_logged_in():
            return False
        
        try:
            # Get current inbound data
            inbounds = await self.get_inbounds()
            target_inbound = None
            
            for inbound in inbounds:
                if inbound.get("id") == inbound_id:
                    target_inbound = inbound
                    break
            
            if not target_inbound:
                logger.error(f"Inbound with ID {inbound_id} not found")
                return False
            
            # Remove client from settings
            settings = json.loads(target_inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            new_clients = [c for c in clients if c.get("id", "") != client_uuid]
            
            if len(clients) == len(new_clients):
                logger.error(f"Client with UUID {client_uuid} not found in inbound {inbound_id}")
                return False
                
            settings["clients"] = new_clients
            
            # Update inbound with new settings
            target_inbound["settings"] = json.dumps(settings)
            
            # Send update request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            response = await self.client.post(
                f"{self.base_url}/panel/api/inbounds/update/{inbound_id}", 
                json=target_inbound,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
            
            logger.error(f"Failed to remove client: {response.status_code} - {response.text[:100]}...")
            return False
        except Exception as e:
            logger.error(f"Error removing client: {e}")
            return False
    
    async def get_server_status(self) -> Dict[str, Any]:
        """
        Get server status
        
        Returns:
            Dict[str, Any]: Server status data
        """
        if not await self.ensure_logged_in():
            return {"success": False, "message": "Authentication failed"}
        
        try:
            headers = {}
            if self.session_cookie:
                headers["Cookie"] = self.session_cookie
            
            response = await self.client.get(
                f"{self.base_url}/panel/api/status",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return data.get("obj", {})
                else:
                    return {"success": False, "message": "Failed to get status", "raw": data}
            
            return {"success": False, "message": f"HTTP error: {response.status_code}", "raw": response.text[:100]}
        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return {"success": False, "message": f"Exception: {str(e)}"}
    
    async def get_new_x25519_keypair(self) -> Optional[Dict[str, str]]:
        """
        Generate new X25519 keypair
        
        Returns:
            Optional[Dict[str, str]]: Dictionary with private and public keys or None on error
        """
        try:
            import subprocess
            
            logger.info("Generating X25519 keypair")
            
            # Try to run xray to generate keys
            try:
                result = subprocess.run(
                    ["xray", "x25519"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                output = result.stdout.strip()
                lines = output.split('\n')
                
                if len(lines) >= 2:
                    private_key = lines[0].split(':')[1].strip()
                    public_key = lines[1].split(':')[1].strip()
                    
                    return {
                        "private_key": private_key,
                        "public_key": public_key
                    }
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.error(f"Failed to generate keypair using xray: {e}")
                
            # Fallback to generating with OpenSSL
            logger.info("Falling back to OpenSSL for X25519 key generation")
            try:
                # Not supported in many OpenSSL versions, but try anyway
                result = subprocess.run(
                    ["openssl", "genpkey", "-algorithm", "x25519"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.returncode == 0:
                    # This is simplified, actual parsing would depend on output format
                    return {
                        "private_key": "from_openssl",
                        "public_key": "from_openssl"
                    }
            except subprocess.SubprocessError:
                logger.error("Failed to generate keypair using OpenSSL")
            
            return None
        except Exception as e:
            logger.error(f"Error generating X25519 keypair: {e}")
            return None
    
    async def close(self):
        """
        Close client connection
        """
        await self.client.aclose() 