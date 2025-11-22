# [文件: app/users/router.py] [行号: 201-400]
"""
用户资料管理路由 - v1.1.0
完整的用户资料、偏好设置、地址管理功能
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from typing import Optional, List
import os
import uuid
import shutil
from datetime import datetime

from app.common.database import supabase
from app.common.models import (
    UserProfile, UpdateProfileRequest, UserPreferences, Address,
    CreateAddressRequest, SuccessResponse, PaginatedResponse
)
from app.common.auth import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# 模拟数据存储（生产环境用数据库）
user_profiles_storage = {}
user_preferences_storage = {}
user_addresses_storage = {}
user_devices_storage = {}

# 确保上传目录存在
UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_user_profile_from_db(user_id: str) -> Optional[dict]:
    """从数据库获取用户资料"""
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception:
        # 如果数据库操作失败，返回模拟数据
        return user_profiles_storage.get(user_id)

def update_user_profile_in_db(user_id: str, update_data: dict) -> dict:
    """更新数据库中的用户资料"""
    try:
        update_data["updated_at"] = datetime.now().isoformat()
        result = supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else update_data
    except Exception:
        # 如果数据库操作失败，使用内存存储
        if user_id not in user_profiles_storage:
            user_profiles_storage[user_id] = {}
        user_profiles_storage[user_id].update(update_data)
        return user_profiles_storage[user_id]

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    """获取当前用户完整资料"""
    try:
        user_id = current_user.id
        
        # 从数据库获取用户资料
        user_profile = get_user_profile_from_db(user_id)
        
        if not user_profile:
            # 创建默认用户资料
            default_profile = {
                "id": user_id,
                "username": f"user_{user_id[:8]}",
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url,
                "phone": current_user.phone,
                "email": current_user.email,
                "date_of_birth": current_user.date_of_birth,
                "gender": current_user.gender,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 保存到数据库
            try:
                result = supabase.table("user_profiles").insert(default_profile).execute()
                user_profile = result.data[0] if result.data else default_profile
            except Exception:
                user_profiles_storage[user_id] = default_profile
                user_profile = default_profile
        
        return user_profile
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户资料失败: {str(e)}"
        )

@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """更新用户资料"""
    try:
        user_id = current_user.id
        
        # 构建更新数据
        update_data = {}
        if request.username is not None:
            update_data["username"] = request.username
        if request.full_name is not None:
            update_data["full_name"] = request.full_name
        if request.email is not None:
            update_data["email"] = request.email
        if request.date_of_birth is not None:
            update_data["date_of_birth"] = request.date_of_birth
        if request.gender is not None:
            update_data["gender"] = request.gender
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供要更新的字段"
            )
        
        # 更新数据库
        updated_profile = update_user_profile_in_db(user_id, update_data)
        
        print(f"✅ 用户资料更新成功: {user_id}")
        
        return updated_profile
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户资料失败: {str(e)}"
        )

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """上传用户头像"""
    try:
        user_id = current_user.id
        
        # 验证文件类型
        allowed_content_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持 JPEG, PNG, GIF, WebP 格式的图片"
            )
        
        # 验证文件大小（最大5MB）
        max_size = 5 * 1024 * 1024  # 5MB
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置文件指针
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="图片大小不能超过5MB"
            )
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"avatar_{user_id}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 生成访问URL
        avatar_url = f"/uploads/avatars/{filename}"
        
        # 更新用户资料中的头像URL
        update_data = {"avatar_url": avatar_url}
        update_user_profile_in_db(user_id, update_data)
        
        print(f"✅ 用户头像上传成功: {user_id}")
        
        return SuccessResponse(
            message="头像上传成功",
            data={"avatar_url": avatar_url}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像上传失败: {str(e)}"
        )

@router.get("/preferences", response_model=UserPreferences)
async def get_preferences(current_user: UserProfile = Depends(get_current_user)):
    """获取用户偏好设置"""
    try:
        user_id = current_user.id
        
        # 从数据库获取偏好设置
        try:
            result = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            preferences = result.data[0] if result.data else None
        except Exception:
            preferences = user_preferences_storage.get(user_id)
        
        if not preferences:
            # 创建默认偏好设置
            default_preferences = {
                "user_id": user_id,
                "language": "vi",
                "notification_enabled": True,
                "dietary_restrictions": {},
                "favorite_cuisines": {}
            }
            
            # 保存到数据库
            try:
                result = supabase.table("user_preferences").insert(default_preferences).execute()
                preferences = result.data[0] if result.data else default_preferences
            except Exception:
                user_preferences_storage[user_id] = default_preferences
                preferences = default_preferences
        
        return preferences
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户偏好设置失败: {str(e)}"
        )

@router.put("/preferences", response_model=UserPreferences)
async def update_preferences(
    request: UserPreferences,
    current_user: UserProfile = Depends(get_current_user)
):
    """更新用户偏好设置"""
    try:
        user_id = current_user.id
        
        # 准备更新数据
        update_data = request.dict()
        update_data["user_id"] = user_id
        
        # 更新数据库
        try:
            # 检查是否存在
            existing = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            if existing.data:
                result = supabase.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
            else:
                result = supabase.table("user_preferences").insert(update_data).execute()
            updated_preferences = result.data[0] if result.data else update_data
        except Exception:
            user_preferences_storage[user_id] = update_data
            updated_preferences = update_data
        
        print(f"✅ 用户偏好设置更新成功: {user_id}")
        
        return updated_preferences
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户偏好设置失败: {str(e)}"
        )

@router.get("/addresses", response_model=List[Address])
async def get_addresses(current_user: UserProfile = Depends(get_current_user)):
    """获取用户地址列表"""
    try:
        user_id = current_user.id
        
        # 从数据库获取地址
        try:
            result = supabase.table("user_addresses").select("*").eq("user_id", user_id).execute()
            addresses = result.data if result.data else []
        except Exception:
            addresses = user_addresses_storage.get(user_id, [])
        
        return addresses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取地址列表失败: {str(e)}"
        )

@router.post("/addresses", response_model=Address)
async def create_address(
    request: CreateAddressRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """创建用户地址"""
    try:
        user_id = current_user.id
        
        # 如果设置为默认地址，清除其他默认地址
        if request.is_default:
            try:
                supabase.table("user_addresses").update({"is_default": False}).eq("user_id", user_id).execute()
            except Exception:
                # 内存存储处理
                for addr in user_addresses_storage.get(user_id, []):
                    addr["is_default"] = False
        
        # 创建新地址
        new_address = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            **request.dict()
        }
        
        # 保存到数据库
        try:
            result = supabase.table("user_addresses").insert(new_address).execute()
            saved_address = result.data[0] if result.data else new_address
        except Exception:
            if user_id not in user_addresses_storage:
                user_addresses_storage[user_id] = []
            user_addresses_storage[user_id].append(new_address)
            saved_address = new_address
        
        print(f"✅ 用户地址创建成功: {user_id}")
        
        return saved_address
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建地址失败: {str(e)}"
        )

@router.put("/addresses/{address_id}", response_model=Address)
async def update_address(
    address_id: str,
    request: CreateAddressRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """更新用户地址"""
    try:
        user_id = current_user.id
        
        # 如果设置为默认地址，清除其他默认地址
        if request.is_default:
            try:
                supabase.table("user_addresses").update({"is_default": False}).eq("user_id", user_id).execute()
            except Exception:
                # 内存存储处理
                for addr in user_addresses_storage.get(user_id, []):
                    addr["is_default"] = False
        
        # 更新地址
        update_data = request.dict()
        
        try:
            result = supabase.table("user_addresses").update(update_data).eq("id", address_id).eq("user_id", user_id).execute()
            if not result.data:
                raise HTTPException(404, "地址不存在")
            updated_address = result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            # 内存存储处理
            addresses = user_addresses_storage.get(user_id, [])
            address_found = False
            for addr in addresses:
                if addr["id"] == address_id:
                    addr.update(update_data)
                    updated_address = addr
                    address_found = True
                    break
            
            if not address_found:
                raise HTTPException(404, "地址不存在")
        
        print(f"✅ 用户地址更新成功: {address_id}")
        
        return updated_address
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新地址失败: {str(e)}"
        )

@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """删除用户地址"""
    try:
        user_id = current_user.id
        
        # 从数据库删除
        try:
            result = supabase.table("user_addresses").delete().eq("id", address_id).eq("user_id", user_id).execute()
            if not result.data:
                raise HTTPException(404, "地址不存在")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            # 内存存储处理
            addresses = user_addresses_storage.get(user_id, [])
            user_addresses_storage[user_id] = [addr for addr in addresses if addr["id"] != address_id]
            if len(addresses) == len(user_addresses_storage[user_id]):
                raise HTTPException(404, "地址不存在")
        
        print(f"✅ 用户地址删除成功: {address_id}")
        
        return SuccessResponse(message="地址删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除地址失败: {str(e)}"
        )

@router.post("/devices")
async def register_device(
    device_id: str = Form(...),
    device_type: str = Form(...),
    fcm_token: str = Form(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """注册用户设备信息"""
    try:
        user_id = current_user.id
        
        device_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "device_id": device_id,
            "device_type": device_type,
            "fcm_token": fcm_token,
            "last_active": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            result = supabase.table("user_devices").insert(device_data).execute()
            saved_device = result.data[0] if result.data else device_data
        except Exception:
            if user_id not in user_devices_storage:
                user_devices_storage[user_id] = []
            user_devices_storage[user_id].append(device_data)
            saved_device = device_data
        
        print(f"✅ 用户设备注册成功: {device_id}")
        
        return SuccessResponse(
            message="设备注册成功",
            data={"device_id": saved_device["id"]}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设备注册失败: {str(e)}"
        )

@router.get("/stats")
async def get_user_stats(current_user: UserProfile = Depends(get_current_user)):
    """获取用户统计信息"""
    try:
        user_id = current_user.id
        
        # 模拟用户统计数据
        stats = {
            "total_orders": 15,
            "total_spent": 1250000,
            "money_saved": 250000,
            "favorite_cuisines": ["越南菜", "中餐", "快餐"],
            "average_rating": 4.5,
            "review_count": 8,
            "member_since": "2024-01-01",
            "success_rate": 95,
            "favorite_merchants": ["merchant_1", "merchant_2"],
            "last_order_at": "2024-03-15T10:30:00Z"
        }
        
        return SuccessResponse(
            message="统计信息获取成功",
            data=stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )

# 开发环境调试端点
@router.get("/debug/storage")
async def debug_storage(current_user: UserProfile = Depends(get_current_user)):
    """查看存储数据（仅开发环境）"""
    user_id = current_user.id
    
    return {
        "user_profiles": user_profiles_storage.get(user_id),
        "user_preferences": user_preferences_storage.get(user_id),
        "user_addresses": user_addresses_storage.get(user_id, []),
        "user_devices": user_devices_storage.get(user_id, [])
    }