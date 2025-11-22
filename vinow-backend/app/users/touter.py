"""
用户管理路由 - 极简版
确保能正常导入
"""
from fastapi import APIRouter

# 创建路由实例
router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/test")
async def test_endpoint():
    """测试端点"""
    return {"message": "用户路由工作正常", "status": "success"}

@router.get("/profile")
async def get_profile():
    """获取用户资料 - 极简版"""
    return {
        "id": "user_123",
        "username": "test_user",
        "phone": "+84123456789",
        "status": "active"
    }