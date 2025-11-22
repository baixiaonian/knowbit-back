"""
应用配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    APP_NAME: str = "AI Writing Tool"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DB_USERNAME: str = "postgres"
    DB_PASSWORD: str = "dn2hf6sn"
    DB_HOST: str = "dbconn.sealosbja.site"
    DB_PORT: int = 48364
    DB_NAME: str = "ai_write_database"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    CORS_ORIGINS: list = ["*"]
    
    # 微信公众号配置
    WECHAT_APPID: Optional[str] = None
    WECHAT_APPSECRET: Optional[str] = None
    WECHAT_TOKEN: Optional[str] = None  # 服务器配置中的Token
    WECHAT_ENCODING_AES_KEY: Optional[str] = None  # EncodingAESKey（安全模式需要，明文模式可忽略）
    WECHAT_QR_EXPIRE_SECONDS: int = 300  # 二维码有效期（5分钟）
    
    # 登录验证码配置
    LOGIN_CODE_EXPIRE_SECONDS: int = 60  # 验证码有效期（1分钟）
    LOGIN_CODE_LENGTH: int = 6  # 验证码长度
    
    # Embedding配置（统一使用环境变量）
    EMBEDDING_API_KEY: Optional[str] = "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
    EMBEDDING_API_BASE: Optional[str] = "https://aiproxy.bja.sealos.run/v1"
    EMBEDDING_MODEL: Optional[str] = "qwen3-embedding-0.6b"
    EMBEDDING_API_MODEL: Optional[str] = "qwen3-embedding-0.6b"  # 兼容旧的环境变量名
    
    @property
    def DATABASE_URL(self) -> str:
        """获取数据库连接URL"""
        return f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

