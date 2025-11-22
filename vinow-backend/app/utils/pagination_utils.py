内容板块
"""
分页工具模块

本模块提供了分页相关的工具函数和数据模型，包括：
1. 基于页码的分页（PaginationParams, PaginatedResult）
2. 基于游标的分页（CursorPaginationParams, CursorPaginatedResult）
3. 分页参数验证和计算工具函数
4. SQLAlchemy查询分页辅助函数

支持两种分页方式：
- 传统分页：基于页码和每页大小
- 游标分页：基于游标，适用于无限滚动场景
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from fastapi import Query

__all__ = [
    'PaginationParams',
    'get_pagination_params',
    'PaginatedResult',
    'paginate_query',
    'calculate_pagination_info',
    'CursorPaginationParams',
    'CursorPaginatedResult',
    'validate_pagination_params',
    'get_offset_limit'
]


class PaginationParams(BaseModel):
    """
    分页参数模型 - 用于统一处理分页参数
    """
    model_config = ConfigDict(from_attributes=True)
    
    page: int = Field(1, ge=1, description="页码，从1开始")  # 页码
    page_size: int = Field(20, ge=1, le=100, description="每页大小，1-100")  # 每页大小

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """
        验证每页大小
        
        Args:
            v: 每页大小值
            
        Returns:
            验证后的每页大小
            
        Raises:
            ValueError: 当每页大小不在有效范围内时抛出
        """
        # 确保每页大小在合理范围内
        if v < 1:
            raise ValueError('每页大小必须大于0')
        if v > 100:
            raise ValueError('每页大小不能超过100')
        return v


def get_pagination_params(
    page: int = Query(1, ge=1, description="页码"),  # 页码查询参数
    page_size: int = Query(20, ge=1, le=100, description="每页大小")  # 每页大小查询参数
) -> PaginationParams:
    """
    获取分页参数 - FastAPI依赖函数
    
    Args:
        page: 页码
        page_size: 每页大小
        
    Returns:
        分页参数对象
    """
    return PaginationParams(page=page, page_size=page_size)


class PaginatedResult(BaseModel):
    """
    分页结果模型 - 用于返回分页查询结果
    """
    model_config = ConfigDict(from_attributes=True)
    
    items: list  # 项目列表
    total: int  # 总数量
    page: int  # 当前页码
    page_size: int  # 每页大小
    total_pages: int  # 总页数
    has_next: bool  # 是否有下一页
    has_previous: bool  # 是否有上一页

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        """
        创建分页结果
        
        Args:
            items: 项目列表
            total: 总数量
            page: 当前页码
            page_size: 每页大小
            
        Returns:
            分页结果对象
        """
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        # 判断是否有下一页
        has_next = page < total_pages
        # 判断是否有上一页
        has_previous = page > 1
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )


def paginate_query(query, pagination: PaginationParams):
    """
    分页查询辅助函数 - 用于SQLAlchemy查询
    
    Args:
        query: SQLAlchemy查询对象
        pagination: 分页参数
        
    Returns:
        分页后的查询对象
    """
    # 计算偏移量
    offset = (pagination.page - 1) * pagination.page_size
    # 应用分页
    paginated_query = query.offset(offset).limit(pagination.page_size)
    
    return paginated_query


def calculate_pagination_info(total_count: int, page: int, page_size: int) -> dict:
    """
    计算分页信息
    
    Args:
        total_count: 总数量
        page: 当前页码
        page_size: 每页大小
        
    Returns:
        分页信息字典
    """
    # 计算总页数
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
    # 判断是否有下一页
    has_next = page < total_pages
    # 判断是否有上一页
    has_previous = page > 1
    # 计算当前页的起始索引
    start_index = (page - 1) * page_size + 1
    # 计算当前页的结束索引
    end_index = min(start_index + page_size - 1, total_count)
    
    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_previous": has_previous,
        "start_index": start_index,
        "end_index": end_index
    }


class CursorPaginationParams(BaseModel):
    """
    游标分页参数模型 - 用于基于游标的分页
    """
    model_config = ConfigDict(from_attributes=True)
    
    cursor: Optional[str] = Field(None, description="游标")  # 游标
    limit: int = Field(20, ge=1, le=100, description="每页大小，1-100")  # 每页大小


class CursorPaginatedResult(BaseModel):
    """
    游标分页结果模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    items: list  # 项目列表
    next_cursor: Optional[str]  # 下一个游标
    has_next: bool  # 是否有下一页
    total_count: Optional[int]  # 总数量（可选）

    @classmethod
    def create(cls, items: list, next_cursor: Optional[str] = None, total_count: Optional[int] = None):
        """
        创建游标分页结果
        
        Args:
            items: 项目列表
            next_cursor: 下一个游标
            total_count: 总数量
            
        Returns:
            游标分页结果对象
        """
        # 判断是否有下一页
        has_next = next_cursor is not None
        
        return cls(
            items=items,
            next_cursor=next_cursor,
            has_next=has_next,
            total_count=total_count
        )


def validate_pagination_params(page: int, page_size: int) -> tuple:
    """
    验证分页参数
    
    Args:
        page: 页码
        page_size: 每页大小
        
    Returns:
        验证后的分页参数元组 (页码, 每页大小)
    """
    # 确保页码有效
    if page < 1:
        page = 1
    
    # 确保每页大小有效
    if page_size < 1:
        page_size = 1
    elif page_size > 100:
        page_size = 100
    
    return page, page_size


def get_offset_limit(page: int, page_size: int) -> tuple:
    """
    计算数据库查询的偏移量和限制
    
    Args:
        page: 页码
        page_size: 每页大小
        
    Returns:
        (偏移量, 限制) 元组
    """
    # 验证分页参数
    page, page_size = validate_pagination_params(page, page_size)
    # 计算偏移量
    offset = (page - 1) * page_size
    
    return offset, page_size


    内容模块-分页工具

from typing import List, TypeVar, Generic, Optional
from math import ceil
from pydantic import BaseModel
from sqlalchemy.orm import Query
from sqlalchemy import func

T = TypeVar('T')


class Page(BaseModel, Generic[T]):
    """分页结果模型"""
    items: List[T]
    page: int
    page_size: int
    total: int
    pages: int
    
    class Config:
        arbitrary_types_allowed = True


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20


class Pagination:
    """分页工具类"""
    
    @staticmethod
    async def paginate(
        query: Query,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ) -> Page:
        """执行分页查询"""
        # 限制每页最大数量
        if page_size > max_page_size:
            page_size = max_page_size
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取总数
        total = query.count()
        
        # 计算总页数
        pages = ceil(total / page_size) if total > 0 else 1
        
        # 执行分页查询
        items = query.offset(offset).limit(page_size).all()
        
        return Page(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=pages
        )
    
    @staticmethod
    def validate_pagination_params(
        page: int,
        page_size: int,
        max_page_size: int = 100
    ) -> tuple[int, int]:
        """验证分页参数"""
        if page < 1:
            page = 1
        
        if page_size < 1:
            page_size = 20
        elif page_size > max_page_size:
            page_size = max_page_size
        
        return page, page_size


class CursorPagination:
    """游标分页"""
    
    def __init__(self, cursor_field: str = "id", page_size: int = 20):
        self.cursor_field = cursor_field
        self.page_size = page_size
    
    async def paginate(
        self,
        query: Query,
        cursor: Optional[str] = None,
        direction: str = "next"
    ) -> dict:
        """执行游标分页查询"""
        # 构建基础查询
        if cursor:
            if direction == "next":
                query = query.filter(getattr(query.column_descriptions[0]['type'], self.cursor_field) > cursor)
            else:  # previous
                query = query.filter(getattr(query.column_descriptions[0]['type'], self.cursor_field) < cursor)
        
        # 获取结果
        items = query.limit(self.page_size + 1).all()
        
        # 检查是否有更多数据
        has_next = len(items) > self.page_size
        has_previous = cursor is not None
        
        if has_next:
            items = items[:-1]
            next_cursor = getattr(items[-1], self.cursor_field) if items else None
        else:
            next_cursor = None
        
        if has_previous and items:
            previous_cursor = getattr(items[0], self.cursor_field)
        else:
            previous_cursor = None
        
        return {
            "items": items,
            "pagination": {
                "next_cursor": next_cursor,
                "previous_cursor": previous_cursor,
                "has_next": has_next,
                "has_previous": has_previous,
                "page_size": self.page_size
            }
        }