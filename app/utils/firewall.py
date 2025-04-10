import subprocess
import logging
from typing import Dict, List, Union, Optional

logger = logging.getLogger(__name__)

def is_ufw_available() -> bool:
    """
    Check if UFW is available on the system
    """
    try:
        result = subprocess.run(
            ["ufw", "status"], 
            capture_output=True, 
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        logger.error("UFW is not installed on this system")
        return False

def get_ufw_status() -> Dict[str, str]:
    """
    Get the status of UFW
    """
    if not is_ufw_available():
        return {"status": "not_available", "message": "UFW is not available on this system"}
    
    try:
        result = subprocess.run(
            ["ufw", "status"], 
            capture_output=True, 
            text=True,
            check=True
        )
        return {
            "status": "active" if "Status: active" in result.stdout else "inactive", 
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting UFW status: {e}")
        return {"status": "error", "message": str(e)}

def open_port(port: int, protocol: str = "tcp") -> Dict[str, str]:
    """
    Open a port with UFW
    """
    if not is_ufw_available():
        return {"status": "error", "message": "UFW is not available on this system"}
    
    try:
        result = subprocess.run(
            ["ufw", "allow", f"{port}/{protocol}"],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "success", "message": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error opening port {port}/{protocol}: {e}")
        return {"status": "error", "message": str(e)}

def close_port(port: int, protocol: str = "tcp") -> Dict[str, str]:
    """
    Close a port with UFW
    """
    if not is_ufw_available():
        return {"status": "error", "message": "UFW is not available on this system"}
    
    try:
        result = subprocess.run(
            ["ufw", "delete", "allow", f"{port}/{protocol}"],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "success", "message": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error closing port {port}/{protocol}: {e}")
        return {"status": "error", "message": str(e)}

def check_port_status(port: int, protocol: str = "tcp") -> Dict[str, str]:
    """
    Check if a port is open or closed
    """
    if not is_ufw_available():
        return {"status": "error", "message": "UFW is not available on this system"}
    
    try:
        result = subprocess.run(
            ["ufw", "status", "verbose"],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse the output and check if the port is open
        for line in result.stdout.splitlines():
            if f"{port}/{protocol}" in line and "ALLOW" in line:
                return {"status": "open", "port": port, "protocol": protocol}
        
        return {"status": "closed", "port": port, "protocol": protocol}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking port status {port}/{protocol}: {e}")
        return {"status": "error", "message": str(e)} 