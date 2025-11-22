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