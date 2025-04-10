import subprocess
import logging
import random

logger = logging.getLogger(__name__)

def check_xray_core():
    """Check if xray-core is available"""
    try:
        result = subprocess.run(
            ["xray", "version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        logger.warning("xray-core is not installed. Some functionality may be limited.")
        return False


def generate_short_id(length=6):
    """
    Generate a random short ID for Reality
    
    Args:
        length (int): Length of the short ID (default: 6)
        
    Returns:
        str: Random short ID
    """
    # Generate a random hex string
    return ''.join(random.choices('0123456789abcdef', k=length))

