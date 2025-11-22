import os 
from dotenv import load_dotenv 
 
load_dotenv() 
# app/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings: 
    """应用配置类""" 
    APP_NAME: str = os.getenv("APP_NAME", "Vinow") 
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0") 
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development") 
    SUPABASE_URL: str = os.getenv("SUPABASE_URL") 
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") 
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production") 
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256") 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    HOST: str = os.getenv("HOST", "0.0.0.0") 
    PORT: int = int(os.getenv("PORT", "8000")) 
 
    settings = Settings() 

    
class Config: # 应用配置
    PROJECT_NAME: str = "商家订单管理系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
class Config:
    case_sensitive = True

    settings = Settings()

    商户内容营销
    # 更新 app/config.py
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """应用配置"""
    
    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 应用配置
    PROJECT_NAME: str = "商家订单与内容营销系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime", "video/x-msvideo"]
    
    # 安全配置
    RATE_LIMIT_PER_MINUTE: int = 100
    API_KEY_HEADER: str = "X-API-Key"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        case_sensitive = True

settings = Settings()

内容系统
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置类 - 生产级别"""
    
    # 应用基础配置
    APP_NAME: str = "越南本地团购内容系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    ENVIRONMENT: str = Field("production", env="ENVIRONMENT")
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Content Management System"
    BACKEND_CORS_ORIGINS: List[str] = Field(["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Supabase配置
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_SERVICE_KEY: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # 数据库配置
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(10, env="DB_MAX_OVERFLOW")
    
    # 安全配置
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # 文件上传配置
    MAX_FILE_SIZE: int = Field(50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    MAX_IMAGE_SIZE: int = Field(10 * 1024 * 1024, env="MAX_IMAGE_SIZE")  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
    UPLOAD_DIRECTORY: str = Field("uploads", env="UPLOAD_DIRECTORY")
    
    # 存储配置
    STORAGE_BUCKET: str = Field("content-media", env="STORAGE_BUCKET")
    CDN_BASE_URL: str = Field("https://cdn.yourdomain.com", env="CDN_BASE_URL")
    BACKUP_BUCKET: str = Field("content-backups", env="BACKUP_BUCKET")
    
    # Redis缓存配置
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    
    # 视频处理配置
    VIDEO_TRANSCODE_RESOLUTIONS: List[str] = Field(["360p", "720p", "1080p"])
    VIDEO_MAX_DURATION: int = Field(300, env="VIDEO_MAX_DURATION")  # 5分钟
    VIDEO_THUMBNAIL_COUNT: int = Field(3, env="VIDEO_THUMBNAIL_COUNT")
    
    # 审核配置
    AUTO_MODERATION_ENABLED: bool = Field(True, env="AUTO_MODERATION_ENABLED")
    MODERATION_API_KEY: Optional[str] = Field(None, env="MODERATION_API_KEY")
    SENSITIVE_WORDS: List[str] = Field([], env="SENSITIVE_WORDS")
    
    # 邮件配置
    SMTP_SERVER: str = Field("smtp.gmail.com", env="SMTP_SERVER")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USERNAME: str = Field(..., env="SMTP_USERNAME")
    SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")
    
    # 异步任务配置
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # 监控配置
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # 业务配置
    DEFAULT_PAGE_SIZE: int = Field(20, env="DEFAULT_PAGE_SIZE")
    MAX_PAGE_SIZE: int = Field(100, env="MAX_PAGE_SIZE")
    CONTENT_AUTO_APPROVE_THRESHOLD: int = Field(80, env="CONTENT_AUTO_APPROVE_THRESHOLD")  # 内容自动审核通过阈值
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """组装CORS origins"""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("SENSITIVE_WORDS", pre=True)
    def assemble_sensitive_words(cls, v):
        """组装敏感词列表"""
        if isinstance(v, str):
            return [word.strip() for word in v.split(",")]
        return v
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例
settings = Settings()

# 日志配置
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = Field("Video Content System", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # Supabase配置
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # 安全配置
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32)
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 文件上传配置
    upload_dir: str = Field("./storage", env="UPLOAD_DIR")
    max_file_size: int = Field(50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_video_types: List[str] = Field(
        ["video/mp4", "video/avi", "video/mov", "video/mkv"], 
        env="ALLOWED_VIDEO_TYPES"
    )
    allowed_image_types: List[str] = Field(
        ["image/jpeg", "image/png", "image/gif"],
        env="ALLOWED_IMAGE_TYPES"
    )
    
    # Redis配置
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # Elasticsearch配置
    elasticsearch_url: str = Field("http://localhost:9200", env="ELASTICSEARCH_URL")
    elasticsearch_username: Optional[str] = Field(None, env="ELASTICSEARCH_USERNAME")
    elasticsearch_password: Optional[str] = Field(None, env="ELASTICSEARCH_PASSWORD")
    
    # Celery配置
    celery_broker_url: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # CORS配置
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    
    # 速率限制
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(1000, env="RATE_LIMIT_PER_HOUR")
    
    # 外部服务
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    cloudflare_account_id: Optional[str] = Field(None, env="CLOUDFLARE_ACCOUNT_ID")
    cloudflare_api_token: Optional[str] = Field(None, env="CLOUDFLARE_API_TOKEN")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_video_types", "allowed_image_types", pre=True)
    def parse_content_types(cls, v):
        if isinstance(v, str):
            return [ctype.strip() for ctype in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()