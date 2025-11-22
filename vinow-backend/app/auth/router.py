"""
认证路由模块 - v1.3.0
修复字段标准化和用户重复创建问题
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import random
import time
import uuid
from datetime import datetime, timedelta

from app.common.database import supabase
from app.common.models import (
    SendOTPRequest, SendOTPResponse, VerifyOTPRequest, VerifyOTPResponse,
    RefreshTokenRequest, RefreshTokenResponse, LogoutRequest, LogoutResponse,
    UserProfile, SuccessResponse, ErrorResponse
)
from app.auth.dependencies import get_current_user,get_optional_user

router = APIRouter(prefix="/api/v1/auth/send-otp", tags=["authentication"])
security = HTTPBearer()

# 存储验证码和用户会话
verification_codes = {}
user_sessions = {}
local_user_store = {}  # 本地用户存储（数据库备份）
user_creation_lock = {}  # 用户创建锁，防止重复创建

def generate_verification_code() -> str:
    """生成6位数字验证码"""
    return str(random.randint(100000, 999999))

def generate_user_id() -> str:
    """生成用户ID"""
    return str(uuid.uuid4())

async def create_or_update_user_profile(user_data: dict) -> dict:
    """创建或更新用户资料 - 超级健壮版，解决重复创建问题"""
    try:
        phone = user_data.get("phone")
        if not phone:
            raise ValueError("手机号是必需的")

        print(f"🔍 开始查找用户: {phone}")

        # 1. 首先尝试Supabase连接查找用户
        try:
            existing_user = supabase.table("user_profiles").select("*").eq("phone", phone).execute()
            
            if existing_user.data and len(existing_user.data) > 0:
                user_record = existing_user.data[0]
                user_id = user_record.get("id")
                print(f"✅ 从Supabase找到现有用户: {user_id}")
                
                # 更新最后活跃时间
                supabase.table("user_profiles").update({
                    "updated_at": datetime.now().isoformat()
                }).eq("id", user_id).execute()
                
                return user_record
        except Exception as e:
            print(f"⚠️ Supabase查询失败: {e}")

        # 2. 如果Supabase失败，使用本地存储
        if phone in local_user_store:
            user_record = local_user_store[phone]
            print(f"✅ 从本地存储找到用户: {user_record.get('id')}")
            return user_record

        # 3. 创建新用户（使用锁防止并发重复创建）
        if phone not in user_creation_lock:
            user_creation_lock[phone] = True
            try:
                user_id = generate_user_id()
                print(f"🆕 创建新用户: {user_id}")

                profile_data = {
                    "id": user_id,
                    "username": f"user_{phone[-4:]}",
                    "phone": phone,
                    "email": None,
                    "full_name": None,
                    "avatar_url": None,
                    "date_of_birth": None,
                    "gender": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }

                # 保存到本地存储
                local_user_store[phone] = profile_data
                
                # 尝试保存到Supabase
                try:
                    result = supabase.table("user_profiles").insert(profile_data).execute()
                    print("📝 用户已保存到Supabase")
                except Exception as e:
                    print("⚠️ 保存到Supabase失败，仅保存在本地")
                    print(e)
                    import traceback
                    traceback.print_exc()

                return profile_data
            finally:
                # 释放锁
                if phone in user_creation_lock:
                    del user_creation_lock[phone]
        else:
            # 如果正在创建中，等待并重试查找
            print(f"⏳ 用户正在创建中，等待重试: {phone}")
            time.sleep(0.5)
            return await create_or_update_user_profile(user_data)

    except Exception as e:
        print(f"❌ 用户资料操作失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 紧急降级方案
        emergency_id = generate_user_id()
        emergency_profile = {
            "id": emergency_id,
            "username": f"emergency_user_{phone[-4:] if phone else 'unknown'}",
            "phone": phone,
            "email": None,
            "full_name": None,
            "avatar_url": None,
            "date_of_birth": None,
            "gender": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        if phone:
            local_user_store[phone] = emergency_profile
        return emergency_profile

def create_jwt_tokens(user_id: str) -> dict:
    """创建JWT令牌"""
    try:
        # 尝试导入JWT模块
        try:
            import jwt
            JWT_AVAILABLE = True
        except ImportError:
            print("❌ pyjwt 模块未安装，使用模拟令牌")
            JWT_AVAILABLE = False
        
        if not JWT_AVAILABLE:
            return {
                "access_token": f"mock_access_token_{user_id}_{int(time.time())}",
                "refresh_token": f"mock_refresh_token_{user_id}_{int(time.time())}",
                "expires_in": 86400,
                "token_type": "bearer"
            }
        
        secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
        # 创建访问令牌
        access_payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)
        
        # 创建刷新令牌
        refresh_payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=30),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 86400,
            "token_type": "bearer"
        }
        
    except Exception as e:
        print(f"❌ JWT令牌创建失败: {e}")
        return {
            "access_token": f"fallback_token_{user_id}_{int(time.time())}",
            "refresh_token": f"fallback_refresh_{user_id}_{int(time.time())}",
            "expires_in": 86400,
            "token_type": "bearer"
        }

@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest):
    """
    发送短信验证码 - 使用标准化响应模型
    """
    try:
        phone = request.phone
        
        # 验证手机号格式
        if not phone.startswith('+84') or len(phone) != 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号格式不正确，越南手机号应为+84开头，共12位"
            )
        
        # 生成验证码
        verification_code = generate_verification_code()
        
        # 存储验证码（带时间戳和尝试次数）
        verification_codes[phone] = {
            "code": verification_code,
            "created_at": time.time(),
            "attempts": 0
        }
        
        # 开发环境：在控制台显示验证码
        print("=" * 50)
        print(f"📱 模拟短信发送")
        print(f"📞 目标手机: {phone}")
        print(f"🔢 验证码: {verification_code}")
        print(f"⏰ 有效期: 10分钟")
        print("=" * 50)
        
        return SendOTPResponse(
            success=True,
            message="验证码已发送到您的手机",
            data={
                "code": verification_code,        # 标准字段
                "debug_code": verification_code,  # 开发环境兼容
                "session_id": str(uuid.uuid4()),
                "expires_in": 600
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"发送验证码失败: {str(e)}"
        )

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(request: VerifyOTPRequest):
    """
    验证短信验证码并登录 - 使用标准化响应模型和字段
    """
    try:
        phone = request.phone
        
        # 智能字段处理：优先使用标准字段 code，同时向后兼容
        verification_code = request.code
        
        print(f"🔐 验证手机: {phone}, 验证码: {verification_code}")
        
        if not verification_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供验证码"
            )
        
        # 检查验证码是否存在
        if phone not in verification_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先获取验证码"
            )
        
        stored_code_info = verification_codes[phone]
        stored_code = stored_code_info["code"]
        created_time = stored_code_info["created_at"]
        
        # 检查验证码是否过期（10分钟）
        if time.time() - created_time > 600:
            del verification_codes[phone]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码已过期，请重新获取"
            )
        
        # 检查尝试次数
        if stored_code_info["attempts"] >= 5:
            del verification_codes[phone]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="尝试次数过多，请重新获取验证码"
            )
        
        # 更新尝试次数
        verification_codes[phone]["attempts"] += 1
        
        # 验证验证码
        if verification_code != stored_code:
            remaining_attempts = 5 - verification_codes[phone]["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"验证码不正确，还剩{remaining_attempts}次尝试机会"
            )
        
        # 验证成功，清除验证码
        del verification_codes[phone]
        
        # 创建或更新用户资料（使用健壮版）
        user_profile = await create_or_update_user_profile({
            "phone": phone
        })
        
        user_id = user_profile["id"]
        
        # 生成JWT令牌
        tokens = create_jwt_tokens(user_id)
        
        # 存储用户会话
        user_sessions[user_id] = {
            "user_profile": user_profile,
            "last_active": time.time()
        }
        
        print(f"✅ 用户登录成功: {user_id}")
        
        return VerifyOTPResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
            user=user_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证失败: {str(e)}"
        )

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest = Body(...)):
    """
    刷新访问令牌 - 使用标准化响应模型
    """
    try:
        refresh_token_value = request.refresh_token
        
        if not refresh_token_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="刷新令牌是必需的"
            )
        
        # 简单的令牌刷新逻辑（生产环境需要更复杂的验证）
        user_id = None
        
        try:
            import jwt
            JWT_AVAILABLE = True
        except ImportError:
            JWT_AVAILABLE = False
        
        if JWT_AVAILABLE:
            try:
                secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
                
                # 验证刷新令牌
                payload = jwt.decode(refresh_token_value, secret_key, algorithms=["HS256"])
                
                if payload.get("type") != "refresh":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="无效的刷新令牌类型"
                    )
                
                user_id = payload.get("sub")
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="无效的令牌载荷"
                    )
                    
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="刷新令牌已过期"
                )
            except jwt.InvalidTokenError:
                # 如果JWT验证失败，尝试模拟令牌
                pass
        
        # 如果JWT验证失败或不可用，尝试模拟令牌验证
        if not user_id:
            if (refresh_token_value.startswith("mock_refresh_token_") or 
                refresh_token_value.startswith("fallback_refresh_")):
                # 从模拟令牌中提取user_id
                parts = refresh_token_value.split("_")
                if len(parts) >= 3:
                    user_id = parts[2]
            
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
        
        # 生成新的令牌
        tokens = create_jwt_tokens(user_id)
        
        # 获取用户资料
        user_profile = user_sessions.get(user_id, {}).get("user_profile")
        if not user_profile:
            # 从数据库获取用户资料
            user_profile = await create_or_update_user_profile({"id": user_id})
        
        print(f"✅ 令牌刷新成功: {user_id}")
        
        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌刷新失败: {str(e)}"
        )

@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: UserProfile = Depends(get_current_user)):
    """
    用户登出 - 使用标准化响应模型
    """
    try:
        user_id = current_user.id
        
        # 从会话存储中移除用户
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        print(f"✅ 用户登出成功: {user_id}")
        
        return LogoutResponse(
            success=True,
            message="已成功登出"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"登出失败: {str(e)}"
        )

@router.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):
    return {"user": current_user}
    """
    获取当前用户资料
    """
    return current_user

@router.get("/session")
async def check_session(current_user: UserProfile = Depends(get_optional_user)):
    """
    检查会话状态
    """
    if current_user:
        return {
            "authenticated": True,
            "user": current_user
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }

# 开发环境调试端点
@router.get("/debug/codes")
async def debug_verification_codes():
    """
    查看当前存储的验证码（仅开发环境）
    """
    return {
        "active_codes": len(verification_codes),
        "codes": verification_codes
    }

@router.get("/debug/sessions")
async def debug_user_sessions():
    """
    查看当前用户会话（仅开发环境）
    """
    return {
        "active_sessions": len(user_sessions),
        "sessions": user_sessions
    }

@router.get("/debug/users")
async def debug_local_users():
    """
    查看本地用户存储（仅开发环境）
    """
    return {
        "local_users": local_user_store,
        "creation_locks": list(user_creation_lock.keys())
    }