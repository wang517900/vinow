交易系统
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class Settings(BaseSettings):
    """
    应用程序配置设置类
    使用 Pydantic 进行配置验证和类型检查
    """
    
    # ==================== 应用基础配置 ====================
    app_name: str = "Trade Platform API"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # ==================== Supabase 数据库配置 ====================
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # ==================== Redis 缓存配置 ====================
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # ==================== Celery 异步任务配置 ====================
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # ==================== CORS 跨域配置 ====================
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # ==================== 订单相关配置 ====================
    order_timeout_minutes: int = int(os.getenv("ORDER_TIMEOUT_MINUTES", "30"))
    payment_timeout_minutes: int = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "15"))
    
    # ==================== 配置验证 ====================
    @validator('secret_key')
    def secret_key_must_not_be_empty(cls, v: str) -> str:
        """验证 SECRET_KEY 是否为空"""
        if not v and not os.getenv("DEBUG", "False").lower() == "true":
            raise ValueError('SECRET_KEY must be set in production environment')
        return v
    
    @validator('supabase_url', 'supabase_key')
    def supabase_config_must_not_be_empty(cls, v: str, field) -> str:
        """验证 Supabase 配置是否为空"""
        if not v and not os.getenv("DEBUG", "False").lower() == "true":
            raise ValueError(f'{field.name} must be set in production environment')
        return v
    
    @validator('cors_origins', pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """解析 CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        """
        Pydantic 配置类
        """
        # 指定环境变量文件
        env_file = ".env"
        # 忽略大小写
        case_sensitive = False

# 创建全局配置实例
settings = Settings()