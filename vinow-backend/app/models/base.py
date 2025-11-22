商家系统板块5商家数据分析
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

class BaseDBModel(BaseModel):
    """基础数据库模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TimeStampedModel(BaseDBModel):
    """时间戳模型"""
    created_at: datetime
    updated_at: datetime"""商家系统 - base"""

# TODO: 实现商家系统相关功能

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


交易系统


from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class BaseModelMixin(BaseModel):
    id: str = Field(..., description="唯一标识")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    is_deleted: bool = Field(default=False, description="软删除标志")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PaginatedResponse(BaseModel):
    items: list[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    has_next: bool = Field(..., description="是否有下一页")