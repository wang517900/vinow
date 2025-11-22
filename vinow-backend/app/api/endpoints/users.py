内容系统
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Query
from pydantic import BaseModel

from app.models.user import UserCreate, UserUpdate, UserResponse, UserLogin, Token, PasswordChange
from app.services.user_service import UserService
from app.core.security import SecurityManager, get_current_user, get_current_active_user
from app.api.v1.dependencies import GetUserService, GetCurrentUser, GetCurrentActiveUser, RateLimitPerMinute
from app.utils.logger import logger

# 创建用户路由
router = APIRouter(prefix="/users", tags=["users"])

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(GetUserService)
):
    """用户注册
    
    注册新用户账户，需要提供有效的邮箱和密码。
    """
    try:
        # 创建用户
        user = await user_service.create_user(user_data)
        
        # 发送欢迎邮件（后台任务）
        background_tasks.add_task(send_welcome_email, user["email"], user["username"])
        
        # 返回用户信息（不包含密码哈希）
        user_response = UserResponse(**user)
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册失败: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    user_service: UserService = Depends(GetUserService),
    rate_limit = Depends(RateLimitPerMinute)
):
    """用户登录
    
    使用邮箱和密码登录系统，成功后返回访问令牌。
    """
    try:
        # 验证用户凭证
        user = await user_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        
        # 创建访问令牌
        access_token = SecurityManager.create_access_token(
            data={"sub": str(user["id"])}
        )
        
        # 创建响应
        token_response = Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30分钟
            user=UserResponse(**user)
        )
        
        logger.info(f"用户登录成功: {user['email']}")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败 {login_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

@router.post("/logout")
async def logout_user(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """用户登出
    
    登出当前用户会话，客户端应删除本地存储的访问令牌。
    """
    try:
        # 在实际应用中，这里应该将令牌加入黑名单
        # 由于JWT是无状态的，客户端应该删除存储的令牌
        
        logger.info(f"用户登出: {current_user['email']}")
        return {"message": "登出成功"}
        
    except Exception as e:
        logger.error(f"用户登出失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """获取当前用户资料
    
    获取当前登录用户的完整个人资料信息。
    """
    try:
        user_id = str(current_user["id"])
        profile = await user_service.get_user_profile(user_id)
        return profile
        
    except Exception as e:
        logger.error(f"获取用户资料失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户资料失败"
        )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """更新当前用户信息
    
    更新当前登录用户的个人信息。
    """
    try:
        user_id = str(current_user["id"])
        updated_user = await user_service.update_user(user_id, update_data)
        
        user_response = UserResponse(**updated_user)
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """修改密码
    
    修改当前用户的登录密码，需要提供当前密码进行验证。
    """
    try:
        user_id = str(current_user["id"])
        
        # 使用UserService的change_password方法
        success = await user_service.change_password(
            user_id, 
            password_data.current_password, 
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码修改失败"
            )
        
        logger.info(f"用户修改密码成功: {current_user['email']}")
        return {"message": "密码修改成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )

@router.get("/{user_id}", response_model=Dict[str, Any])
async def get_user_profile(
    user_id: str,
    user_service: UserService = Depends(GetUserService)
):
    """获取指定用户资料（公开信息）
    
    获取指定用户的公开资料信息，不包含敏感数据。
    """
    try:
        profile = await user_service.get_user_profile(user_id)
        
        # 移除敏感信息
        if "password_hash" in profile:
            del profile["password_hash"]
        if "email" in profile:
            del profile["email"]  # 或者只对好友显示
        
        return profile
        
    except Exception as e:
        logger.error(f"获取用户公开资料失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

@router.get("", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_service: UserService = Depends(GetUserService)
):
    """获取用户列表
    
    获取系统中的用户列表，支持分页。
    """
    try:
        # 这里应该调用UserService的获取用户列表方法
        # 由于当前UserService没有实现该方法，我们模拟实现
        
        # 注意：在真实应用中，这应该只返回公开信息
        users = []  # 模拟用户列表
        total = 0   # 模拟总数
        
        response = UserListResponse(
            items=[UserResponse(**user) for user in users],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if total > 0 else 0
        )
        
        return response
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )

@router.delete("/me")
async def delete_current_user(
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """删除当前用户账户
    
    删除当前用户的账户，这是一个不可逆的操作。
    """
    try:
        user_id = str(current_user["id"])
        
        # 删除用户
        await user_service.delete_user(user_id)
        
        logger.info(f"用户账户删除成功: {current_user['email']}")
        return {"message": "账户删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户账户失败 {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除账户失败"
        )

@router.get("/{user_id}/statistics")
async def get_user_statistics(
    user_id: str,
    user_service: UserService = Depends(GetUserService)
):
    """获取用户统计信息
    
    获取指定用户的统计信息，如作品数量、获赞数等。
    """
    try:
        # 获取用户资料，其中包含统计信息
        profile = await user_service.get_user_profile(user_id)
        
        # 提取统计信息
        statistics = profile.get("profile", {}).get("statistics", {})
        creator_growth = profile.get("creator_growth", {})
        
        return {
            "user_id": user_id,
            "basic_statistics": statistics,
            "creator_growth": creator_growth
        }
        
    except Exception as e:
        logger.error(f"获取用户统计信息失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

@router.post("/{user_id}/follow")
async def follow_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """关注用户
    
    关注指定用户。
    """
    try:
        follower_id = str(current_user["id"])
        
        # 在实际应用中，这里应该调用关注服务或更新用户关系表
        # 由于当前UserService没有实现该功能，我们模拟实现
        
        logger.info(f"用户 {follower_id} 关注了用户 {user_id}")
        return {"message": "关注成功"}
        
    except Exception as e:
        logger.error(f"关注用户失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="关注失败"
        )

@router.post("/{user_id}/unfollow")
async def unfollow_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser),
    user_service: UserService = Depends(GetUserService)
):
    """取消关注用户
    
    取消对指定用户的关注。
    """
    try:
        follower_id = str(current_user["id"])
        
        # 在实际应用中，这里应该调用关注服务或更新用户关系表
        # 由于当前UserService没有实现该功能，我们模拟实现
        
        logger.info(f"用户 {follower_id} 取消关注了用户 {user_id}")
        return {"message": "取消关注成功"}
        
    except Exception as e:
        logger.error(f"取消关注用户失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消关注失败"
        )

@router.get("/me/followers")
async def get_my_followers(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """获取我的关注者列表
    
    获取当前用户的关注者（粉丝）列表。
    """
    try:
        user_id = str(current_user["id"])
        
        # 在实际应用中，这里应该查询关注关系表
        # 由于当前UserService没有实现该功能，我们模拟实现
        
        followers = []  # 模拟关注者列表
        total = 0       # 模拟总数
        
        return {
            "followers": followers,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"获取关注者列表失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取关注者列表失败"
        )

@router.get("/me/following")
async def get_my_following(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """获取我关注的用户列表
    
    获取当前用户关注的用户列表。
    """
    try:
        user_id = str(current_user["id"])
        
        # 在实际应用中，这里应该查询关注关系表
        # 由于当前UserService没有实现该功能，我们模拟实现
        
        following = []  # 模拟关注列表
        total = 0       # 模拟总数
        
        return {
            "following": following,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"获取关注列表失败 {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取关注列表失败"
        )

# 后台任务函数
async def send_welcome_email(email: str, username: str):
    """发送欢迎邮件（模拟实现）
    
    用户注册成功后发送欢迎邮件。
    
    Args:
        email: 用户邮箱
        username: 用户名
    """
    try:
        # 在实际应用中，这里应该调用邮件服务
        logger.info(f"发送欢迎邮件给: {email}, 用户名: {username}")
        # 模拟邮件发送延迟
        import asyncio
        await asyncio.sleep(1)
        logger.info(f"欢迎邮件发送成功: {email}")
    except Exception as e:
        logger.error(f"发送欢迎邮件失败 {email}: {str(e)}")