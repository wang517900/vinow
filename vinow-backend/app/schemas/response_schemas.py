内容系统
"""
响应模式定义模块

本模块定义了API接口的标准化响应格式，包括：
1. 标准响应格式（StandardResponse）
2. 分页响应格式（PaginatedResponse）
3. 错误响应格式（ErrorResponse）
4. 健康检查响应格式（HealthCheckResponse）
5. 文件上传响应格式（UploadResponse）
6. 批量操作响应格式（BatchOperationResponse）
7. 统计信息响应格式（StatisticsResponse）

以及相应的响应创建工具函数。
"""

from typing import TypeVar, Generic, Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# 定义泛型类型变量
T = TypeVar('T')

__all__ = [
    'StandardResponse',
    'PaginatedResponse',
    'ErrorResponse',
    'HealthCheckResponse',
    'UploadResponse',
    'BatchOperationResponse',
    'StatisticsResponse',
    'create_success_response',
    'create_error_response',
    'create_paginated_response'
]


class StandardResponse(BaseModel, Generic[T]):
    """
    标准API响应模型 - 所有API响应的统一格式
    
    Generic[T]: 泛型类型，T为数据字段的类型
    """
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    success: bool = Field(..., description="请求是否成功")  # 成功状态
    message: str = Field(..., description="响应消息")  # 响应消息
    data: Optional[T] = Field(None, description="响应数据")  # 响应数据（可选）
    error: Optional[Dict[str, Any]] = Field(None, description="错误信息")  # 错误信息（可选）
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")  # 时间戳


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页API响应模型 - 用于分页列表数据
    
    Generic[T]: 泛型类型，T为列表项的类型
    """
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    success: bool = Field(..., description="请求是否成功")  # 成功状态
    message: str = Field(..., description="响应消息")  # 响应消息
    data: List[T] = Field(..., description="数据列表")  # 数据列表
    pagination: Dict[str, Any] = Field(..., description="分页信息")  # 分页信息
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")  # 时间戳


class ErrorResponse(BaseModel):
    """
    错误响应模型 - 用于错误响应的统一格式
    """
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    success: bool = Field(False, description="请求是否成功")  # 成功状态（固定为False）
    message: str = Field(..., description="错误消息")  # 错误消息
    error: Dict[str, Any] = Field(..., description="错误详情")  # 错误详情
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")  # 时间戳


def create_success_response(
    data: Any = None, 
    message: str = "操作成功", 
    status_code: int = 200
) -> StandardResponse:
    """
    创建成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        status_code: HTTP状态码
        
    Returns:
        成功响应模型实例
    """
    return StandardResponse(
        success=True,
        message=message,
        data=data,
        timestamp=datetime.now()
    )


def create_error_response(
    message: str = "操作失败",
    error_code: str = "UNKNOWN_ERROR",
    error_details: Any = None,
    status_code: int = 400
) -> ErrorResponse:
    """
    创建错误响应
    
    Args:
        message: 错误消息
        error_code: 错误代码
        error_details: 错误详情
        status_code: HTTP状态码
        
    Returns:
        错误响应模型实例
    """
    return ErrorResponse(
        success=False,
        message=message,
        error={
            "code": error_code,
            "details": error_details
        },
        timestamp=datetime.now()
    )


def create_paginated_response(
    data: List[Any],
    total_count: int,
    page: int,
    page_size: int,
    message: str = "获取列表成功"
) -> PaginatedResponse:
    """
    创建分页响应
    
    Args:
        data: 数据列表
        total_count: 总记录数
        page: 当前页码
        page_size: 每页大小
        message: 成功消息
        
    Returns:
        分页响应模型实例
    """
    # 计算总页数
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
    # 判断是否有下一页
    has_next = page < total_pages
    # 判断是否有上一页
    has_previous = page > 1
    
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination={
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous
        },
        timestamp=datetime.now()
    )


class HealthCheckResponse(BaseModel):
    """
    健康检查响应模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(..., description="健康状态")  # 健康状态
    timestamp: float = Field(..., description="检查时间戳")  # 时间戳
    version: str = Field(..., description="应用版本")  # 应用版本
    environment: str = Field(..., description="运行环境")  # 运行环境
    database: Dict[str, Any] = Field(..., description="数据库状态")  # 数据库状态
    cache: Dict[str, Any] = Field(..., description="缓存状态")  # 缓存状态


class UploadResponse(BaseModel):
    """
    文件上传响应模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    file_url: str = Field(..., description="文件URL")  # 文件URL
    file_name: str = Field(..., description="文件名")  # 文件名
    file_size: int = Field(..., description="文件大小")  # 文件大小
    file_type: str = Field(..., description="文件类型")  # 文件类型
    upload_id: str = Field(..., description="上传ID")  # 上传ID


class BatchOperationResponse(BaseModel):
    """
    批量操作响应模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    success_count: int = Field(..., description="成功数量")  # 成功数量
    failure_count: int = Field(..., description="失败数量")  # 失败数量
    total_count: int = Field(..., description="总数量")  # 总数量
    failures: List[Dict[str, Any]] = Field(default_factory=list, description="失败详情")  # 失败详情


class StatisticsResponse(BaseModel):
    """
    统计信息响应模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    total_count: int = Field(..., description="总数")  # 总数
    today_count: int = Field(..., description="今日数量")  # 今日数量
    week_count: int = Field(..., description="本周数量")  # 本周数量
    month_count: int = Field(..., description="本月数量")  # 本月数量
    growth_rate: float = Field(..., description="增长率")  # 增长率
    statistics: Dict[str, Any] = Field(default_factory=dict, description="详细统计")  # 详细统计

    内容板块-响应模型

from pydantic import BaseModel, Generic, TypeVar
from typing import Optional, List, Any, Generic
from datetime import datetime

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """标准API响应模型"""
    success: bool
    message: str
    data: Optional[T] = None
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class PaginatedResponse(BaseModel, Generic[T]):
    """分页API响应模型"""
    success: bool
    message: str
    data: List[T]
    pagination: 'PaginationParams'
    timestamp: datetime = datetime.utcnow()


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    version: str