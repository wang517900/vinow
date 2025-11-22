内容模块-自定义异常文件
"""
异常处理工具模块

本模块定义了内容管理系统中使用的自定义异常类，包括：
1. 内容系统基础异常（ContentSystemException）
2. 内容相关异常（内容不存在、权限拒绝等）
3. 评价相关异常（评价已存在等）
4. 文件上传相关异常（文件类型、大小等）
5. 存储服务异常
6. 数据库连接异常
7. 缓存服务异常
8. 数据验证异常
9. 速率限制异常

所有异常都继承自FastAPI的HTTPException，确保与FastAPI框架良好集成。
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

__all__ = [
    'ContentSystemException',
    'ContentNotFoundException',
    'ContentPermissionDeniedException',
    'ReviewAlreadyExistsException',
    'FileUploadException',
    'FileTypeNotAllowedException',
    'FileSizeExceededException',
    'StorageServiceException',
    'DatabaseConnectionException',
    'CacheServiceException',
    'ValidationException',
    'RateLimitException'
]


class ContentSystemException(HTTPException):
    """
    内容系统基础异常类 - 所有自定义异常的基类
    """
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "内容系统异常",
        error_code: str = "CONTENT_SYSTEM_ERROR",
        error_data: Optional[Dict[str, Any]] = None
    ):
        """
        初始化内容系统异常
        
        Args:
            status_code: HTTP状态码
            detail: 错误详情
            error_code: 错误代码
            error_data: 错误数据
        """
        # 调用父类初始化
        super().__init__(status_code=status_code, detail=detail)
        # 设置错误代码
        self.error_code = error_code
        # 设置错误数据
        self.error_data = error_data or {}
        # 记录异常日志
        logger.error(f"内容系统异常: {error_code} - {detail}", extra={
            "error_code": error_code,
            "error_data": error_data,
            "status_code": status_code
        })


class ContentNotFoundException(ContentSystemException):
    """
    内容不存在异常
    """
    
    def __init__(self, content_id: str, detail: Optional[str] = None):
        """
        初始化内容不存在异常
        
        Args:
            content_id: 内容ID
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"内容不存在: {content_id}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="CONTENT_NOT_FOUND",
            error_data={"content_id": content_id}
        )


class ContentPermissionDeniedException(ContentSystemException):
    """
    内容权限拒绝异常
    """
    
    def __init__(self, content_id: str, user_id: str, detail: Optional[str] = None):
        """
        初始化内容权限拒绝异常
        
        Args:
            content_id: 内容ID
            user_id: 用户ID
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"用户 {user_id} 无权限操作内容 {content_id}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="CONTENT_PERMISSION_DENIED",
            error_data={
                "content_id": content_id,
                "user_id": user_id
            }
        )


class ReviewAlreadyExistsException(ContentSystemException):
    """
    评价已存在异常
    """
    
    def __init__(self, user_id: str, target_entity_id: str, detail: Optional[str] = None):
        """
        初始化评价已存在异常
        
        Args:
            user_id: 用户ID
            target_entity_id: 目标实体ID
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"用户 {user_id} 已对实体 {target_entity_id} 进行过评价"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="REVIEW_ALREADY_EXISTS",
            error_data={
                "user_id": user_id,
                "target_entity_id": target_entity_id
            }
        )


class FileUploadException(ContentSystemException):
    """
    文件上传异常
    """
    
    def __init__(self, filename: str, detail: Optional[str] = None):
        """
        初始化文件上传异常
        
        Args:
            filename: 文件名
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"文件上传失败: {filename}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_UPLOAD_ERROR",
            error_data={"filename": filename}
        )


class FileTypeNotAllowedException(FileUploadException):
    """
    文件类型不允许异常
    """
    
    def __init__(self, filename: str, file_type: str, allowed_types: List[str]):
        """
        初始化文件类型不允许异常
        
        Args:
            filename: 文件名
            file_type: 文件类型
            allowed_types: 允许的文件类型列表
        """
        # 构建错误详情
        detail = f"文件类型不允许: {file_type}，支持的类型: {', '.join(allowed_types)}"
        
        # 调用父类初始化
        super(FileUploadException, self).__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_TYPE_NOT_ALLOWED",
            error_data={
                "filename": filename,
                "file_type": file_type,
                "allowed_types": allowed_types
            }
        )


class FileSizeExceededException(FileUploadException):
    """
    文件大小超出限制异常
    """
    
    def __init__(self, filename: str, file_size: int, max_size: int):
        """
        初始化文件大小超出限制异常
        
        Args:
            filename: 文件名
            file_size: 文件大小
            max_size: 最大文件大小
        """
        # 构建错误详情
        detail = f"文件大小超出限制: {file_size} > {max_size}"
        
        # 调用父类初始化
        super(FileUploadException, self).__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_SIZE_EXCEEDED",
            error_data={
                "filename": filename,
                "file_size": file_size,
                "max_size": max_size
            }
        )


class StorageServiceException(ContentSystemException):
    """
    存储服务异常
    """
    
    def __init__(self, operation: str, detail: Optional[str] = None):
        """
        初始化存储服务异常
        
        Args:
            operation: 操作名称
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"存储服务操作失败: {operation}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="STORAGE_SERVICE_ERROR",
            error_data={"operation": operation}
        )


class DatabaseConnectionException(ContentSystemException):
    """
    数据库连接异常
    """
    
    def __init__(self, detail: Optional[str] = None):
        """
        初始化数据库连接异常
        
        Args:
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = "数据库连接失败"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="DATABASE_CONNECTION_ERROR"
        )


class CacheServiceException(ContentSystemException):
    """
    缓存服务异常
    """
    
    def __init__(self, operation: str, detail: Optional[str] = None):
        """
        初始化缓存服务异常
        
        Args:
            operation: 操作名称
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"缓存服务操作失败: {operation}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="CACHE_SERVICE_ERROR",
            error_data={"operation": operation}
        )


class ValidationException(ContentSystemException):
    """
    数据验证异常
    """
    
    def __init__(self, field: str, value: Any, rule: str, detail: Optional[str] = None):
        """
        初始化数据验证异常
        
        Args:
            field: 字段名
            value: 字段值
            rule: 验证规则
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"字段 '{field}' 验证失败: {rule}"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR",
            error_data={
                "field": field,
                "value": value,
                "rule": rule
            }
        )


class RateLimitException(ContentSystemException):
    """
    速率限制异常
    """
    
    def __init__(self, operation: str, limit: int, window: int, detail: Optional[str] = None):
        """
        初始化速率限制异常
        
        Args:
            operation: 操作名称
            limit: 限制次数
            window: 时间窗口（秒）
            detail: 错误详情
        """
        # 设置默认错误详情
        if detail is None:
            detail = f"操作 '{operation}' 超过速率限制: {limit}次/{window}秒"
        
        # 调用父类初始化
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            error_data={
                "operation": operation,
                "limit": limit,
                "window": window
            }
        )

        内容模块-自定义异常
    
    from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class BaseAPIException(HTTPException):
    """基础API异常"""
    
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


class NotFoundException(BaseAPIException):
    """资源未找到异常"""
    
    def __init__(self, detail: str = "资源未找到", error_code: str = "NOT_FOUND"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code
        )


class ValidationException(BaseAPIException):
    """数据验证异常"""
    
    def __init__(self, detail: str = "数据验证失败", error_code: str = "VALIDATION_ERROR"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code
        )


class AuthenticationException(BaseAPIException):
    """认证异常"""
    
    def __init__(self, detail: str = "认证失败", error_code: str = "AUTHENTICATION_ERROR"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code
        )


class AuthorizationException(BaseAPIException):
    """授权异常"""
    
    def __init__(self, detail: str = "权限不足", error_code: str = "AUTHORIZATION_ERROR"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code
        )


class BusinessException(BaseAPIException):
    """业务逻辑异常"""
    
    def __init__(self, detail: str = "业务逻辑错误", error_code: str = "BUSINESS_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )


class RateLimitException(BaseAPIException):
    """限流异常"""
    
    def __init__(self, detail: str = "请求过于频繁", error_code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code=error_code
        )


class DatabaseException(BaseAPIException):
    """数据库异常"""
    
    def __init__(self, detail: str = "数据库操作失败", error_code: str = "DATABASE_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code
        )


class ExternalServiceException(BaseAPIException):
    """外部服务异常"""
    
    def __init__(self, detail: str = "外部服务调用失败", error_code: str = "EXTERNAL_SERVICE_ERROR"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code
        )


class FileUploadException(BaseAPIException):
    """文件上传异常"""
    
    def __init__(self, detail: str = "文件上传失败", error_code: str = "FILE_UPLOAD_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )


class VideoProcessingException(BaseAPIException):
    """视频处理异常"""
    
    def __init__(self, detail: str = "视频处理失败", error_code: str = "VIDEO_PROCESSING_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code
        )