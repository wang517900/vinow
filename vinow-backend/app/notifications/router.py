"""
高级功能路由 - v1.7.0
推送通知、第三方登录、安全增强、用户成就
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
import uuid
import time
from datetime import datetime
import hashlib
import jwt

router = APIRouter(prefix="/api/v1", tags=["advanced"])

# 数据模型
class FCMTokenRequest(BaseModel):
    fcm_token: str
    device_id: str
    device_type: str = "android"  # android, ios, web

class NotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None

class ThirdPartyLoginRequest(BaseModel):
    provider: str  # zalo, facebook, google
    access_token: str

class SecuritySettings(BaseModel):
    enable_two_factor: bool = False
    login_alerts: bool = True
    session_timeout: int = 60  # 分钟

class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    unlocked_at: Optional[str] = None
    progress: float = 0.0
    target: float = 1.0

# 模拟数据存储
user_devices = {}
user_notifications = {}
user_achievements = {}
security_settings = {}
third_party_logins = {}

# FCM模拟函数
async def send_fcm_notification(fcm_token: str, title: str, body: str, data: dict = None):
    """模拟发送FCM推送通知"""
    print(f"📱 发送推送通知 -> {fcm_token}")
    print(f"标题: {title}")
    print(f"内容: {body}")
    print(f"数据: {data}")
    
    # 生产环境需要调用FCM API
    # from firebase_admin import messaging
    # message = messaging.Message(
    #     token=fcm_token,
    #     notification=messaging.Notification(
    #         title=title,
    #         body=body,
    #     ),
    #     data=data or {}
    # )
    # response = messaging.send(message)
    
    return {"success": True, "message_id": f"mock_msg_{int(time.time())}"}

# 第三方登录验证模拟
async def verify_zalo_login(access_token: str) -> Dict[str, Any]:
    """验证Zalo登录令牌（模拟）"""
    # 生产环境需要调用Zalo API验证token
    # 这里返回模拟用户数据
    return {
        "user_id": f"zalo_{hashlib.md5(access_token.encode()).hexdigest()[:16]}",
        "name": "Zalo User",
        "email": "user@zalo.com",
        "avatar": "https://example.com/avatar.jpg",
        "phone": "+84123456789"
    }

async def verify_facebook_login(access_token: str) -> Dict[str, Any]:
    """验证Facebook登录令牌（模拟）"""
    # 生产环境需要调用Facebook Graph API
    return {
        "user_id": f"fb_{hashlib.md5(access_token.encode()).hexdigest()[:16]}",
        "name": "Facebook User", 
        "email": "user@facebook.com",
        "avatar": "https://example.com/avatar.jpg"
    }

async def verify_google_login(access_token: str) -> Dict[str, Any]:
    """验证Google登录令牌（模拟）"""
    # 生产环境需要调用Google API
    return {
        "user_id": f"google_{hashlib.md5(access_token.encode()).hexdigest()[:16]}",
        "name": "Google User",
        "email": "user@gmail.com",
        "avatar": "https://example.com/avatar.jpg"
    }

# 通知相关端点
@router.post("/notifications/token")
async def register_fcm_token(request: FCMTokenRequest):
    """
    注册FCM推送令牌
    """
    try:
        user_id = "mock_user_123"  # 生产环境从JWT获取
        
        if user_id not in user_devices:
            user_devices[user_id] = []
        
        # 检查设备是否已存在
        device_exists = False
        for device in user_devices[user_id]:
            if device["device_id"] == request.device_id:
                device["fcm_token"] = request.fcm_token
                device["updated_at"] = datetime.now().isoformat()
                device_exists = True
                break
        
        if not device_exists:
            user_devices[user_id].append({
                "device_id": request.device_id,
                "fcm_token": request.fcm_token,
                "device_type": request.device_type,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        
        print(f"✅ FCM令牌注册成功: {request.device_id}")
        
        return {
            "success": True,
            "message": "FCM令牌注册成功"
        }
        
    except Exception as e:
        raise HTTPException(400, f"注册FCM令牌失败: {str(e)}")

@router.post("/notifications/send")
async def send_notification(request: NotificationRequest):
    """
    发送推送通知（管理员功能）
    """
    try:
        user_id = "mock_user_123"
        
        if user_id not in user_devices:
            raise HTTPException(400, "用户没有注册的设备")
        
        # 发送通知到所有设备
        results = []
        for device in user_devices[user_id]:
            if device.get("fcm_token"):
                result = await send_fcm_notification(
                    device["fcm_token"],
                    request.title,
                    request.body,
                    request.data
                )
                results.append(result)
        
        # 保存通知记录
        notification_id = f"notif_{int(time.time())}"
        if user_id not in user_notifications:
            user_notifications[user_id] = []
        
        user_notifications[user_id].append({
            "id": notification_id,
            "title": request.title,
            "body": request.body,
            "data": request.data,
            "sent_at": datetime.now().isoformat(),
            "read": False
        })
        
        print(f"✅ 推送通知发送成功: {request.title}")
        
        return {
            "success": True,
            "message": "通知发送成功",
            "notification_id": notification_id,
            "sent_to_devices": len(results)
        }
        
    except Exception as e:
        raise HTTPException(400, f"发送通知失败: {str(e)}")

@router.get("/notifications")
async def get_notifications(limit: int = 20, offset: int = 0):
    """
    获取用户通知列表
    """
    user_id = "mock_user_123"
    
    if user_id not in user_notifications:
        user_notifications[user_id] = []
    
    notifications = user_notifications[user_id]
    
    # 分页
    start_index = offset
    end_index = offset + limit
    paginated_notifications = notifications[start_index:end_index]
    
    return {
        "notifications": paginated_notifications,
        "total": len(notifications),
        "unread_count": len([n for n in notifications if not n.get("read", False)])
    }

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """
    标记通知为已读
    """
    user_id = "mock_user_123"
    
    if user_id not in user_notifications:
        raise HTTPException(404, "通知不存在")
    
    for notification in user_notifications[user_id]:
        if notification["id"] == notification_id:
            notification["read"] = True
            notification["read_at"] = datetime.now().isoformat()
            break
    
    return {"success": True, "message": "通知已标记为已读"}

@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """
    删除通知
    """
    user_id = "mock_user_123"
    
    if user_id not in user_notifications:
        raise HTTPException(404, "通知不存在")
    
    user_notifications[user_id] = [
        n for n in user_notifications[user_id] 
        if n["id"] != notification_id
    ]
    
    return {"success": True, "message": "通知已删除"}

# 第三方登录端点
@router.post("/auth/zalo")
async def zalo_login(request: ThirdPartyLoginRequest):
    """
    Zalo第三方登录
    """
    try:
        print(f"🔐 Zalo登录请求: {request.access_token[:20]}...")
        
        # 验证Zalo令牌
        user_info = await verify_zalo_login(request.access_token)
        
        # 创建或获取用户
        user_id = user_info["user_id"]
        
        # 记录第三方登录
        third_party_logins[user_id] = {
            "provider": "zalo",
            "linked_at": datetime.now().isoformat(),
            "user_info": user_info
        }
        
        # 生成JWT令牌（使用之前的模拟令牌生成）
        from app.auth.router import create_mock_tokens, create_mock_user
        
        user_profile = create_mock_user(user_info.get("phone", "+84123456789"))
        user_profile.update({
            "name": user_info["name"],
            "email": user_info.get("email"),
            "avatar": user_info.get("avatar")
        })
        
        tokens = create_mock_tokens(user_id)
        
        print(f"✅ Zalo登录成功: {user_info['name']}")
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": user_profile,
            "expires_in": tokens["expires_in"],
            "is_new_user": True  # 可以根据实际情况判断
        }
        
    except Exception as e:
        print(f"❌ Zalo登录失败: {e}")
        raise HTTPException(401, f"Zalo登录失败: {str(e)}")

@router.post("/auth/facebook")
async def facebook_login(request: ThirdPartyLoginRequest):
    """
    Facebook第三方登录
    """
    try:
        print(f"🔐 Facebook登录请求: {request.access_token[:20]}...")
        
        # 验证Facebook令牌
        user_info = await verify_facebook_login(request.access_token)
        
        # 创建或获取用户
        user_id = user_info["user_id"]
        
        # 记录第三方登录
        third_party_logins[user_id] = {
            "provider": "facebook",
            "linked_at": datetime.now().isoformat(),
            "user_info": user_info
        }
        
        # 生成JWT令牌
        from app.auth.router import create_mock_tokens, create_mock_user
        
        user_profile = create_mock_user("+84123456789")  # 默认手机号
        user_profile.update({
            "name": user_info["name"],
            "email": user_info.get("email"),
            "avatar": user_info.get("avatar")
        })
        
        tokens = create_mock_tokens(user_id)
        
        print(f"✅ Facebook登录成功: {user_info['name']}")
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": user_profile,
            "expires_in": tokens["expires_in"],
            "is_new_user": True
        }
        
    except Exception as e:
        print(f"❌ Facebook登录失败: {e}")
        raise HTTPException(401, f"Facebook登录失败: {str(e)}")

@router.post("/auth/google")
async def google_login(request: ThirdPartyLoginRequest):
    """
    Google第三方登录
    """
    try:
        print(f"🔐 Google登录请求: {request.access_token[:20]}...")
        
        # 验证Google令牌
        user_info = await verify_google_login(request.access_token)
        
        # 创建或获取用户
        user_id = user_info["user_id"]
        
        # 记录第三方登录
        third_party_logins[user_id] = {
            "provider": "google", 
            "linked_at": datetime.now().isoformat(),
            "user_info": user_info
        }
        
        # 生成JWT令牌
        from app.auth.router import create_mock_tokens, create_mock_user
        
        user_profile = create_mock_user("+84123456789")  # 默认手机号
        user_profile.update({
            "name": user_info["name"],
            "email": user_info.get("email"),
            "avatar": user_info.get("avatar")
        })
        
        tokens = create_mock_tokens(user_id)
        
        print(f"✅ Google登录成功: {user_info['name']}")
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": user_profile,
            "expires_in": tokens["expires_in"],
            "is_new_user": True
        }
        
    except Exception as e:
        print(f"❌ Google登录失败: {e}")
        raise HTTPException(401, f"Google登录失败: {str(e)}")

# 安全设置端点
@router.get("/users/security", response_model=SecuritySettings)
async def get_security_settings():
    """
    获取用户安全设置
    """
    user_id = "mock_user_123"
    
    if user_id not in security_settings:
        # 默认安全设置
        security_settings[user_id] = {
            "enable_two_factor": False,
            "login_alerts": True,
            "session_timeout": 60
        }
    
    return security_settings[user_id]

@router.put("/users/security", response_model=SecuritySettings)
async def update_security_settings(request: SecuritySettings):
    """
    更新用户安全设置
    """
    user_id = "mock_user_123"
    security_settings[user_id] = request.dict()
    
    print(f"✅ 安全设置已更新: {security_settings[user_id]}")
    
    return security_settings[user_id]

@router.post("/users/security/two-factor")
async def enable_two_factor():
    """
    启用双重认证
    """
    user_id = "mock_user_123"
    
    if user_id not in security_settings:
        security_settings[user_id] = {}
    
    security_settings[user_id]["enable_two_factor"] = True
    
    # 生成2FA密钥（模拟）
    two_factor_secret = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()
    
    # 生成QR码URL（模拟）
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?data=otpauth://totp/Vinow:{user_id}?secret={two_factor_secret}&issuer=Vinow"
    
    return {
        "success": True,
        "message": "双重认证已启用",
        "two_factor_secret": two_factor_secret,
        "qr_code_url": qr_code_url
    }

@router.post("/users/security/change-password")
async def change_password(old_password: str, new_password: str):
    """
    修改密码（模拟）
    """
    # 生产环境需要验证旧密码并加密新密码
    print(f"🔐 密码修改请求")
    print(f"旧密码: {old_password} -> 新密码: {new_password}")
    
    # 模拟密码强度检查
    if len(new_password) < 6:
        raise HTTPException(400, "密码长度至少6位")
    
    return {
        "success": True,
        "message": "密码修改成功"
    }

# 用户成就系统
@router.get("/users/achievements", response_model=List[Achievement])
async def get_achievements():
    """
    获取用户成就列表
    """
    user_id = "mock_user_123"
    
    if user_id not in user_achievements:
        # 初始化默认成就
        user_achievements[user_id] = [
            {
                "id": "first_order",
                "name": "首次下单",
                "description": "完成第一次订单",
                "icon": "🛒",
                "unlocked_at": "2024-01-01T00:00:00Z",
                "progress": 1.0,
                "target": 1.0
            },
            {
                "id": "food_reviewer", 
                "name": "美食评论家",
                "description": "发表5条评价",
                "icon": "📝",
                "unlocked_at": None,
                "progress": 2.0,
                "target": 5.0
            },
            {
                "id": "explorer",
                "name": "美食探索者", 
                "description": "在10家不同商家下单",
                "icon": "🗺️",
                "unlocked_at": None,
                "progress": 3.0,
                "target": 10.0
            },
            {
                "id": "saver",
                "name": "省钱达人",
                "description": "累计节省500,000 VND",
                "icon": "💰", 
                "unlocked_at": None,
                "progress": 125000.0,
                "target": 500000.0
            },
            {
                "id": "loyal_customer",
                "name": "忠实顾客",
                "description": "连续30天使用应用",
                "icon": "📱",
                "unlocked_at": None, 
                "progress": 15.0,
                "target": 30.0
            }
        ]
    
    return user_achievements[user_id]

@router.get("/users/achievements/stats")
async def get_achievement_stats():
    """
    获取用户成就统计
    """
    user_id = "mock_user_123"
    
    if user_id not in user_achievements:
        await get_achievements()  # 初始化成就
    
    achievements = user_achievements[user_id]
    
    total_achievements = len(achievements)
    unlocked_achievements = len([a for a in achievements if a["unlocked_at"] is not None])
    in_progress_achievements = len([a for a in achievements if a["progress"] > 0 and a["unlocked_at"] is None])
    
    return {
        "total_achievements": total_achievements,
        "unlocked_achievements": unlocked_achievements,
        "in_progress_achievements": in_progress_achievements,
        "completion_rate": round((unlocked_achievements / total_achievements) * 100, 1) if total_achievements > 0 else 0
    }

@router.post("/achievements/{achievement_id}/unlock")
async def unlock_achievement(achievement_id: str):
    """
    解锁成就（开发测试用）
    """
    user_id = "mock_user_123"
    
    if user_id not in user_achievements:
        await get_achievements()
    
    for achievement in user_achievements[user_id]:
        if achievement["id"] == achievement_id:
            achievement["unlocked_at"] = datetime.now().isoformat()
            achievement["progress"] = achievement["target"]
            
            print(f"🎉 成就解锁: {achievement['name']}")
            
            # 发送成就解锁通知
            await send_fcm_notification(
                "mock_fcm_token",  # 生产环境使用真实token
                "成就解锁！",
                f"您已解锁成就：{achievement['name']}",
                {"type": "achievement", "id": achievement_id}
            )
            
            return {
                "success": True,
                "message": f"成就 '{achievement['name']}' 已解锁",
                "achievement": achievement
            }
    
    raise HTTPException(404, "成就不存在")

# 开发工具端点
@router.get("/debug/third-party-logins")
async def debug_third_party_logins():
    """
    查看第三方登录状态（仅开发环境）
    """
    return {
        "third_party_logins": third_party_logins,
        "user_devices": user_devices
    }

@router.post("/debug/send-test-notification")
async def send_test_notification():
    """
    发送测试通知（仅开发环境）
    """
    request = NotificationRequest(
        title="测试通知",
        body="这是一个测试推送通知",
        data={"type": "test", "action": "debug"}
    )
    
    return await send_notification(request)