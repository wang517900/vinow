"""
认证工具函数模块
包含认证相关的辅助函数
"""
from supabase import Client
from fastapi import HTTPException, status
from app.models.user import UserProfile, UserPreferences

async def create_or_update_user_profile(supabase: Client, user):
    """
    创建或更新用户资料
    
    Args:
        supabase: Supabase 客户端
        user: 认证用户对象
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 检查用户资料是否已存在
        profile_response = supabase.table("user_profiles").select("*").eq("id", user.id).execute()
        
        if not profile_response.data:
            # 创建新用户资料
            profile_data = {
                "id": user.id,
                "phone": user.phone,
                "username": f"user_{user.id[:8]}",  # 生成默认用户名
                "full_name": None,
                "avatar_url": None,
                "date_of_birth": None,
                "gender": None,
                "created_at": "now()",
                "updated_at": "now()"
            }
            
            profile_result = supabase.table("user_profiles").insert(profile_data).execute()
            
            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="用户资料创建失败"
                )
            
            # 创建用户偏好设置
            preferences_data = {
                "user_id": user.id,
                "language": "vi",
                "notification_enabled": True,
                "dietary_restrictions": None,
                "favorite_cuisines": None
            }
            
            preferences_result = supabase.table("user_preferences").insert(preferences_data).execute()
            
            if not preferences_result.data:
                # 回滚：删除已创建的用户资料
                supabase.table("user_profiles").delete().eq("id", user.id).execute()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="用户偏好设置创建失败"
                )
            
            print(f"✅ 新用户资料创建成功: {user.id}")
        else:
            print(f"✅ 用户资料已存在: {user.id}")
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 用户资料操作失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"用户资料操作失败: {str(e)}"
        )

async def get_user_profile(supabase: Client, user_id: str):
    """
    获取用户资料
    
    Args:
        supabase: Supabase 客户端
        user_id: 用户ID
    
    Returns:
        dict: 用户资料数据
    """
    try:
        # 查询用户资料
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户资料不存在"
            )
        
        return profile_response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取用户资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户资料失败: {str(e)}"
        )