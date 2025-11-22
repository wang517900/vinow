"""
用户数据模型模块
定义 Pydantic 模型用于请求/响应验证
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime

class SendOTPRequest(BaseModel):
    """发送验证码请求模型"""
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        """验证越南手机号格式"""
        # 越南手机号格式: +84开头，后面是3-9，然后是8位数字
        if not v.startswith('+84'):
            raise ValueError('手机号必须以 +84 开头')
        if len(v) != 12:  # +84 + 9位数字 = 12位
            raise ValueError('手机号长度不正确')
        if not v[3:].isdigit():
            raise ValueError('手机号必须全部为数字')
        return v

class VerifyOTPRequest(BaseModel):
    """验证验证码请求模型"""
    phone: str
    token: str
    
    @validator('token')
    def validate_token(cls, v):
        """验证验证码格式"""
        if len(v) != 6 or not v.isdigit():
            raise ValueError('验证码必须是6位数字')
        return v

class AuthResponse(BaseModel):
    """认证响应模型"""
    access_token: str
    refresh_token: str
    user: Dict[str, Any]
    expires_in: int
    token_type: str = "bearer"

class UserProfile(BaseModel):
    """用户资料模型"""
    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UserPreferences(BaseModel):
    """用户偏好设置模型"""
    user_id: str
    language: str = "vi"
    notification_enabled: bool = True
    dietary_restrictions: Optional[Dict[str, Any]] = None
    favorite_cuisines: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: bool = True
    code: int
    message: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


    内容系统

    from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
from uuid import UUID, uuid4

class UserRole(str, Enum):
    USER = "user"
    CREATOR = "creator"
    MODERATOR = "moderator"
    ADMIN = "admin"

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_]+$")
    full_name: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[Dict[str, Any]] = None

class UserInDB(UserBase):
    id: UUID = Field(default_factory=uuid4)
    password_hash: str
    is_active: bool = True
    is_verified: bool = False
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    role: UserRole
    created_at: datetime
    updated_at: datetime

class UserProfile(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    social_links: Dict[str, Any] = Field(default_factory=dict)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)