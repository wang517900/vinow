"""
通用数据模型模块 - 按照行业标准优化
定义整个v1系列共享的数据模型
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class UserRole(str, Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    ADMIN = "admin"

# 认证相关模型 - 按照行业标准优化
class SendOTPRequest(BaseModel):
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v.startswith('+84') or len(v) != 12:
            raise ValueError('越南手机号必须以+84开头，共12位')
        return v

class SendOTPResponse(BaseModel):
    """发送验证码响应 - 行业标准"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str  # 行业标准：使用code表示验证码
    
    @validator('code')
    def validate_code(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('验证码必须是6位数字')
        return v

class VerifyOTPResponse(BaseModel):
    """验证验证码响应 - 行业标准"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    """刷新令牌响应 - 行业标准"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class LogoutRequest(BaseModel):
    """登出请求 - 行业标准"""
    access_token: str

class LogoutResponse(BaseModel):
    """登出响应 - 行业标准"""
    success: bool = True
    message: str

# 用户相关模型
class UserProfile(BaseModel):
    id: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    phone: str
    email: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[Gender]
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime
    updated_at: datetime

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    date_of_birth: Optional[str] = None
    gender: Optional[Gender] = None

class UserPreferences(BaseModel):
    language: str = "vi"
    notification_enabled: bool = True
    dietary_restrictions: Optional[Dict[str, Any]] = None
    favorite_cuisines: Optional[Dict[str, Any]] = None

class Address(BaseModel):
    id: str
    label: str
    recipient_name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    district: str
    ward: str
    is_default: bool

class CreateAddressRequest(BaseModel):
    label: str
    recipient_name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    district: str
    ward: str
    is_default: bool = False

# 互动相关模型
class FavoriteType(str, Enum):
    MERCHANT = "merchant"
    PRODUCT = "product"

class FavoriteRequest(BaseModel):
    merchant_id: Optional[str] = None
    product_id: Optional[str] = None
    favorite_type: FavoriteType

class BrowsingHistory(BaseModel):
    id: str
    user_id: str
    merchant_id: Optional[str] = None
    product_id: Optional[str] = None
    viewed_at: datetime
    duration_seconds: int = 0

class SearchHistory(BaseModel):
    id: str
    user_id: str
    query_text: str
    search_type: str
    filters: Optional[Dict[str, Any]] = None
    result_count: int = 0
    searched_at: datetime

# 订单相关模型
class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    CASH = "cash"
    MOMO = "momo"
    ZALOPAY = "zalopay"
    BANKING = "banking"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    unit_price: float
    quantity: int
    options: Optional[Dict[str, Any]] = None
    subtotal: float

class CreateOrderRequest(BaseModel):
    merchant_id: str
    items: List[OrderItem]
    payment_method: PaymentMethod
    delivery_address: Dict[str, Any]
    special_instructions: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    user_id: str
    merchant_id: str
    status: OrderStatus
    total_amount: float
    discount_amount: float = 0
    final_amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    delivery_address: Dict[str, Any]
    special_instructions: Optional[str] = None
    estimated_preparation_time: Optional[int] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]

# 评价相关模型
class ReviewRating(BaseModel):
    taste: int
    service: int
    environment: int
    value: int

class CreateReviewRequest(BaseModel):
    order_id: str
    rating: int
    title: Optional[str] = None
    content: Optional[str] = None
    image_urls: Optional[List[str]] = None
    is_anonymous: bool = False
    detailed_ratings: Optional[ReviewRating] = None

class ReviewResponse(BaseModel):
    id: str
    user_id: str
    order_id: str
    merchant_id: str
    rating: int
    title: Optional[str] = None
    content: Optional[str] = None
    image_urls: Optional[List[str]] = None
    is_anonymous: bool
    helpful_count: int = 0
    view_count: int = 0
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    detailed_ratings: Optional[ReviewRating] = None
    user_profile: Optional[UserProfile] = None

# 分析相关模型
class AnalyticsPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

class AnalyticsRequest(BaseModel):
    period: AnalyticsPeriod
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class UserAnalytics(BaseModel):
    total_orders: int = 0
    total_spent: float = 0
    money_saved: float = 0
    favorite_cuisines: List[str] = []
    average_rating: float = 0
    review_count: int = 0
    favorite_merchants: List[str] = []
    last_order_at: Optional[datetime] = None

# 支付相关模型
class PaymentInitRequest(BaseModel):
    order_id: str
    payment_method: PaymentMethod
    amount: float
    return_url: str

class PaymentResponse(BaseModel):
    payment_url: str
    transaction_id: str
    qr_code: Optional[str] = None

# 通用响应模型 - 按照行业标准优化
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool

# 向后兼容的别名（可选，用于平滑过渡）
# 如果您需要暂时支持旧的token字段，可以添加这个兼容模型
class VerifyOTPRequestLegacy(BaseModel):
    """向后兼容模型 - 支持旧的token字段"""
    phone: str
    token: str  # 旧字段名
    
    @validator('token')
    def validate_token(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('验证码必须是6位数字')
        return v