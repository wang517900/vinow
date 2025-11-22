print("Supabase URL:", os.getenv("SUPABASE_URL"))
print("Supabase KEY:", os.getenv("SUPABASE_SERVICE_KEY"))
# app/database/supabase_client.py
# ✅ 兼容 Supabase 2.3.1 最新稳定版

import os
import logging
from supabase import create_client, Client
from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# 初始化日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 直接从系统环境读取 .env 中的配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_supabase() -> Client | None:
    """创建并返回一个 Supabase 客户端实例（稳定增强版）"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Supabase 配置缺失，请检查 .env 文件中的 SUPABASE_URL 和 SUPABASE_SERVICE_KEY")
        return None

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # 测试连接
        _ = client.table("profiles").select("*").limit(1).execute()
        logger.info("✅ Supabase 客户端创建成功，并成功连接数据库")
        return client
    except Exception as e:
        logger.error(f"❌ Supabase 客户端创建失败: {e}")
        return None


class SupabaseClient:
    """Supabase客户端单例"""
    
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """获取Supabase客户端实例"""
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                logger.info("Supabase客户端初始化成功")
            except Exception as e:
                logger.error(f"Supabase客户端初始化失败: {e}")
                raise
        return cls._instance

# 创建全局客户端实例
supabase: Client = SupabaseClient.get_client()

async def test_connection():
    """测试数据库连接"""
    try:
        result = supabase.table("orders").select("*").limit(1).execute()
        logger.info("数据库连接测试成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

        商家板块6财务中心
        import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """Supabase 客户端封装"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """获取 Supabase 客户端实例"""
        if cls._instance is None:
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
        return cls._instance
    
    @classmethod
    async def execute_query(
        cls, 
        table: str,
        query: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """执行查询"""
        client = cls.get_client()
        
        # 构建查询
        query_builder = client.table(table).select(query)
        
        # 添加过滤条件
        if filters:
            for key, value in filters.items():
                if isinstance(value, (list, tuple)):
                    query_builder = query_builder.in_(key, value)
                else:
                    query_builder = query_builder.eq(key, value)
        
        # 添加排序
        if order_by:
            query_builder = query_builder.order(order_by)
        
        # 添加分页
        if limit:
            query_builder = query_builder.limit(limit)
        if offset:
            query_builder = query_builder.offset(offset)
        
        # 执行查询
        response = query_builder.execute()
        return response.data if hasattr(response, 'data') else []
    
    @classmethod
    async def insert_data(
        cls, 
        table: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """插入数据"""
        client = cls.get_client()
        response = client.table(table).insert(data).execute()
        return response.data[0] if response.data else {}
    
    @classmethod
    async def update_data(
        cls, 
        table: str, 
        data: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """更新数据"""
        client = cls.get_client()
        query_builder = client.table(table).update(data)
        
        for key, value in filters.items():
            query_builder = query_builder.eq(key, value)
        
        response = query_builder.execute()
        return response.data if hasattr(response, 'data') else []
    
    @classmethod
    async def delete_data(
        cls, 
        table: str, 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """删除数据"""
        client = cls.get_client()
        query_builder = client.table(table).delete()
        
        for key, value in filters.items():
            query_builder = query_builder.eq(key, value)
        
        response = query_builder.execute()
        return response.data if hasattr(response, 'data') else []


# 全局数据库客户端实例
db = SupabaseClient()

商家系统7评价管理数据库
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            url = os.getenv("SUPABASE_URL")
            key = os.get.env("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("Supabase URL and key must be set in environment variables")
            cls._instance = create_client(url, key)
        return cls._instance

# 创建数据库客户端实例
supabase = SupabaseClient.get_client()



交易系统


from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            try:
                cls._instance = create_client(settings.supabase_url, settings.supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return cls._instance
    
    @classmethod
    def get_service_client(cls) -> Client:
        """获取具有服务权限的客户端（用于管理操作）"""
        try:
            return create_client(settings.supabase_url, settings.supabase_service_key)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase service client: {e}")
            raise

# 全局数据库客户端实例
supabase = SupabaseClient.get_client()
supabase_service = SupabaseClient.get_service_client()


内容系统
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Supabase 数据库管理器"""
    
    _instance: Optional['SupabaseManager'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            try:
                self._client = create_client(
                    settings.supabase_url,
                    settings.supabase_key
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
    
    @property
    def client(self) -> Client:
        """获取 Supabase 客户端"""
        if self._client is None:
            raise RuntimeError("Supabase client not initialized")
        return self._client
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行原始 SQL 查询"""
        try:
            result = self._client.rpc('execute_sql', {'query': query, 'params': params or {}}).execute()
            return result.data
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """插入数据"""
        try:
            result = self._client.table(table).insert(data).execute()
            if result.data:
                return result.data[0]
            raise ValueError("Insert operation failed")
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {e}")
            raise
    
    async def select(self, table: str, columns: str = "*", filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """查询数据"""
        try:
            query = self._client.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    if isinstance(value, (list, tuple)):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Select failed for table {table}: {e}")
            raise
    
    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """更新数据"""
        try:
            query = self._client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Update failed for table {table}: {e}")
            raise
    
    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """删除数据"""
        try:
            query = self._client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Delete failed for table {table}: {e}")
            raise

# 全局数据库管理器实例
db_manager = SupabaseManager()

# 表名常量
class Tables:
    USERS = "users"
    USER_PROFILES = "user_profiles"
    CONTENT = "content"
    CONTENT_INTERACTIONS = "content_interactions"
    CONTENT_QUALITY_SCORES = "content_quality_scores"
    MODERATION_QUEUE = "moderation_queue"
    MODERATION_RESULTS = "moderation_results"
    CREATOR_GROWTH = "creator_growth"
    TAGS = "tags"
    CONTENT_TAGS = "content_tags"