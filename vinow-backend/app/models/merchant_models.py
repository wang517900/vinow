# -*- coding: utf-8 -*-
"""商家系统 - merchant_models"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


# -----------------------------
# 枚举类型（分类、星期、状态）
# -----------------------------

class MerchantStatus(str, Enum):
    """商家状态枚举"""
    PENDING = "pending"      # 待审核
    ACTIVE = "active"        # 活跃
    SUSPENDED = "suspended"  # 暂停
    REJECTED = "rejected"    # 已拒绝


class BusinessCategory(str, Enum):
    """商家类别枚举"""
    RESTAURANT = "restaurant"        # 餐厅
    CAFE = "cafe"                    # 咖啡馆
    BEAUTY_SALON = "beauty_salon"    # 美容沙龙
    FITNESS = "fitness"              # 健身
    RETAIL = "retail"                # 零售
    ENTERTAINMENT = "entertainment"  # 娱乐
    HEALTHCARE = "healthcare"        # 医疗保健
    OTHER = "other"                  # 其他


class DayOfWeek(str, Enum):
    """星期枚举"""
    MONDAY = "monday"        # 星期一
    TUESDAY = "tuesday"      # 星期二
    WEDNESDAY = "wednesday"  # 星期三
    THURSDAY = "thursday"    # 星期四
    FRIDAY = "friday"        # 星期五
    SATURDAY = "saturday"    # 星期六
    SUNDAY = "sunday"        # 星期日


# -----------------------------
# 营销相关枚举
# -----------------------------

class PromotionType(str, Enum):
    """促销类型枚举"""
    PERCENTAGE_DISCOUNT = "percentage_discount"     # 百分比折扣
    FIXED_AMOUNT_DISCOUNT = "fixed_amount_discount" # 固定金额折扣
    BUY_ONE_GET_ONE = "buy_one_get_one"             # 买一送一
    FREE_SHIPPING = "free_shipping"                 # 免运费


class PromotionStatus(str, Enum):
    """促销状态枚举"""
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 活跃
    INACTIVE = "inactive"    # 非活跃
    EXPIRED = "expired"      # 已过期


class CouponType(str, Enum):
    """优惠券类型枚举"""
    SINGLE_USE = "single_use"    # 单次使用
    MULTI_USE = "multi_use"      # 多次使用
    UNLIMITED = "unlimited"      # 无限制


# -----------------------------
# 营业时间
# -----------------------------

class BusinessHours(BaseModel):
    """营业时间模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    day: DayOfWeek                           # 星期几
    open_time: Optional[str] = None         # 开始营业时间 (HH:MM格式)
    close_time: Optional[str] = None        # 结束营业时间 (HH:MM格式)
    is_closed: bool = False                 # 是否休息

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v):
        """验证时间格式是否正确 (HH:MM)"""
        if v is None:
            return v
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("时间必须为 HH:MM 格式")
        return v


# -----------------------------
# 商家创建
# -----------------------------

class MerchantCreate(BaseModel):
    """商家创建请求模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: str = Field(..., min_length=1, max_length=100)           # 商家名称
    description: Optional[str] = Field(None, max_length=500)       # 描述
    category: BusinessCategory                                     # 商家类别

    # 地址信息（更适合越南地址结构）
    address: str = Field(..., min_length=1, max_length=200)        # 地址
    district: Optional[str] = None                                 # 郡/县
    province: Optional[str] = None                                 # 省/市
    ward: Optional[str] = None                                     # 坊/社

    latitude: Optional[float] = Field(None, ge=-90, le=90)         # 纬度
    longitude: Optional[float] = Field(None, ge=-180, le=180)      # 经度

    phone: str                                                     # 电话号码
    email: Optional[str] = None                                    # 邮箱
    website: Optional[str] = None                                  # 网站

    # 商家媒体资源
    logo_url: Optional[str] = None                                 # Logo链接
    banner_url: Optional[str] = None                               # 横幅链接

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """验证越南手机号码格式"""
        if v is None:
            return v

        # 去掉空格
        v = v.replace(" ", "")

        # 越南手机号规则
        pattern = r'^(0|\+84)(3|5|7|8|9)[0-9]{8}$'

        if not re.match(pattern, v):
            raise ValueError("无效的越南手机号码")

        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v is None:
            return v

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(pattern, v):
            raise ValueError("无效的邮箱格式")

        return v


# -----------------------------
# 商家更新
# -----------------------------

class MerchantUpdate(BaseModel):
    """商家更新请求模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)  # 商家名称
    description: Optional[str] = Field(None, max_length=500)         # 描述
    category: Optional[BusinessCategory] = None                      # 商家类别
    address: Optional[str] = Field(None, max_length=200)             # 地址
    district: Optional[str] = None                                   # 郡/县
    province: Optional[str] = None                                   # 省/市
    ward: Optional[str] = None                                       # 坊/社
    latitude: Optional[float] = Field(None, ge=-90, le=90)           # 纬度
    longitude: Optional[float] = Field(None, ge=-180, le=180)        # 经度

    phone: Optional[str] = None                                      # 电话号码
    email: Optional[str] = None                                      # 邮箱
    website: Optional[str] = None                                    # 网站
    logo_url: Optional[str] = None                                   # Logo链接
    banner_url: Optional[str] = None                                 # 横幅链接

    status: Optional[MerchantStatus] = None                          # 商家状态

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """验证越南手机号码格式"""
        if v is None:
            return v

        # 去掉空格
        v = v.replace(" ", "")

        # 越南手机号规则
        pattern = r'^(0|\+84)(3|5|7|8|9)[0-9]{8}$'

        if not re.match(pattern, v):
            raise ValueError("无效的越南手机号码")

        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v is None:
            return v

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(pattern, v):
            raise ValueError("无效的邮箱格式")

        return v


# -----------------------------
# 商家响应模型
# -----------------------------

class MerchantResponse(BaseModel):
    """商家响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str                            # 商家ID
    name: str                          # 商家名称
    description: Optional[str]         # 描述
    category: BusinessCategory         # 商家类别
    address: str                       # 地址
    district: Optional[str]            # 郡/县
    province: Optional[str]            # 省/市
    ward: Optional[str]                # 坊/社

    latitude: Optional[float]          # 纬度
    longitude: Optional[float]         # 经度

    phone: str                         # 电话号码
    email: Optional[str]               # 邮箱
    website: Optional[str]             # 网站

    logo_url: Optional[str]            # Logo链接
    banner_url: Optional[str]          # 横幅链接

    status: MerchantStatus             # 商家状态
    owner_id: str                      # 所有者ID

    created_at: datetime               # 创建时间
    updated_at: datetime               # 更新时间

    average_rating: Optional[float] = None  # 平均评分
    review_count: int = 0                   # 评论数


# -----------------------------
# 商家列表响应
# -----------------------------

class MerchantListResponse(BaseModel):
    """商家列表响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    merchants: List[MerchantResponse]  # 商家列表
    total_count: int                   # 总数
    page: int                          # 当前页码
    page_size: int                     # 每页大小


# -----------------------------
# 营业时间创建
# -----------------------------

class BusinessHoursCreate(BaseModel):
    """营业时间创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    business_hours: List[BusinessHours]  # 营业时间列表


# -----------------------------
# 商家搜索筛选
# -----------------------------

class MerchantSearchParams(BaseModel):
    """商家搜索参数模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    query: Optional[str] = None                        # 搜索关键词
    category: Optional[BusinessCategory] = None        # 商家类别筛选

    latitude: Optional[float] = None                   # 纬度
    longitude: Optional[float] = None                  # 经度
    radius: Optional[float] = None                     # 搜索半径(公里)

    min_rating: Optional[float] = None                 # 最低评分
    is_open_now: Optional[bool] = None                 # 是否当前营业

    sort_by: Optional[str] = Field(
        default="distance",
        description="排序依据: distance(距离) | rating(评分) | created_at(创建时间)"
    )

    page: int = 1                                      # 页码
    page_size: int = 20                                # 每页大小


# -----------------------------
# 营销模型 - 促销活动
# -----------------------------

class PromotionCreate(BaseModel):
    """促销活动创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    merchant_id: str                                         # 关联商家ID
    name: str = Field(..., min_length=1, max_length=100)     # 促销名称
    description: Optional[str] = Field(None, max_length=500) # 促销描述
    promotion_type: PromotionType                            # 促销类型
    discount_value: Optional[float] = None                   # 折扣值 (如10表示10%或10元)
    minimum_purchase: Optional[float] = None                 # 最低购买金额要求
    maximum_discount: Optional[float] = None                 # 最大折扣金额（适用于百分比折扣）
    start_date: datetime                                     # 开始时间
    end_date: datetime                                       # 结束时间
    is_active: bool = True                                   # 是否激活

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """验证结束时间必须晚于开始时间"""
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class PromotionUpdate(BaseModel):
    """促销活动更新模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)  # 促销名称
    description: Optional[str] = Field(None, max_length=500)         # 促销描述
    promotion_type: Optional[PromotionType] = None                   # 促销类型
    discount_value: Optional[float] = None                           # 折扣值
    minimum_purchase: Optional[float] = None                         # 最低购买金额要求
    maximum_discount: Optional[float] = None                         # 最大折扣金额
    start_date: Optional[datetime] = None                            # 开始时间
    end_date: Optional[datetime] = None                              # 结束时间
    is_active: Optional[bool] = None                                 # 是否激活

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """验证结束时间必须晚于开始时间"""
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class PromotionResponse(BaseModel):
    """促销活动响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str                           # 促销ID
    merchant_id: str                  # 关联商家ID
    name: str                         # 促销名称
    description: Optional[str]        # 促销描述
    promotion_type: PromotionType     # 促销类型
    discount_value: Optional[float]   # 折扣值
    minimum_purchase: Optional[float] # 最低购买金额要求
    maximum_discount: Optional[float] # 最大折扣金额
    start_date: datetime              # 开始时间
    end_date: datetime                # 结束时间
    is_active: bool                   # 是否激活
    status: PromotionStatus           # 促销状态
    created_at: datetime              # 创建时间
    updated_at: datetime              # 更新时间


# -----------------------------
# 营销模型 - 优惠券
# -----------------------------

class CouponCreate(BaseModel):
    """优惠券创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    merchant_id: str                                          # 关联商家ID
    code: str = Field(..., min_length=3, max_length=50)      # 优惠码
    name: str = Field(..., min_length=1, max_length=100)     # 优惠券名称
    description: Optional[str] = Field(None, max_length=500) # 优惠券描述
    coupon_type: CouponType                                  # 优惠券类型
    discount_type: PromotionType                             # 折扣类型
    discount_value: float                                    # 折扣值
    minimum_purchase: Optional[float] = None                 # 最低购买金额要求
    maximum_discount: Optional[float] = None                 # 最大折扣金额
    valid_from: datetime                                     # 有效期开始时间
    valid_to: datetime                                       # 有效期结束时间
    usage_limit: Optional[int] = None                        # 总使用次数限制
    per_user_limit: Optional[int] = None                     # 每用户使用次数限制
    is_active: bool = True                                   # 是否激活

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """验证优惠码格式"""
        if not re.match(r'^[A-Z0-9_]+$', v.upper()):
            raise ValueError('优惠码只能包含大写字母、数字和下划线')
        return v.upper()

    @field_validator('valid_to')
    @classmethod
    def validate_validity_period(cls, v, info):
        """验证有效期结束时间必须晚于开始时间"""
        valid_from = info.data.get('valid_from')
        if valid_from and v < valid_from:
            raise ValueError('有效期结束时间必须晚于开始时间')
        return v


class CouponUpdate(BaseModel):
    """优惠券更新模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)  # 优惠券名称
    description: Optional[str] = Field(None, max_length=500)         # 优惠券描述
    coupon_type: Optional[CouponType] = None                         # 优惠券类型
    discount_type: Optional[PromotionType] = None                    # 折扣类型
    discount_value: Optional[float] = None                           # 折扣值
    minimum_purchase: Optional[float] = None                         # 最低购买金额要求
    maximum_discount: Optional[float] = None                         # 最大折扣金额
    valid_from: Optional[datetime] = None                            # 有效期开始时间
    valid_to: Optional[datetime] = None                              # 有效期结束时间
    usage_limit: Optional[int] = None                                # 总使用次数限制
    per_user_limit: Optional[int] = None                             # 每用户使用次数限制
    is_active: Optional[bool] = None                                 # 是否激活

    @field_validator('valid_to')
    @classmethod
    def validate_validity_period(cls, v, info):
        """验证有效期结束时间必须晚于开始时间"""
        valid_from = info.data.get('valid_from')
        if valid_from and v < valid_from:
            raise ValueError('有效期结束时间必须晚于开始时间')
        return v


class CouponResponse(BaseModel):
    """优惠券响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str                           # 优惠券ID
    merchant_id: str                  # 关联商家ID
    code: str                         # 优惠码
    name: str                         # 优惠券名称
    description: Optional[str]        # 优惠券描述
    coupon_type: CouponType           # 优惠券类型
    discount_type: PromotionType      # 折扣类型
    discount_value: float             # 折扣值
    minimum_purchase: Optional[float] # 最低购买金额要求
    maximum_discount: Optional[float] # 最大折扣金额
    valid_from: datetime              # 有效期开始时间
    valid_to: datetime                # 有效期结束时间
    usage_limit: Optional[int]        # 总使用次数限制
    per_user_limit: Optional[int]     # 每用户使用次数限制
    is_active: bool                   # 是否激活
    used_count: int = 0               # 已使用次数
    created_at: datetime              # 创建时间
    updated_at: datetime              # 更新时间


# -----------------------------
# 营销模型 - 广告
# -----------------------------

class AdvertisementCreate(BaseModel):
    """广告创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    merchant_id: str                                          # 关联商家ID
    title: str = Field(..., min_length=1, max_length=100)     # 广告标题
    description: Optional[str] = Field(None, max_length=500)  # 广告描述
    image_url: Optional[str] = None                           # 图片链接
    target_url: Optional[str] = None                          # 目标链接
    start_date: datetime                                      # 开始时间
    end_date: datetime                                        # 结束时间
    is_active: bool = True                                    # 是否激活
    priority: int = 0                                         # 优先级（数值越高越优先）

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """验证结束时间必须晚于开始时间"""
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class AdvertisementUpdate(BaseModel):
    """广告更新模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    title: Optional[str] = Field(None, min_length=1, max_length=100)  # 广告标题
    description: Optional[str] = Field(None, max_length=500)          # 广告描述
    image_url: Optional[str] = None                                   # 图片链接
    target_url: Optional[str] = None                                  # 目标链接
    start_date: Optional[datetime] = None                             # 开始时间
    end_date: Optional[datetime] = None                               # 结束时间
    is_active: Optional[bool] = None                                  # 是否激活
    priority: Optional[int] = None                                    # 优先级

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """验证结束时间必须晚于开始时间"""
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class AdvertisementResponse(BaseModel):
    """广告响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str                      # 广告ID
    merchant_id: str             # 关联商家ID
    title: str                   # 广告标题
    description: Optional[str]   # 广告描述
    image_url: Optional[str]     # 图片链接
    target_url: Optional[str]    # 目标链接
    start_date: datetime         # 开始时间
    end_date: datetime           # 结束时间
    is_active: bool              # 是否激活
    priority: int                # 优先级
    created_at: datetime         # 创建时间
    updated_at: datetime         # 更新时间


# -----------------------------
# 其他实用模型
# -----------------------------

class ReviewCreate(BaseModel):
    """评价创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    merchant_id: str                    # 商家ID
    rating: int = Field(..., ge=1, le=5) # 评分 (1-5星)
    comment: Optional[str] = Field(None, max_length=1000) # 评论内容
    user_id: str                        # 用户ID


class ReviewResponse(BaseModel):
    """评价响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str
    merchant_id: str
    user_id: str
    user_name: str                      # 用户名
    rating: int                         # 评分
    comment: Optional[str]              # 评论内容
    created_at: datetime                # 创建时间
    updated_at: datetime                # 更新时间


class StatisticsResponse(BaseModel):
    """统计数据响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    total_merchants: int                # 总商家数
    active_merchants: int               # 活跃商家数
    total_promotions: int               # 总促销数
    active_promotions: int              # 活跃促销数
    total_coupons: int                  # 总优惠券数
    active_coupons: int                 # 活跃优惠券数
    total_reviews: int                  # 总评价数
    average_rating: float               # 平均评分