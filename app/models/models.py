from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime



class FirewallPort(BaseModel):
    port: int
    protocol: str = "tcp"  # tcp, udp, or both
    
    class Config:
        json_schema_extra = {
            "example": {
                "port": 8443,
                "protocol": "tcp"
            }
        }

class FirewallStatus(BaseModel):
    port: int
    protocol: str
    status: str  # open, closed
    
    class Config:
        json_schema_extra = {
            "example": {
                "port": 8443,
                "protocol": "tcp",
                "status": "open"
            }
        }