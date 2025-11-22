商家板块5数据分析
from fastapi import Depends, HTTPException, status, Header
from typing import Optional
from app.core.security import verify_token, TokenData, validate_api_key
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging import logger
from app.services.supabase_client import SupabaseClient
from app.services.analytics import AnalyticsService

async def get_supabase_client() -> SupabaseClient:
    """获取 Supabase 客户端依赖"""
    return SupabaseClient()

async def get_analytics_service(
    supabase: SupabaseClient = Depends(get_supabase_client)
) -> AnalyticsService:
    """获取分析服务依赖"""
    return AnalyticsService(supabase)

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> bool:
    """验证 API Key"""
    if not x_api_key or not validate_api_key(x_api_key):
        logger.warning("API key validation failed")
        raise AuthenticationException("Invalid API Key")
    return True

async def verify_jwt_token(
    authorization: Optional[str] = Header(None)
) -> TokenData:
    """验证 JWT Token"""
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("JWT token missing or invalid format")
        raise AuthenticationException("Invalid authentication credentials")
    
    token = authorization.replace("Bearer ", "")
    token_data = verify_token(token)
    
    if token_data is None:
        logger.warning("JWT token verification failed")
        raise AuthenticationException("Invalid token")
    
    return token_data

# 依赖组合
async def get_current_user(
    token_data: TokenData = Depends(verify_jwt_token)
) -> TokenData:
    """获取当前用户"""
    return token_data

async def get_authenticated_user(
    api_key_valid: bool = Depends(verify_api_key),
    token_data: TokenData = Depends(verify_jwt_token)
) -> TokenData:
    """获取认证用户 (API Key + JWT)"""
    return token_data
    

商户系统6财务中心
from fastapi import Depends, HTTPException, status, Query
from typing import Optional

from app.core.security import get_current_merchant, validate_merchant_access
from app.schemas.finance import (
    IncomeFlowParams, SettlementHistoryParams, ReportParams,
    PaginationParams
)
from app.utils.date_utils import DateUtils


async def get_merchant_id(
    current_merchant: dict = Depends(get_current_merchant)
) -> str:
    """获取商户ID"""
    return current_merchant["merchant_id"]


async def get_income_flow_params(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    payment_method: Optional[str] = Query(None, description="支付方式"),
    order_status: Optional[str] = Query(None, description="订单状态"),
    min_amount: Optional[float] = Query(None, description="最小金额"),
    max_amount: Optional[float] = Query(None, description="最大金额"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> IncomeFlowParams:
    """获取收入流水参数"""
    return IncomeFlowParams(
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method,
        order_status=order_status,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size
    )


async def get_settlement_history_params(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="结算状态"),
    min_amount: Optional[float] = Query(None, description="最小金额"),
    max_amount: Optional[float] = Query(None, description="最大金额"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> SettlementHistoryParams:
    """获取结算历史参数"""
    return SettlementHistoryParams(
        start_date=start_date,
        end_date=end_date,
        status=status,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size
    )


async def get_report_params(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    compare_period: bool = Query(False, description="是否对比同期"),
    include_details: bool = Query(False, description="是否包含明细")
) -> ReportParams:
    """获取报表参数"""
    return ReportParams(
        start_date=start_date,
        end_date=end_date,
        compare_period=compare_period,
        include_details=include_details
    )


async def get_pagination_params(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> PaginationParams:
    """获取分页参数"""
    return PaginationParams(page=page, page_size=page_size)


async def verify_merchant_access(
    merchant_id: str,
    current_merchant: dict = Depends(get_current_merchant)
):
    """验证商户访问权限"""
    await validate_merchant_access(merchant_id, current_merchant)
    return merchant_id



    内容系统

import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from app.core.security import get_current_user, get_current_active_user, require_role, rate_limit
from app.services.user_service import UserService
from app.services.content_service import ContentService
from app.services.recommendation_service import RecommendationService
from app.services.moderation_service import ModerationService
from app.services.file_service import FileService
from app.utils.logger import logger

# 创建服务实例
user_service = UserService()
content_service = ContentService()
recommendation_service = RecommendationService()
moderation_service = ModerationService()
file_service = FileService()

async def get_user_service() -> UserService:
    """获取用户服务依赖"""
    return user_service

async def get_content_service() -> ContentService:
    """获取内容服务依赖"""
    return content_service

async def get_recommendation_service() -> RecommendationService:
    """获取推荐服务依赖"""
    return recommendation_service

async def get_moderation_service() -> ModerationService:
    """获取审核服务依赖"""
    return moderation_service

async def get_file_service() -> FileService:
    """获取文件服务依赖"""
    return file_service

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """验证API密钥（用于服务间通信）"""
    if not x_api_key or x_api_key != "video_system_internal_key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return x_api_key

# 常用的依赖组合
GetCurrentUser = Depends(get_current_user)  # 获取当前用户
GetCurrentActiveUser = Depends(get_current_active_user)  # 获取当前活跃用户
GetUserService = Depends(get_user_service)  # 获取用户服务
GetContentService = Depends(get_content_service)  # 获取内容服务
GetRecommendationService = Depends(get_recommendation_service)  # 获取推荐服务
GetModerationService = Depends(get_moderation_service)  # 获取审核服务
GetFileService = Depends(get_file_service)  # 获取文件服务

# 角色权限依赖
RequireAdmin = Depends(require_role("admin"))  # 需要管理员权限
RequireModerator = Depends(require_role("moderator"))  # 需要审核员权限
RequireCreator = Depends(require_role("creator"))  # 需要创作者权限

def get_rate_limiter(requests: int = 60, window: int = 60):
    """获取速率限制器依赖"""
    def rate_limiter(user_id: str = Depends(get_current_user)):
        return rate_limit(f"user:{user_id}", requests, window)
    return rate_limiter

# 常用的速率限制
RateLimitPerMinute = Depends(get_rate_limiter(60, 60))  # 每分钟60次
RateLimitPerHour = Depends(get_rate_limiter(1000, 3600))  # 每小时1000次