"""
应用配置模块 - 完全修复版
解决 pydantic-settings JSON 解析错误
"""
import os
import json
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AppConfig:
    """应用配置类 - 简化版，避免 pydantic-settings 问题"""
    
    def __init__(self):
        # Supabase 配置
        self.SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        self.SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
        
        # 应用配置
        self.APP_NAME = "Vinow Backend API"
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # 安全配置
        self.JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "15"))
        self.REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "7"))
        
        # CORS 配置 - 手动处理逗号分隔的字符串
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
        self.CORS_ORIGINS = [origin.strip() for origin in cors_origins_str.split(",")]
        
        # 验证配置
        self.validate_config()
    
    def validate_config(self):
        """验证必要配置是否设置"""
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL 和 SUPABASE_SERVICE_KEY 必须配置在 .env 文件中")
        
        if not self.SUPABASE_URL.startswith("https://"):
            raise ValueError("SUPABASE_URL 格式不正确，应以 https:// 开头")
        
        print(f"✅ 配置加载成功 - {self.APP_NAME} v{self.APP_VERSION}")

# 创建全局配置实例
settings = AppConfig()


商家板块5数据分析
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """应用配置设置"""
    
    # FastAPI 配置
    APP_NAME: str = "Analytics Suite"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Supabase 配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()

增强版
import os
import logging
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """应用配置设置"""
    
    # FastAPI 配置
    APP_NAME: str = "Analytics Suite"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API 配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Analytics Suite API"
    
    # Supabase 配置
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_SERVICE_KEY: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # 安全配置
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS 配置
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # 数据库配置
    DATABASE_URL: str = Field(default="", env="DATABASE_URL")
    
    @property
    def log_level_int(self) -> int:
        """将日志级别字符串转换为整数"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(self.LOG_LEVEL.upper(), logging.INFO)

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

商家板块6财务中心
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # Supabase 配置
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    
    # 应用配置
    app_name: str = "商户财务中心"
    app_version: str = "1.0.0"
    debug: bool = Field(False, env="DEBUG")
    
    # 安全配置
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS 配置
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 缓存配置
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # 文件存储
    upload_dir: str = "exports"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()