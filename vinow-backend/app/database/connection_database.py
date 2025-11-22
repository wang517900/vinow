内容系统
"""
数据库连接管理模块

本模块提供了统一的数据库连接管理，支持多种数据库类型：
- Supabase (PostgreSQL)
- Redis (缓存)
- SQLAlchemy (ORM)

采用单例模式确保每个数据库只有一个连接实例，提高性能并减少资源消耗。
"""

import asyncio
from typing import Optional, Dict, Any
from supabase import create_client, Client
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
from app.config import settings
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

__all__ = ['DatabaseManager', 'Base', 'supabase', 'redis_client', 'SessionLocal']


class DatabaseManager:
    """数据库连接管理器 - 生产级别"""
    
    _supabase_instance: Optional[Client] = None
    _sqlalchemy_engine = None
    _sqlalchemy_session_local = None
    _redis_instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_supabase_client(cls) -> Client:
        """
        获取Supabase客户端单例
        
        Returns:
            Supabase客户端实例
            
        Raises:
            Exception: 初始化失败时抛出异常
        """
        if cls._supabase_instance is None:
            try:
                cls._supabase_instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                # 测试连接
                cls._supabase_instance.table("health_check").select("count").limit(1).execute()
                logger.info("Supabase客户端初始化成功")
            except Exception as e:
                logger.error(f"Supabase客户端初始化失败: {e}")
                raise
        return cls._supabase_instance
    
    @classmethod
    def get_sqlalchemy_engine(cls):
        """
        获取SQLAlchemy引擎（用于复杂查询）
        
        Returns:
            SQLAlchemy引擎实例
            
        Raises:
            Exception: 初始化失败时抛出异常
        """
        if cls._sqlalchemy_engine is None:
            try:
                cls._sqlalchemy_engine = create_engine(
                    settings.DATABASE_URL,
                    pool_size=settings.DB_POOL_SIZE,
                    max_overflow=settings.DB_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    pool_recycle=3600,  # 1小时回收连接
                    echo=settings.DEBUG
                )
                logger.info("SQLAlchemy引擎初始化成功")
            except Exception as e:
                logger.error(f"SQLAlchemy引擎初始化失败: {e}")
                raise
        return cls._sqlalchemy_engine
    
    @classmethod
    def get_session_local(cls):
        """
        获取SQLAlchemy会话工厂
        
        Returns:
            SQLAlchemy会话工厂
        """
        if cls._sqlalchemy_session_local is None:
            engine = cls.get_sqlalchemy_engine()
            cls._sqlalchemy_session_local = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=engine
            )
        return cls._sqlalchemy_session_local
    
    @classmethod
    def get_redis_client(cls) -> redis.Redis:
        """
        获取Redis客户端
        
        Returns:
            Redis客户端实例
            
        Raises:
            Exception: 初始化失败时抛出异常
        """
        if cls._redis_instance is None:
            try:
                cls._redis_instance = redis.Redis.from_url(
                    settings.REDIS_URL,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,  # 30秒健康检查间隔
                    max_connections=settings.REDIS_MAX_CONNECTIONS or 10
                )
                # 测试连接
                cls._redis_instance.ping()
                logger.info("Redis客户端初始化成功")
            except Exception as e:
                logger.error(f"Redis客户端初始化失败: {e}")
                raise
        return cls._redis_instance
    
    @classmethod
    @contextmanager
    def get_db_session(cls):
        """
        获取数据库会话上下文管理器
        
        Yields:
            SQLAlchemy数据库会话对象
        """
        session_local = cls.get_session_local()
        db = session_local()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库会话异常: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @classmethod
    async def health_check(cls) -> Dict[str, Any]:
        """
        数据库健康检查
        
        Returns:
            各数据库连接状态的字典
            {
                "supabase": bool,
                "redis": bool,
                "sqlalchemy": bool,
                "timestamp": datetime
            }
        """
        health_status = {
            "supabase": False,
            "redis": False,
            "sqlalchemy": False,
            "timestamp": datetime.utcnow()
        }
        
        try:
            # 检查Supabase
            supabase = cls.get_supabase_client()
            supabase.table("health_check").select("count").limit(1).execute()
            health_status["supabase"] = True
        except Exception as e:
            logger.error(f"Supabase健康检查失败: {e}")
        
        try:
            # 检查Redis
            redis_client = cls.get_redis_client()
            redis_client.ping()
            health_status["redis"] = True
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
        
        try:
            # 检查SQLAlchemy
            engine = cls.get_sqlalchemy_engine()
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            health_status["sqlalchemy"] = True
        except Exception as e:
            logger.error(f"SQLAlchemy健康检查失败: {e}")
        
        return health_status
    
    @classmethod
    def close_connections(cls):
        """关闭所有数据库连接"""
        try:
            if cls._sqlalchemy_engine:
                cls._sqlalchemy_engine.dispose()
                cls._sqlalchemy_engine = None
            
            if cls._redis_instance:
                cls._redis_instance.close()
                cls._redis_instance = None
                
            cls._supabase_instance = None
            logger.info("所有数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时发生错误: {e}", exc_info=True)


# 全局数据库实例
Base = declarative_base()
supabase = DatabaseManager.get_supabase_client()
redis_client = DatabaseManager.get_redis_client()
SessionLocal = DatabaseManager.get_session_local()