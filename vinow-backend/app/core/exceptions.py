from fastapi import HTTPException 
 
class AppException(HTTPException): 
    def __init__(self, message: str, status_code: int = 400): 
        super().__init__(status_code=status_code, detail=message) 
 
class ValidationError(AppException): 
    def __init__(self, message: str = "数据验证失败"): 
        super().__init__(message, 400) 
 
class AuthenticationError(AppException): 
    def __init__(self, message: str = "认证失败"): 
        super().__init__(message, 401) 


商家内容3营销部分
# app/core/exceptions.py
from fastapi import HTTPException, status
from typing import Any, Dict

class BusinessException(HTTPException):
    """业务异常基类"""
    
    def __init__(self, detail: str, code: str = None, data: Any = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
        self.code = code
        self.data = data

class ContentNotFoundException(BusinessException):
    """内容不存在异常"""
    
    def __init__(self, content_id: str):
        super().__init__(
            detail=f"内容不存在: {content_id}",
            code="CONTENT_NOT_FOUND"
        )

class CollaborationNotFoundException(BusinessException):
    """合作任务不存在异常"""
    
    def __init__(self, collaboration_id: str):
        super().__init__(
            detail=f"合作任务不存在: {collaboration_id}",
            code="COLLABORATION_NOT_FOUND"
        )

class PermissionDeniedException(BusinessException):
    """权限拒绝异常"""
    
    def __init__(self, resource: str):
        super().__init__(
            detail=f"没有权限访问资源: {resource}",
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ValidationException(BusinessException):
    """数据验证异常"""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            detail=f"字段验证失败: {field} - {message}",
            code="VALIDATION_ERROR"
        )

class RateLimitException(BusinessException):
    """限流异常"""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            detail=f"请求过于频繁，限制 {limit} 次/{window}秒",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

        商家板块5数据分析
        from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class AnalyticsException(HTTPException):
    """基础异常类"""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class DatabaseException(AnalyticsException):
    """数据库异常"""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class ValidationException(AnalyticsException):
    """验证异常"""
    
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class AuthenticationException(AnalyticsException):
    """认证异常"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationException(AnalyticsException):
    """授权异常"""
    
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class NotFoundException(AnalyticsException):
    """资源未找到异常"""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class ExternalServiceException(AnalyticsException):
    """外部服务异常"""
    
    def __init__(self, detail: str = "External service error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

        商家板块6财务中心
        from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """认证异常"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )


class FinanceDataException(HTTPException):
    """财务数据异常"""
    def __init__(self, detail: str = "财务数据操作失败"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class SettlementException(HTTPException):
    """结算异常"""
    def __init__(self, detail: str = "结算操作失败"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ReconciliationException(HTTPException):
    """对账异常"""
    def __init__(self, detail: str = "对账操作失败"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class ReportException(HTTPException):
    """报表异常"""
    def __init__(self, detail: str = "报表生成失败"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


    内容系统
    from fastapi import HTTPException, status
from typing import Any, Dict

class VideoContentException(HTTPException):
    """自定义异常基类"""
    
    def __init__(self, status_code: int, detail: Any = None, headers: Dict[str, str] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class ContentNotFoundException(VideoContentException):
    """内容未找到异常"""
    
    def __init__(self, content_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content with ID {content_id} not found"
        )

class UserNotFoundException(VideoContentException):
    """用户未找到异常"""
    
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

class PermissionDeniedException(VideoContentException):
    """权限拒绝异常"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

class FileUploadException(VideoContentException):
    """文件上传异常"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class ContentModerationException(VideoContentException):
    """内容审核异常"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

class RateLimitException(VideoContentException):
    """速率限制异常"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )

class DatabaseException(VideoContentException):
    """数据库异常"""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class ExternalServiceException(VideoContentException):
    """外部服务异常"""
    
    def __init__(self, service: str, detail: str = "Service unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service} service error: {detail}"
        )