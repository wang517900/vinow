商家系统7评价管理
"""
评价相关 Pydantic 模型定义

本模块定义了与商户评价相关的 Pydantic 模型，用于：
- 评价数据的输入验证
- API 接口的数据序列化与反序列化
- 不同业务场景下的数据结构定义
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ReviewBase(BaseModel):
    """
    评价基础模型
    
    定义评价的基本字段，作为其他评价模型的基础类
    """
    # 商户ID
    merchant_id: int
    
    # 用户ID
    user_id: int
    
    # 用户名称
    user_name: str
    
    # 用户头像URL（可选）
    user_avatar: Optional[str] = None
    
    # 评分（1-5星）
    rating: int
    
    # 评价内容（可选）
    content: Optional[str] = None
    
    # 评价图片URL列表（可选）
    images: Optional[List[str]] = None
    
    # 是否匿名评价，默认为False
    is_anonymous: bool = False

class ReviewCreate(ReviewBase):
    """
    创建评价请求模型
    
    用于创建新评价时的数据验证，继承自 ReviewBase
    目前没有额外字段，完全复用基础模型
    """
    pass

class ReviewUpdate(BaseModel):
    """
    更新评价请求模型
    
    用于更新评价状态时的数据验证
    """
    # 评价状态：active(正常)/hidden(隐藏)/deleted(已删除)
    status: Optional[str] = None

class ReviewInDB(ReviewBase):
    """
    数据库评价模型
    
    表示从数据库查询出的完整评价信息
    """
    # 启用 ORM 模式，允许从 ORM 对象创建 Pydantic 模型
    model_config = ConfigDict(from_attributes=True)
    
    # 评价ID
    id: int
    
    # 评价状态
    status: str
    
    # 创建时间
    created_at: datetime
    
    # 更新时间
    updated_at: datetime

class ReviewWithReply(ReviewInDB):
    """
    带回复信息的评价模型
    
    在基本评价信息基础上增加回复相关信息
    """
    # 是否有回复
    has_reply: bool = False
    
    # 回复内容（可选）
    reply_content: Optional[str] = None
    
    # 回复创建时间（可选）
    reply_created_at: Optional[datetime] = None

class ReviewListResponse(BaseModel):
    """
    评价列表响应模型
    
    定义获取评价列表接口的返回数据结构
    """
    # 请求是否成功
    success: bool = True
    
    # 返回的数据
    data: dict
    
    @classmethod
    def create_response(cls, reviews: List[ReviewWithReply], total: int, page: int, limit: int):
        """
        创建标准化的列表响应
        
        Args:
            reviews: 评价列表数据
            total: 总记录数
            page: 当前页码
            limit: 每页条数
            
        Returns:
            ReviewListResponse: 标准化的响应对象
        """
        return cls(
            data={
                "reviews": reviews,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
        )

class ReviewSummary(BaseModel):
    """
    评价汇总信息模型
    
    用于展示商户评价的关键统计数据
    """
    # 今日新增评价数
    today_reviews: int
    
    # 待回复评价数
    pending_replies: int
    
    # 平均评分
    average_rating: float
    
    # 回复率
    reply_rate: float
    
    # 周趋势（最近7天评分变化趋势）
    weekly_trend: float

class ReviewSummaryResponse(BaseModel):
    """
    评价汇总响应模型
    
    定义获取评价汇总信息接口的返回数据结构
    """
    # 请求是否成功
    success: bool = True
    
    # 返回的汇总数据
    data: ReviewSummary