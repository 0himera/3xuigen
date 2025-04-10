from fastapi import APIRouter, HTTPException, status, Depends, Request, Form
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
import uuid
import os
import httpx
from app.utils.xui_client import XUIClient
from app.models.xui_models import (
    XUIInbound, CreateInboundRequest, CreateClientRequest, 
    RemoveClientRequest, ClientSettings
)
from app.utils.templates import HTML_LOGIN_FORM
import json
from app.utils.reality_keys import generate_short_id

router = APIRouter()

async def get_xui_client() -> XUIClient:
    """Dependency for getting the 3xui client"""
    client = XUIClient()
    try:
        yield client
    finally:
        await client.close()

@router.get("/status")
async def get_status(xui_client: XUIClient = Depends(get_xui_client)):
    """
    Get the status of the 3xui server with detailed diagnostics
    """
    try:
        # Check connection
        status_response = await xui_client.get_server_status()
        
        # If there's an error, try getting inbounds for additional diagnostics
        if not status_response.get("success"):
            inbounds_response = await xui_client.get_inbounds()
            
            return {
                "success": False,
                "message": "Failed to get server status",
                "status_error": status_response,
                "inbounds_check": {
                    "success": bool(inbounds_response),
                    "count": len(inbounds_response) if inbounds_response else 0,
                    "error": "Failed to get inbounds" if not inbounds_response else None
                },
                "diagnostics": {
                    "base_url": xui_client.base_url,
                    "is_authenticated": bool(xui_client.session_cookie),
                    "session_cookie": bool(xui_client.session_cookie)
                }
            }
        
        return status_response
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting server status: {str(e)}",
            "diagnostics": {
                "base_url": xui_client.base_url,
                "is_authenticated": bool(xui_client.session_cookie),
                "session_cookie": bool(xui_client.session_cookie)
            }
        }

@router.get("/connection-test")
async def test_connection(request: Request):
    """
    Test connection to 3xui with diagnostics
    """
    # Collect diagnostic data
    xui_url = os.getenv("XUI_BASE_URL", "not specified")
    username = os.getenv("XUI_USERNAME", "not specified")
    password_masked = "***" if os.getenv("XUI_PASSWORD") else "not specified"
    
    # Client information
    client_info = {
        "remote_address": request.client.host if request.client else "unknown",
        "headers": dict(request.headers)
    }
    
    # Check direct connection
    try:
        client = XUIClient()
        login_result = await client.login()
        
        if login_result:
            # Successful authentication - try to get data
            inbounds = await client.get_inbounds()
            server_status = await client.get_server_status()
            
            await client.close()
            
            return {
                "success": True,
                "message": "Connection to 3xui established successfully",
                "connection_info": {
                    "xui_url": xui_url,
                    "username": username,
                    "authentication": "successful",
                    "server_status_available": server_status.get("success", False),
                    "inbounds_count": len(inbounds)
                },
                "client_info": client_info
            }
        else:
            # Successful connection, but authentication failed
            await client.close()
            
            return {
                "success": False,
                "message": "Connection established, but authentication failed",
                "connection_info": {
                    "xui_url": xui_url,
                    "username": username,
                    "password_provided": bool(os.getenv("XUI_PASSWORD")),
                    "authentication": "failed"
                },
                "client_info": client_info,
                "troubleshooting": [
                    "Check the username and password for correctness",
                    "Ensure the URL for 3xui is specified correctly",
                    "Verify that the tunnel to the server is working correctly",
                    "Check that the 3xui server is running and accessible"
                ]
            }
    except Exception as e:
        # Connection error
        return {
            "success": False,
            "message": "Error connecting to 3xui",
            "error": str(e),
            "connection_info": {
                "xui_url": xui_url,
                "username": username,
                "password_provided": bool(os.getenv("XUI_PASSWORD"))
            },
            "client_info": client_info,
            "troubleshooting": [
                "Check if the specified URL is accessible",
                "Ensure the tunnel is configured correctly",
                "Verify network access to the server",
                "Check the URL format (should include http:// or https://)"
            ]
        }

@router.get("/inbounds", response_model=List[Dict[str, Any]])
async def get_inbounds(client: XUIClient = Depends(get_xui_client)):
    """
    Get the list of all inbounds from 3xui
    """
    inbounds = await client.get_inbounds()
    return inbounds

@router.post("/inbounds", status_code=status.HTTP_201_CREATED)
async def create_inbound(
    request: CreateInboundRequest,
    client: XUIClient = Depends(get_xui_client)
):
    """
    Create a new inbound in 3xui
    """
    # Prepare client with default additional fields
    client_id = request.client_id or str(uuid.uuid4())
    client_data = {
        "id": client_id,
        "email": request.client_email or f"user_{client_id}",
        "flow": request.flow if request.protocol == "vless" else "", # Flow only for VLESS
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": 0,
        "enable": True,
        "tgId": "",
        "subId": request.sub_id or str(uuid.uuid4()).replace("-", "")[:16], # Generate if not provided
        "comment": request.comment or "",
        "reset": 0
    }
    
    # Reality settings if enabled
    reality_opts = None
    if request.is_reality:
        # Check and add additional shortIds
        all_short_ids = [request.short_id]
        if request.additional_short_ids:
            all_short_ids.extend(request.additional_short_ids)
        else:
            # Automatically generate additional short IDs with different lengths
            # Generate 8 additional short IDs with different lengths like in the panel
            additional_ids = [
                generate_short_id(2),    # 2 characters
                generate_short_id(4),    # 4 characters
                generate_short_id(6),    # 6 characters
                generate_short_id(10),   # 10 characters
                generate_short_id(10),   # 10 characters
                generate_short_id(8),    # 8 characters
                generate_short_id(14),   # 14 characters
                generate_short_id(16)    # 16 characters
            ]
            all_short_ids.extend(additional_ids)
        
        # Determine domain and serverNames
        domain = request.server_name or "yahoo.com"
        server_names = []
        
        # Add base domain
        server_names.append(domain)
        
        # Add www. version if not already present
        if not domain.startswith("www."):
            server_names.append(f"www.{domain}")
        
        reality_opts = {
            "show": False,
            "xver": 0,
            "dest": f"{domain}:443",
            "serverNames": server_names,
            "privateKey": request.private_key or "", # Use provided or empty
            "minClient": "",
            "maxClient": "",
            "maxTimediff": 0,
            "shortIds": all_short_ids,
            # Nested settings object
            "settings": {
                "publicKey": request.public_key,
                "fingerprint": request.fingerprint,
                "serverName": "",
                "spiderX": request.spider_x
            }
        }
    
    # Create inbound settings based on protocol
    if request.protocol == "vless":
        settings_content = {
            "clients": [client_data],
            "decryption": "none",
            "fallbacks": []
        }
        # The settings key now contains a JSON string with pretty formatting
        settings_str = json.dumps(settings_content, indent=2)
    elif request.protocol == "vmess":
        client_data.pop("flow", None) # Remove flow for VMess
        settings_content = {
            "clients": [client_data],
            "disableInsecureEncryption": False
        }
        settings_str = json.dumps(settings_content, indent=2)
    elif request.protocol == "trojan":
        client_data.pop("flow", None) # Remove flow for Trojan
        settings_content = {
            "clients": [client_data],
            "fallbacks": []
        }
        settings_str = json.dumps(settings_content, indent=2)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported protocol: {request.protocol}"
        )
    
    # Stream settings
    stream_settings_dict = {
        "network": "tcp",
        "security": "reality" if request.is_reality else "none",
        "externalProxy": [],
        "tcpSettings": {
            "acceptProxyProtocol": False,
            "header": {
                "type": "none"
            }
        }
    }
    
    # Add Reality settings if available
    if reality_opts:
        stream_settings_dict["realitySettings"] = reality_opts
    
    # Convert streamSettings to JSON string with pretty formatting
    stream_settings_str = json.dumps(stream_settings_dict, indent=2)
    
    # Standard sniffing settings
    sniffing_dict = {
        "enabled": False,
        "destOverride": ["http", "tls", "quic", "fakedns"],
        "metadataOnly": False,
        "routeOnly": False
    }
    sniffing_str = json.dumps(sniffing_dict, indent=2)

    # Standard allocate settings
    allocate_dict = {
        "strategy": "always",
        "refresh": 5,
        "concurrency": 3
    }
    allocate_str = json.dumps(allocate_dict, indent=2)

    # Use IP from request or leave empty for automatic detection
    listen_ip = request.listen or ""
    
    # Create inbound data to send to XUIClient
    inbound_payload_for_client = {
        "remark": request.remark,
        "port": request.port,
        "protocol": request.protocol,
        "settings": settings_str,
        "streamSettings": stream_settings_str,
        "sniffing": sniffing_str,
        "allocate": allocate_str,
        "enable": True,
        "listen": listen_ip,
        "tag": f"inbound-{listen_ip}:{request.port}" if listen_ip else f"inbound-{request.port}"
    }
    
    # Send request
    result_obj = await client.add_inbound(inbound_payload_for_client)
    if not result_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create inbound in 3xui panel. Check API logs and panel logs."
        )
    
    # Return response
    return {
        "success": True,
        "message": "Inbound created successfully",
        "data": result_obj,
        "client": {
            "id": client_id,
            "email": client_data["email"],
            "sub_id": client_data["subId"],
            "flow": client_data.get("flow", "")
        },
        "reality": {
            "server_names": reality_opts["serverNames"] if reality_opts else None,
            "short_ids": reality_opts["shortIds"] if reality_opts else None,
            "public_key": request.public_key if request.is_reality else None
        } if request.is_reality else None
    }

@router.delete("/inbounds/{inbound_id}", status_code=status.HTTP_200_OK)
async def delete_inbound(
    inbound_id: int,
    client: XUIClient = Depends(get_xui_client)
):
    """
    Delete inbound by ID (uses POST request to 3xui)
    """
    result = await client.delete_inbound(inbound_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete inbound with ID {inbound_id}"
        )
    
    return {
        "success": True,
        "message": f"Inbound with ID {inbound_id} deleted successfully"
    }

@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def add_client_to_inbound(
    request: CreateClientRequest,
    client: XUIClient = Depends(get_xui_client)
):
    """
    Add client to an existing inbound
    """
    # Get list of inbounds to check if specified one exists
    inbounds = await client.get_inbounds()
    inbound = next((i for i in inbounds if i.get("id") == request.inbound_id), None)
    
    if not inbound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inbound with ID {request.inbound_id} not found"
        )
    
    # Determine protocol
    protocol = inbound.get("protocol", "").lower()
    
    # Prepare client data
    client_id = request.id or str(uuid.uuid4())
    client_settings = {
        "id": client_id,
        "email": request.email or f"user_{client_id}",
        # Add other client settings from CreateClientRequest if needed (limitIp, totalGB, expiryTime, etc.)
        # These should match the structure expected by 3xui when adding a client.
        # Example (add these to CreateClientRequest model first):
        # "limitIp": request.limit_ip or 0,
        # "totalGB": request.total_gb * 1024**3 if request.total_gb else 0, # Convert GB to bytes
        # "expiryTime": request.expiry_time or 0,
        # "enable": request.enable if request.enable is not None else True,
        # "tgId": request.tg_id or "",
        # "subId": request.sub_id or ""
    }
    
    if protocol == "vless" and request.flow:
        client_settings["flow"] = request.flow
    
    # Call the updated add_client method, passing only client_settings
    result = await client.add_client(request.inbound_id, client_settings)
    if result is None: # Check for None, as success might return null obj
        # Attempt to get more specific error info if possible
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add client to inbound {request.inbound_id}. Check server logs."
        )
    
    return {
        "success": True,
        "message": "Client added successfully",
        "data": {
            "inbound_id": request.inbound_id,
            "client": client_settings # Return the settings we sent
        }
    }

@router.post("/inbounds/{inbound_id}/clients/{client_uuid}", status_code=status.HTTP_200_OK)
async def remove_client_from_inbound(
    inbound_id: int,
    client_uuid: str,
    client: XUIClient = Depends(get_xui_client)
):
    """
    Remove client from inbound by UUID (uses POST to 3xui)
    """
    # Removed RemoveClientRequest model dependency
    result = await client.remove_client(inbound_id, client_uuid)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove client with UUID {client_uuid} from inbound {inbound_id}."
        )
    
    return {
        "success": True,
        "message": f"Client with UUID {client_uuid} removed successfully from inbound {inbound_id}."
    }

@router.post("/manual-login")
async def manual_login(
    url: str = Form(..., description="URL of 3xui panel"),
    username: str = Form(..., description="Username"),
    password: str = Form(..., description="Password")
):
    """
    Manual check of login to 3xui with detailed output
    """
    results = []
    
    # Method 1: Direct request with httpx
    try:
        results.append({"step": "Connection", "message": f"Connecting to {url}/login"})
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Try JSON
            results.append({"step": "Attempt 1", "message": "Attempting JSON authentication"})
            json_response = await client.post(
                f"{url}/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            results.append({
                "step": "JSON Response",
                "status_code": json_response.status_code,
                "headers": dict(json_response.headers),
                "cookies": dict(json_response.cookies),
                "response": json_response.text[:500]  # First 500 chars of response
            })
            
            # Check success
            json_success = False
            try:
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    json_success = json_data.get("success", False)
                    results.append({
                        "step": "JSON Check",
                        "success": json_success,
                        "data": json_data
                    })
            except Exception as e:
                results.append({
                    "step": "JSON Error",
                    "error": str(e)
                })
            
            # Try form-data if JSON failed
            if not json_success:
                results.append({"step": "Attempt 2", "message": "Attempting Form authentication"})
                form_response = await client.post(
                    f"{url}/login",
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                results.append({
                    "step": "Form Response",
                    "status_code": form_response.status_code,
                    "headers": dict(form_response.headers),
                    "cookies": dict(form_response.cookies),
                    "response": form_response.text[:500]  # First 500 chars of response
                })
                
                # Check success
                form_success = False
                try:
                    if form_response.status_code == 200:
                        form_data = form_response.json()
                        form_success = form_data.get("success", False)
                        results.append({
                            "step": "Form Check",
                            "success": form_success,
                            "data": form_data
                        })
                except Exception as e:
                    results.append({
                        "step": "Form Error",
                        "error": str(e)
                    })
            
            # Check cookies after either method
            if client.cookies:
                results.append({
                    "step": "Cookie Check",
                    "cookies_found": True,
                    "cookies": dict(client.cookies)
                })
            
            # Try requesting status or inbounds with obtained cookies
            if json_success or form_success or client.cookies:
                try:
                    status_response = await client.post(f"{url}/panel/api/server/status")
                    results.append({
                        "step": "Status Check",
                        "status_code": status_response.status_code,
                        "response": status_response.text[:500]
                    })
                    
                    inbounds_response = await client.get(f"{url}/panel/api/inbounds/list")
                    results.append({
                        "step": "Inbounds Check",
                        "status_code": inbounds_response.status_code,
                        "response": inbounds_response.text[:500]
                    })
                except Exception as e:
                    results.append({
                        "step": "API Check Error",
                        "error": str(e)
                    })
    
    except Exception as e:
        results.append({
            "step": "Connection Error",
            "error": str(e)
        })
    
    # Return all results for analysis
    return {
        "url": url,
        "username": username,
        "password_masked": "*" * len(password),
        "results": results
    }

@router.get("/login-form", response_class=HTMLResponse)
async def show_login_form():
    """
    Display HTML form for testing login to 3xui
    """
    return HTML_LOGIN_FORM 

@router.get("/generate-keypair")
async def generate_new_keypair(client: XUIClient = Depends(get_xui_client)):
    """
    Request 3xui to generate a new X25519 keypair for Reality.
    Returns the private and public keys.
    """
    key_pair = await client.get_new_x25519_keypair()
    if not key_pair:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate new keypair from 3xui panel. Check logs."
        )
    
    # Return only the keys, without the success/msg/obj wrapper from 3xui
    return {
        "privateKey": key_pair.get("privateKey"),
        "publicKey": key_pair.get("publicKey")
    } 