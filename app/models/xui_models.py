from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import uuid
from app.utils.reality_keys import generate_short_id

class SniffingConfig(BaseModel):
    enabled: bool = True
    destOverride: List[str] = ["http", "tls", "quic"]
    metadataOnly: bool = False

class ClientTraffic(BaseModel):
    down: int = 0
    up: int = 0
    total: int = 0  # 0 means unlimited
    expiry_time: int = 0  # 0 means never expires

class ClientSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    security: str = "auto"
    encryption: str = "none"
    flow: Optional[str] = "xtls-rprx-vision"
    tls_settings: Optional[Dict[str, Any]] = None
    traffic: Optional[ClientTraffic] = None

class StreamSettings(BaseModel):
    network: str
    security: str
    reality_settings: Optional[Dict[str, Any]] = None
    tls_settings: Optional[Dict[str, Any]] = None
    ws_settings: Optional[Dict[str, Any]] = None
    grpc_settings: Optional[Dict[str, Any]] = None
    tcp_settings: Optional[Dict[str, Any]] = None

class VlessSettings(BaseModel):
    clients: List[ClientSettings] = []
    decryption: str = "none"
    fallbacks: List[Dict[str, Any]] = []

class InboundSettings(BaseModel):
    vless: Optional[VlessSettings] = None
    vmess: Optional[Dict[str, Any]] = None
    trojan: Optional[Dict[str, Any]] = None
    shadowsocks: Optional[Dict[str, Any]] = None

class XUIInbound(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    up: int = 0
    down: int = 0
    total: int = 0
    remark: str
    enable: bool = True
    port: int
    protocol: str
    settings: Union[InboundSettings, Dict[str, Any]]
    stream_settings: Union[StreamSettings, Dict[str, Any]]
    tag: str = "proxy"
    sniffing: SniffingConfig = SniffingConfig()
    
    class Config:
        json_schema_extra = {
            "example": {
                "remark": "remark",
                "port": 8888,
                "protocol": "vless",
                "settings": {
                    "vless": {
                        "clients": [
                            {
                                "id": "ur_generated_client_id",
                                "email": "user@example.com",
                                "flow": "xtls-rprx-vision"
                            }
                        ],
                        "decryption": "none",
                        "fallbacks": []
                    }
                },
                "stream_settings": {
                    "network": "tcp",
                    "security": "reality",
                    "reality_settings": {
                        "serverName": "example.com",
                        "fingerprint": "chrome",
                        "show": False,
                        "publicKey": "ur_generated_public_key",
                        "shortId": "ur_generated_short_id",
                        "spiderX": "/"
                    }
                }
            }
        }

class CreateInboundRequest(BaseModel):
    remark: str = Field(..., description="Название конфигурации")
    port: int = Field(..., description="Порт для подключения")
    protocol: str = Field(..., description="Протокол (vless, vmess, trojan)", example="vless")
    listen: Optional[str] = Field(None, description="IP для прослушивания (если не указан, будет использован IP сервера)")
    
    # Reality настройки
    is_reality: bool = Field(True, description="Использовать Reality")
    server_name: Optional[str] = Field("yahoo.com", description="Server Name для SNI", example="nl.wikipedia.org")
    public_key: str = Field(..., description="Публичный ключ Reality")
    private_key: Optional[str] = Field(None, description="Приватный ключ Reality (если не указан, будет использован существующий)")
    short_id: Optional[str] = Field(default_factory=lambda: generate_short_id(8), description="Short ID (если не указан, будет сгенерирован автоматически)")
    additional_short_ids: Optional[List[str]] = Field(None, description="Дополнительные Short ID (если не указаны, будут сгенерированы автоматически)")
    flow: str = Field("xtls-rprx-vision", description="Flow для VLESS")
    fingerprint: str = Field("chrome", description="Fingerprint для TLS")
    spider_x: str = Field("/", description="SpiderX для Reality")
    
    # Клиент
    client_email: Optional[str] = Field(None, description="Email клиента")
    client_id: Optional[str] = Field(None, description="UUID клиента (если не указан, будет сгенерирован)")
    sub_id: Optional[str] = Field(None, description="ID для подписки (если не указан, будет сгенерирован автоматически)")
    comment: Optional[str] = Field("", description="Комментарий")
    
    class Config:
        json_schema_extra = {
            "example": {
                "remark": "remark",
                "port": 8888,
                "protocol": "vless",
                "listen": "111.222.333.444",
                "is_reality": True, 
                "server_name": "example.com",
                "public_key": "ur_generated_public_key",
                "private_key": "ur_generated_private_key",
                "short_id": "ur_generated_short_id",
                "additional_short_ids": None,
                "flow": "xtls-rprx-vision",
                "client_email": "user@example.com",
                "sub_id": None,
                "comment": ""
            }
        }

class CreateClientRequest(BaseModel):
    inbound_id: int = Field(..., description="ID инбаунда")
    email: Optional[str] = Field(None, description="Email (метка) клиента. Если не указан, будет сгенерирован.")
    id: Optional[str] = Field(None, description="UUID клиента (если не указан, будет сгенерирован)")
    flow: Optional[str] = Field("xtls-rprx-vision", description="Flow для VLESS (игнорируется для других протоколов)")
    limit_ip: Optional[int] = Field(0, description="Лимит одновременных IP (0 = безлимит)")
    total_gb: Optional[int] = Field(0, description="Лимит трафика в ГБ (0 = безлимит)")
    expiry_time: Optional[int] = Field(0, description="Unix timestamp окончания срока действия в миллисекундах (0 = бессрочно)")
    enable: Optional[bool] = Field(True, description="Статус клиента (включен/выключен)")
    tg_id: Optional[str] = Field("", description="Telegram ID")
    sub_id: Optional[str] = Field(None, description="ID для генерации подписки (если не указан, будет сгенерирован)")

    class Config:
        json_schema_extra = {
            "example": {
                "inbound_id": 1,
                "email": "user@example.com",
                "flow": "xtls-rprx-vision",
                "limit_ip": 0,
                "total_gb": 0,
                "expiry_time": 0, # Example: 2025-01-01 UTC
                "enable": True,
                "tg_id": "",
                "sub_id": None
            }
        }

class RemoveClientRequest(BaseModel):
    inbound_id: int = Field(..., description="ID инбаунда")
    client_id: str = Field(..., description="UUID клиента")
    client_email: Optional[str] = Field(None, description="Email клиента")
    
    class Config:
        json_schema_extra = {
            "example": {
                "inbound_id": 1,
                "client_id": "ur_generated_client_id",
                "client_email": "user@example.com"
            }
        } 