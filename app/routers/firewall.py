from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Dict, Any
import os
from app.models.models import FirewallPort, FirewallStatus
from app.utils.firewall import open_port, close_port, check_port_status, get_ufw_status, is_ufw_available
from app.utils.ssh_client import SSHClient, SSHConfig

router = APIRouter()

def get_ssh_client() -> SSHClient:
    """
    Creates and returns SSH client with settings from .env
    """
    config = SSHConfig(
        hostname=os.getenv("SSH_HOST"),
        port=int(os.getenv("SSH_PORT", "22")),
        username=os.getenv("SSH_USERNAME"),
        password=os.getenv("SSH_PASSWORD"),
        timeout=int(os.getenv("SSH_TIMEOUT", "10"))
    )
    
    client = SSHClient(config)
    # Return client without closing connection
    # Connection will be closed automatically when request completes
    return client

@router.get("/status")
async def get_firewall_status(ssh_client: SSHClient = Depends(get_ssh_client)):
    """
    Gets firewall status on VDS
    """
    try:
        return ssh_client.check_ufw_status()
    finally:
        ssh_client.close()

@router.get("/rules")
async def get_firewall_rules(ssh_client: SSHClient = Depends(get_ssh_client)):
    """
    Gets firewall rules list in structured format
    """
    try:
        rules_response = ssh_client.get_ufw_rules()
        
        if not rules_response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=rules_response.get("message", "Failed to get firewall rules")
            )
        
        # Return structured rules
        return {
            "success": True,
            "count": rules_response.get("count", 0),
            "rules": rules_response.get("rules", {})
        }
    finally:
        ssh_client.close()

@router.post("/rules")
async def add_firewall_rule(
    port: int,
    protocol: str = "tcp",
    action: str = "allow",
    ssh_client: SSHClient = Depends(get_ssh_client)
):
    """
    Adds rule to firewall
    
    Parameters:
    - **port**: Port number to add
    - **protocol**: Protocol (tcp/udp), default tcp
    - **action**: Action (allow/deny), default allow
    
    Returns:
    - Information about operation result
    """
    try:
        return ssh_client.add_ufw_rule(port, protocol, action)
    finally:
        ssh_client.close()

@router.delete("/rules/{rule_number}")
async def delete_firewall_rule(
    rule_number: int,
    ssh_client: SSHClient = Depends(get_ssh_client)
):
    """
    Deletes rule from firewall
    """
    try:
        result = ssh_client.delete_ufw_rule(rule_number)
        return result
    finally:
        # Close SSH connection after request execution
        ssh_client.close()

@router.post("/ports")
async def open_new_port(port_data: FirewallPort, ssh_client: SSHClient = Depends(get_ssh_client)):
    """
    Opens new port in firewall
    
    - **port**: Port number to open
    - **protocol**: Protocol (tcp/udp)
    """
    try:
        # Check UFW status
        ufw_status = ssh_client.check_ufw_status()
        if ufw_status["status"] == "not_available":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="UFW is not available on this system"
            )
        
        # Add rule
        result = ssh_client.add_ufw_rule(port_data.port, port_data.protocol, "allow")
        
        if result["success"]:
            return {"message": f"Port {port_data.port}/{port_data.protocol} opened successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to open port: {result.get('message')}"
            )
    finally:
        ssh_client.close()

@router.delete("/ports/{port}")
async def close_port_endpoint(
    port: int, 
    protocol: str = "tcp",
    ssh_client: SSHClient = Depends(get_ssh_client)
):
    """
    Closes port in firewall
    
    Parameters:
    - **port**: Port number to close
    - **protocol**: Protocol (tcp/udp)
    """
    try:
        # Get rules list to find needed rule number
        rules_response = ssh_client.get_ufw_rules()
        
        if not rules_response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get firewall rules"
            )
            
        # Use structured rules for search
        rules = rules_response.get("rules", {})
        rule_number = None
        
        # Find rule with specified port and protocol
        for num, rule in rules.items():
            if (isinstance(num, int) and 
                rule.get("port") == str(port) and 
                rule.get("protocol", "").lower() == protocol.lower()):
                rule_number = num
                break
        
        if rule_number is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Port {port}/{protocol} not found in firewall rules"
            )
        
        # Delete rule by number
        result = ssh_client.delete_ufw_rule(rule_number)
        
        if result["success"]:
            return {"message": f"Port {port}/{protocol} closed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to close port: {result.get('message')}"
            )
    finally:
        ssh_client.close()

@router.get("/ports/{port}")
async def check_port(
    port: int, 
    protocol: str = Query("tcp", description="Protocol (tcp/udp)"), 
    ssh_client: SSHClient = Depends(get_ssh_client)
):
    """
    Checks if port is open in firewall
    
    Parameters:
    - **port**: Port number to check
    - **protocol**: Protocol (tcp/udp), default tcp
    
    Returns:
    - Information about IPv4 and IPv6 rules for specified port
    """
    try:
        # Get rules list and search for port
        rules_response = ssh_client.get_ufw_rules()
        
        if not rules_response["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get firewall rules"
            )
            
        # Use structured rules for search
        rules = rules_response.get("rules", {})
        
        # Create dictionaries to store IPv4 and IPv6 rules
        ipv4_rule = None
        ipv6_rule = None
        ipv4_rule_number = None
        ipv6_rule_number = None
        
        # Find rules with specified port and protocol - both for IPv4 and IPv6
        for num, rule in rules.items():
            if isinstance(num, int):
                # Get port and protocol
                if rule.get("port") == str(port) and rule.get("protocol", "").lower() == protocol.lower():
                    # Check if IPv4 or IPv6
                    if "(v6)" in rule.get("raw", ""):
                        ipv6_rule = rule
                        ipv6_rule_number = num
                    else:
                        ipv4_rule = rule
                        ipv4_rule_number = num
        
        # Form result
        result = {
            "port": str(port),
            "protocol": protocol,
            "ipv4": {
                "status": "closed",
                "message": f"Port {port}/{protocol} is not configured for IPv4"
            },
            "ipv6": {
                "status": "closed",
                "message": f"Port {port}/{protocol} is not configured for IPv6"
            }
        }
        
        # Add IPv4 rule information if found
        if ipv4_rule:
            result["ipv4"] = {
                "status": "open" if ipv4_rule.get("action") == "ALLOW" else "blocked",
                "rule_number": str(ipv4_rule_number),
                "details": ipv4_rule
            }
        
        # Add IPv6 rule information if found
        if ipv6_rule:
            result["ipv6"] = {
                "status": "open" if ipv6_rule.get("action") == "ALLOW" else "blocked",
                "rule_number": str(ipv6_rule_number),
                "details": ipv6_rule
            }
            
        return result
    finally:
        ssh_client.close() 