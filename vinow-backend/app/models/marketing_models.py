# -*- coding: utf-8 -*-
"""商家系统 - marketing_models"""

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
    ACTIVE = "active"        # 激活
    SUSPENDED = "suspended"  # 暂停
    REJECTED = "rejected"    # 拒绝


class BusinessCategory(str, Enum):
    """业务类别枚举"""
    RESTAURANT = "restaurant"      # 餐厅
    CAFE = "cafe"                  # 咖啡厅
    BEAUTY_SALON = "beauty_salon"  # 美容沙龙
    FITNESS = "fitness"            # 健身
    RETAIL = "retail"              # 零售
    ENTERTAINMENT = "entertainment"  # 娱乐
    HEALTHCARE = "healthcare"      # 医疗保健
    OTHER = "other"                # 其他


class DayOfWeek(str, Enum):
    """星期枚举"""
    MONDAY = "monday"       # 星期一
    TUESDAY = "tuesday"     # 星期二
    WEDNESDAY = "wednesday" # 星期三
    THURSDAY = "thursday"   # 星期四
    FRIDAY = "friday"       # 星期五
    SATURDAY = "saturday"   # 星期六
    SUNDAY = "sunday"       # 星期日


# -----------------------------
# 营业时间
# -----------------------------

class BusinessHours(BaseModel):
    """营业时间模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    day: DayOfWeek                    # 星期几
    open_time: Optional[str] = None   # 开门时间，HH:MM 格式
    close_time: Optional[str] = None  # 关门时间，HH:MM 格式
    is_closed: bool = False           # 是否休息

    @field_validator("open_time", "close_time")  # Pydantic V2 使用 field_validator 而不是 validator
    @classmethod
    def validate_time_format(cls, v):
        """验证时间格式是否正确"""
        if v is None:
            return v
        if not re.match(r"^\d{2}:\d{2}$", v):  # 必须是 HH:MM 格式
            raise ValueError("Time must be in HH:MM format")
        return v


# -----------------------------
# 商家创建
# -----------------------------

class MerchantCreate(BaseModel):
    """商家创建模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: str = Field(..., min_length=1, max_length=100)          # 商家名称，必填，长度1-100
    description: Optional[str] = Field(None, max_length=500)       # 描述，可选，最长500字符
    category: BusinessCategory                                     # 类别，必填

    # 地址结构更专业更适合越南
    address: str = Field(..., min_length=1, max_length=200)       # 地址，必填，长度1-200
    district: Optional[str] = None                                # 区县，可选
    province: Optional[str] = None                                # 省份，可选
    ward: Optional[str] = None                                    # 社区/街道，可选

    latitude: Optional[float] = Field(None, ge=-90, le=90)        # 纬度，范围-90到90
    longitude: Optional[float] = Field(None, ge=-180, le=180)     # 经度，范围-180到180

    phone: str                                                    # 电话号码，必填
    email: Optional[str] = None                                   # 邮箱，可选
    website: Optional[str] = None                                 # 网站，可选

    # 商家 logo 和 banner
    logo_url: Optional[str] = None                                # Logo URL，可选
    banner_url: Optional[str] = None                              # Banner URL，可选

    @field_validator('phone')  # Pydantic V2 使用 field_validator 而不是 validator
    @classmethod
    def validate_phone(cls, v):
        """验证越南手机号码格式"""
        pattern = r'^(\+84|84|0)(3|5|7|8|9)([0-9]{8})$'
        if not re.match(pattern, v.replace(" ", "")):
            raise ValueError("Invalid Vietnamese phone number")
        return v

    @field_validator('email')  # Pydantic V2 使用 field_validator 而不是 validator
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v is None:
            return v
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v


# -----------------------------
# 商家更新
# -----------------------------

class MerchantUpdate(BaseModel):
    """商家更新模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)   # 名称，可选
    description: Optional[str] = Field(None, max_length=500)           # 描述，可选
    category: Optional[BusinessCategory] = None                       # 类别，可选
    address: Optional[str] = None                                     # 地址，可选
    district: Optional[str] = None                                    # 区县，可选
    province: Optional[str] = None                                    # 省份，可选
    ward: Optional[str] = None                                        # 社区/街道，可选
    latitude: Optional[float] = Field(None, ge=-90, le=90)            # 纬度，可选
    longitude: Optional[float] = Field(None, ge=-180, le=180)         # 经度，可选

    phone: Optional[str] = None                                       # 电话，可选
    email: Optional[str] = None                                       # 邮箱，可选
    website: Optional[str] = None                                     # 网站，可选
    logo_url: Optional[str] = None                                    # Logo URL，可选
    banner_url: Optional[str] = None                                  # Banner URL，可选

    status: Optional[MerchantStatus] = None                           # 状态，可选

    @field_validator('phone')  # Pydantic V2 使用 field_validator 而不是 validator
    @classmethod
    def validate_phone(cls, v):
        """验证越南手机号码格式"""
        if v is None:
            return v
        pattern = r'^(\+84|84|0)(3|5|7|8|9)([0-9]{8})$'
        if not re.match(pattern, v.replace(" ", "")):
            raise ValueError("Invalid Vietnamese phone number")
        return v

    @field_validator('email')  # Pydantic V2 使用 field_validator 而不是 validator
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式"""
        if v is None:
            return v
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v


# -----------------------------
# 商家响应模型
# -----------------------------

class MerchantResponse(BaseModel):
    """商家响应模型"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2 配置方式
    
    id: str                          # ID
    name: str                        # 名称
    description: Optional[str]       # 描述
    category: BusinessCategory       # 类别
    address: str                     # 地址
    district: Optional[str]          # 区县
    province: Optional[str]          # 省份
    ward: Optional[str]              # 社区/街道

    latitude: Optional[float]        # 纬度
    longitude: Optional[float]       # 经度

    phone: str                       # 电话
    email: Optional[str]             # 邮箱
    website: Optional[str]           # 网站

    logo_url: Optional[str]          # Logo URL
    banner_url: Optional[str]        # Banner URL

    status: MerchantStatus           # 状态
    owner_id: str                    # 所有者ID

    created_at: datetime             # 创建时间
    updated_at: datetime             # 更新时间

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
# 营业时间
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
    
    query: Optional[str] = None              # 搜索关键词
    category: Optional[BusinessCategory] = None  # 类别筛选

    latitude: Optional[float] = None         # 纬度
    longitude: Optional[float] = None        # 经度
    radius: Optional[float] = None           # 半径(km)

    min_rating: Optional[float] = None       # 最低评分
    is_open_now: Optional[bool] = None       # 是否当前营业

    sort_by: Optional[str] = Field(
        default="distance", 
        description="distance | rating | created_at"  # 排序方式
    )

    page: int = 1        # 页码，默认第1页
    page_size: int = 20  # 每页大小，默认20条


# -----------------------------
# 促销活动模型（占位符）
# -----------------------------

class Promotion:
    """
    促销活动模型
    用于管理各种促销活动，如打折、满减等
    """
    __tablename__ = 'promotions'  # 数据库表名
    
    def __init__(self):
        """初始化方法（占位符）"""
        # id = Column(Integer, primary_key=True, autoincrement=True)
        # name = Column(String(255), nullable=False, comment="促销活动名称")
        # description = Column(Text, comment="活动描述")
        # start_time = Column(DateTime, nullable=False, comment="开始时间")
        # end_time = Column(DateTime, nullable=False, comment="结束时间")
        # discount_type = Column(String(50), comment="折扣类型：percentage百分比/fixed固定金额")
        # discount_value = Column(Float, comment="折扣值")
        # is_active = Column(Boolean, default=True, comment="是否启用")
        # created_at = Column(DateTime, default=datetime.now)
        # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
        pass


# -----------------------------
# 优惠券模型（占位符）
# -----------------------------

class Coupon:
    """
    优惠券模型
    用于管理发放给用户的优惠券
    """
    __tablename__ = 'coupons'  # 数据库表名
    
    def __init__(self):
        """初始化方法（占位符）"""
        # id = Column(Integer, primary_key=True, autoincrement=True)
        # code = Column(String(100), unique=True, nullable=False, comment="优惠券代码")
        # name = Column(String(255), nullable=False, comment="优惠券名称")
        # description = Column(Text, comment="优惠券描述")
        # discount_type = Column(String(50), comment="折扣类型：percentage百分比/fixed固定金额")
        # discount_value = Column(Float, comment="折扣值")
        # min_purchase_amount = Column(Float, default=0.0, comment="最低消费金额")
        # max_discount_amount = Column(Float, comment="最大折扣金额")
        # total_quantity = Column(Integer, comment="总数量")
        # issued_quantity = Column(Integer, default=0, comment="已发放数量")
        # used_quantity = Column(Integer, default=0, comment="已使用数量")
        # valid_from = Column(DateTime, comment="有效期开始时间")
        # valid_to = Column(DateTime, comment="有效期结束时间")
        # is_active = Column(Boolean, default=True, comment="是否有效")
        # created_at = Column(DateTime, default=datetime.now)
        # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
        pass


# -----------------------------
# 营销活动模型（占位符）
# -----------------------------

class MarketingCampaign:
    """
    营销活动模型
    用于管理整体营销活动，可包含多个促销和优惠券
    """
    __tablename__ = 'marketing_campaigns'  # 数据库表名
    
    def __init__(self):
        """初始化方法（占位符）"""
        # id = Column(Integer, primary_key=True, autoincrement=True)
        # name = Column(String(255), nullable=False, comment="营销活动名称")
        # description = Column(Text, comment="活动描述")
        # start_date = Column(DateTime, nullable=False, comment="开始日期")
        # end_date = Column(DateTime, nullable=False, comment="结束日期")
        # budget = Column(Float, comment="预算")
        # status = Column(String(50), default='draft', comment="状态：draft草稿/active进行中/completed已完成")
        # created_at = Column(DateTime, default=datetime.now)
        # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
        pass


# -----------------------------
# 客户分群模型（占位符）
# -----------------------------

class CustomerSegment:
    """
    客户分群模型
    用于定义不同类型的客户群体
    """
    __tablename__ = 'customer_segments'  # 数据库表名
    
    def __init__(self):
        """初始化方法（占位符）"""
        # id = Column(Integer, primary_key=True, autoincrement=True)
        # name = Column(String(255), nullable=False, comment="分群名称")
        # criteria = Column(Text, comment="筛选条件(JSON格式)")
        # description = Column(Text, comment="分群描述")
        # customer_count = Column(Integer, default=0, comment="客户数量")
        # is_active = Column(Boolean, default=True, comment="是否启用")
        # created_at = Column(DateTime, default=datetime.now)
        # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
        pass