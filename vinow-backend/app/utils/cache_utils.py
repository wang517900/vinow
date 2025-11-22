内容系统
"""
缓存管理工具模块

本模块提供了基于Redis的缓存管理功能，包括：
1. 基础缓存操作（设置、获取、删除）
2. 哈希表操作
3. 计数器操作（递增、递减）
4. 缓存模式匹配删除
5. 缓存健康检查
6. TTL管理和过期时间设置

所有操作都是异步安全的，并具有完善的异常处理机制。
"""

import json
from typing import Any, Optional, List, Dict
import redis
from app.config import settings
from app.database.connection import DatabaseManager
import logging
import asyncio

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = ['CacheManager', 'cache_manager', 'initialize_cache']


class CacheManager:
    """缓存管理器 - 生产级别Redis缓存管理"""
    
    def __init__(self):
        # Redis客户端实例
        self.redis_client: Optional[redis.Redis] = None
        # 默认缓存过期时间（秒）
        self.default_expire = 300
        
    async def initialize(self):
        """初始化Redis连接"""
        try:
            # 从数据库管理器获取Redis客户端
            self.redis_client = DatabaseManager.get_redis_client()
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis缓存管理器初始化成功")
        except Exception as e:
            logger.error(f"Redis缓存管理器初始化失败: {e}")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据或None
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return None
            
            # 从Redis获取数据
            value = self.redis_client.get(key)
            
            # 检查数据是否存在
            if value is None:
                return None
            
            # 尝试解析JSON数据
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始数据
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存获取异常 - 键: {key}, 错误: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒）
            
        Returns:
            设置是否成功
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return False
            
            # 确定过期时间
            actual_expire = expire if expire is not None else self.default_expire
            
            # 序列化数据为JSON
            if isinstance(value, (dict, list, tuple, int, float, bool, str)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                # 对于不支持的类型，转换为字符串
                serialized_value = str(value)
            
            # 设置缓存数据
            result = self.redis_client.setex(key, actual_expire, serialized_value)
            
            # 返回操作结果
            return bool(result)
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存设置异常 - 键: {key}, 错误: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            删除是否成功
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return False
            
            # 删除缓存数据
            result = self.redis_client.delete(key)
            
            # 返回操作结果
            return result > 0
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存删除异常 - 键: {key}, 错误: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        根据模式删除缓存数据
        
        Args:
            pattern: 键模式
            
        Returns:
            删除的键数量
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return 0
            
            # 查找匹配的键
            keys = self.redis_client.keys(pattern)
            
            # 检查是否有匹配的键
            if not keys:
                return 0
            
            # 删除所有匹配的键
            result = self.redis_client.delete(*keys)
            
            # 记录删除操作
            logger.info(f"缓存模式删除 - 模式: {pattern}, 删除键数: {result}")
            
            # 返回删除的键数量
            return result
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存模式删除异常 - 模式: {pattern}, 错误: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return False
            
            # 检查键是否存在
            return bool(self.redis_client.exists(key))
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存存在检查异常 - 键: {key}, 错误: {str(e)}")
            return False
    
    async def expire(self, key: str, expire: int) -> bool:
        """
        设置缓存过期时间
        
        Args:
            key: 缓存键
            expire: 过期时间（秒）
            
        Returns:
            设置是否成功
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return False
            
            # 设置过期时间
            return bool(self.redis_client.expire(key, expire))
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存过期设置异常 - 键: {key}, 错误: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """
        获取缓存剩余生存时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余生存时间（秒）或None
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return None
            
            # 获取剩余生存时间
            ttl = self.redis_client.ttl(key)
            
            # 返回剩余时间（-2表示键不存在，-1表示没有设置过期时间）
            if ttl == -2:
                return None  # 键不存在
            elif ttl == -1:
                return -1  # 没有设置过期时间
            else:
                return ttl  # 剩余时间
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存TTL获取异常 - 键: {key}, 错误: {str(e)}")
            return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递增缓存值
        
        Args:
            key: 缓存键
            amount: 递增数量
            
        Returns:
            递增后的值或None
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return None
            
            # 递增缓存值
            return self.redis_client.incr(key, amount)
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存递增异常 - 键: {key}, 错误: {str(e)}")
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递减缓存值
        
        Args:
            key: 缓存键
            amount: 递减数量
            
        Returns:
            递减后的值或None
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return None
            
            # 递减缓存值
            return self.redis_client.decr(key, amount)
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"缓存递减异常 - 键: {key}, 错误: {str(e)}")
            return None
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """
        设置哈希字段值
        
        Args:
            key: 哈希键
            field: 字段名
            value: 字段值
            
        Returns:
            设置是否成功
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return False
            
            # 序列化值为JSON
            if isinstance(value, (dict, list, tuple, int, float, bool, str)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                # 对于不支持的类型，转换为字符串
                serialized_value = str(value)
            
            # 设置哈希字段值
            result = self.redis_client.hset(key, field, serialized_value)
            
            # 返回操作结果
            return bool(result)
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"哈希设置异常 - 键: {key}, 字段: {field}, 错误: {str(e)}")
            return False
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """
        获取哈希字段值
        
        Args:
            key: 哈希键
            field: 字段名
            
        Returns:
            字段值或None
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return None
            
            # 获取哈希字段值
            value = self.redis_client.hget(key, field)
            
            # 检查值是否存在
            if value is None:
                return None
            
            # 尝试解析JSON数据
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始数据
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"哈希获取异常 - 键: {key}, 字段: {field}, 错误: {str(e)}")
            return None
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """
        获取所有哈希字段和值
        
        Args:
            key: 哈希键
            
        Returns:
            字段值字典
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return {}
            
            # 获取所有哈希字段和值
            hash_data = self.redis_client.hgetall(key)
            
            # 解析JSON数据
            result = {}
            for field, value in hash_data.items():
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                try:
                    result[field_str] = json.loads(value)
                except json.JSONDecodeError:
                    result[field_str] = value.decode('utf-8') if isinstance(value, bytes) else value
            
            # 返回解析后的数据
            return result
            
        except Exception as e:
            # 记录异常，但不抛出（缓存失败不应该影响主流程）
            logger.warning(f"哈希获取全部异常 - 键: {key}, 错误: {str(e)}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        缓存健康检查
        
        Returns:
            健康状态信息
        """
        try:
            # 检查Redis客户端是否可用
            if not self.redis_client:
                return {
                    "status": "unhealthy",
                    "message": "Redis客户端未初始化"
                }
            
            # 测试Redis连接
            self.redis_client.ping()
            
            # 获取Redis信息
            info = self.redis_client.info()
            
            # 返回健康状态
            return {
                "status": "healthy",
                "message": "Redis连接正常",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
            
        except Exception as e:
            # 返回不健康状态
            return {
                "status": "unhealthy",
                "message": f"Redis连接异常: {str(e)}"
            }


# 创建全局缓存管理器实例
cache_manager = CacheManager()


# 异步初始化缓存管理器
async def initialize_cache():
    """初始化缓存管理器"""
    await cache_manager.initialize()

内容板块-Redis缓存管理

import json
import logging
import asyncio
from typing import Any, Optional, List, Dict
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理类"""
    
    def __init__(self):
        self.redis_client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_URL,
                port=6379,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )
            logger.info("Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存值"""
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, expire, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存键"""
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> bool:
        """按模式删除缓存键"""
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Redis delete pattern error for {pattern}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增键值"""
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error for key {key}: {str(e)}")
            return None
    
    async def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """递减键值"""
        try:
            return await self.redis_client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decr error for key {key}: {str(e)}")
            return None
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """设置哈希字段"""
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.hset(key, field, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis hset error for key {key}.{field}: {str(e)}")
            return False
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """获取哈希字段"""
        try:
            value = await self.redis_client.hget(key, field)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis hget error for key {key}.{field}: {str(e)}")
            return None
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            data = await self.redis_client.hgetall(key)
            result = {}
            for field, value in data.items():
                result[field] = json.loads(value)
            return result
        except Exception as e:
            logger.error(f"Redis hgetall error for key {key}: {str(e)}")
            return {}
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        try:
            await self.redis_client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """获取键的剩余生存时间"""
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error for key {key}: {str(e)}")
            return None
    
    async def ping(self) -> bool:
        """检查Redis连接"""
        try:
            return await self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False
    
    async def close(self):
        """关闭Redis连接"""
        try:
            await self.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")


# 全局缓存实例
cache_redis = RedisCache()


def cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [prefix]
    
    # 添加位置参数
    for arg in args:
        key_parts.append(str(arg))
    
    # 添加关键字参数
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    return ":".join(key_parts)