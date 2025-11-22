# -*- coding: utf-8 -*-
"""商家系统 - merchant_service"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from supabase import Client
from app.models.merchant_models import (
    MerchantCreate, MerchantUpdate, MerchantResponse, MerchantStatus,
    BusinessCategory, MerchantSearchParams, MerchantListResponse,
    ReviewCreate, ReviewResponse
)

logger = logging.getLogger(__name__)

class MerchantService:
    """商家服务类（优化版 - 异常统一处理 / 查询优化 / 清晰结构）"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase

    # --------------------------------------------------------------
    # 公用方法
    # --------------------------------------------------------------
    def _now(self):
        """获取当前UTC时间的ISO格式字符串"""
        return datetime.utcnow().isoformat()

    def _clean_enum(self, value):
        """清理枚举值，提取实际值"""
        return value.value if hasattr(value, "value") else value

    def _check_owner(self, merchant_id: str, owner_id: str):
        """验证商家是否属于该用户"""
        try:
            # Pydantic V2语法：查询商家信息
            result = self.supabase.table("merchants")\
                .select("id, owner_id, status")\
                .eq("id", merchant_id)\
                .single()\
                .execute()

            # Pydantic V2语法：检查商家是否存在
            if not result.data:
                raise ValueError("商家不存在")

            # Pydantic V2语法：验证所有权
            if result.data["owner_id"] != owner_id:
                raise PermissionError("无权限操作该商家")

            return result.data
        except Exception as e:
            logger.error(f"[_check_owner] 验证商家所有权失败: {e}")
            raise

    # --------------------------------------------------------------
    # 创建商家
    # --------------------------------------------------------------
    def create_merchant(self, merchant_data: MerchantCreate, owner_id: str) -> MerchantResponse:
        """创建商家（含名称唯一验证）"""
        try:
            # Pydantic V2语法：检查商家名称是否已存在
            existing = self.supabase.table("merchants")\
                .select("id")\
                .eq("name", merchant_data.name)\
                .execute()

            # Pydantic V2语法：如果有重复名称则报错
            if existing.data:
                raise ValueError("商家名称已存在")

            # Pydantic V2语法：构建商家记录
            record = {
                "name": merchant_data.name,
                "description": merchant_data.description,
                "category": merchant_data.category.value,
                "address": merchant_data.address,
                "district": merchant_data.district,
                "province": merchant_data.province,
                "ward": merchant_data.ward,
                "latitude": merchant_data.latitude,
                "longitude": merchant_data.longitude,
                "phone": merchant_data.phone,
                "email": merchant_data.email,
                "website": merchant_data.website,
                "logo_url": merchant_data.logo_url,
                "banner_url": merchant_data.banner_url,
                "owner_id": owner_id,
                "status": MerchantStatus.PENDING.value,
                "created_at": self._now(),
                "updated_at": self._now(),
            }

            # Pydantic V2语法：插入商家记录
            result = self.supabase.table("merchants").insert(record).execute()

            # Pydantic V2语法：检查插入结果
            if not result.data:
                raise RuntimeError("创建商家失败")

            # Pydantic V2语法：格式化返回结果
            return self._format_merchant_response(result.data[0])

        except Exception as e:
            logger.error(f"[create_merchant] 创建商家失败: {e}")
            raise

    # --------------------------------------------------------------
    # 查询商家
    # --------------------------------------------------------------
    def get_merchant(self, merchant_id: str) -> Optional[MerchantResponse]:
        """根据ID获取商家信息"""
        try:
            # Pydantic V2语法：查询商家信息
            result = self.supabase.table("merchants")\
                .select("*")\
                .eq("id", merchant_id)\
                .single()\
                .execute()

            # Pydantic V2语法：如果没有找到商家则返回None
            if not result.data:
                return None

            # Pydantic V2语法：格式化返回结果
            return self._format_merchant_response(result.data)

        except Exception as e:
            logger.error(f"[get_merchant] 获取商家信息失败: {e}")
            raise

    # --------------------------------------------------------------
    # 更新商家
    # --------------------------------------------------------------
    def update_merchant(self, merchant_id: str, update_data: MerchantUpdate, owner_id: str) -> Optional[MerchantResponse]:
        """更新商家信息"""
        try:
            # Pydantic V2语法：验证商家所有权
            self._check_owner(merchant_id, owner_id)

            # Pydantic V2语法：使用model_dump()替代dict()
            update_fields = {
                k: self._clean_enum(v)
                for k, v in update_data.model_dump(exclude_unset=True).items()  # Pydantic V2使用model_dump()方法
            }
            update_fields["updated_at"] = self._now()

            # Pydantic V2语法：执行更新操作
            result = self.supabase.table("merchants")\
                .update(update_fields)\
                .eq("id", merchant_id)\
                .execute()

            # Pydantic V2语法：如果没有更新成功则返回None
            if not result.data:
                return None

            # Pydantic V2语法：格式化返回结果
            return self._format_merchant_response(result.data[0])

        except Exception as e:
            logger.error(f"[update_merchant] 更新商家失败: {e}")
            raise

    # --------------------------------------------------------------
    # 删除商家（软删除）
    # --------------------------------------------------------------
    def delete_merchant(self, merchant_id: str, owner_id: str) -> bool:
        """删除商家（软删除，设置为暂停状态）"""
        try:
            # Pydantic V2语法：验证商家所有权
            self._check_owner(merchant_id, owner_id)

            # Pydantic V2语法：执行软删除操作
            result = self.supabase.table("merchants")\
                .update({
                    "status": MerchantStatus.SUSPENDED.value,
                    "updated_at": self._now()
                })\
                .eq("id", merchant_id)\
                .execute()

            # Pydantic V2语法：返回布尔值表示操作是否成功
            return bool(result.data)

        except Exception as e:
            logger.error(f"[delete_merchant] 删除商家失败: {e}")
            raise

    # --------------------------------------------------------------
    # 商家列表（分页）
    # --------------------------------------------------------------
    def list_merchants(self, owner_id: str, page: int = 1, page_size: int = 20) -> MerchantListResponse:
        """获取用户的所有商家列表（分页）"""
        try:
            # Pydantic V2语法：计算起始位置
            start = (page - 1) * page_size

            # Pydantic V2语法：查询商家数据
            result = self.supabase.table("merchants")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .order("created_at", desc=True)\
                .range(start, start + page_size - 1)\
                .execute()

            # Pydantic V2语法：查询总数
            count_result = self.supabase.table("merchants")\
                .select("id", count="exact")\
                .eq("owner_id", owner_id)\
                .execute()
            
            # Pydantic V2语法：获取总数量
            total_count = count_result.count or 0

            # Pydantic V2语法：格式化商家数据
            merchants = [
                self._format_merchant_response(m)
                for m in result.data
            ]

            # Pydantic V2语法：返回列表响应
            return MerchantListResponse(
                merchants=merchants,
                total_count=total_count,
                page=page,
                page_size=page_size
            )

        except Exception as e:
            logger.error(f"[list_merchants] 获取商家列表失败: {e}")
            raise

    # --------------------------------------------------------------
    # 搜索商家
    # --------------------------------------------------------------
    def search_merchants(self, params: MerchantSearchParams) -> MerchantListResponse:
        """搜索商家"""
        try:
            # Pydantic V2语法：初始化查询
            query = self.supabase.table("merchants").select("*")

            # Pydantic V2语法：添加搜索条件
            if params.query:
                search = f"%{params.query}%"
                query = query.or_(f"name.ilike.{search},description.ilike.{search}")

            # Pydantic V2语法：添加分类筛选
            if params.category:
                query = query.eq("category", params.category.value)

            # Pydantic V2语法：添加地理位置筛选
            if params.latitude is not None and params.longitude is not None and params.radius is not None:
                # 这里可以实现基于地理位置的搜索逻辑
                # 由于Supabase的地理位置查询较为复杂，这里仅作注释说明
                pass

            # Pydantic V2语法：添加评分筛选
            if params.min_rating is not None:
                query = query.gte("average_rating", params.min_rating)

            # Pydantic V2语法：分页处理
            start = (params.page - 1) * params.page_size
            query = query.range(start, start + params.page_size - 1)

            # Pydantic V2语法：执行查询
            result = query.execute()

            # Pydantic V2语法：查询总数
            count_q = self.supabase.table("merchants").select("id", count="exact")
            if params.query:
                search = f"%{params.query}%"
                count_q = count_q.or_(f"name.ilike.{search},description.ilike.{search}")
            if params.category:
                count_q = count_q.eq("category", params.category.value)
            if params.min_rating is not None:
                count_q = count_q.gte("average_rating", params.min_rating)

            # Pydantic V2语法：获取总数
            total_result = count_q.execute()
            total_count = total_result.count or 0

            # Pydantic V2语法：格式化商家数据
            merchants = [
                self._format_merchant_response(m)
                for m in result.data
            ]

            # Pydantic V2语法：返回搜索结果
            return MerchantListResponse(
                merchants=merchants,
                total_count=total_count,
                page=params.page,
                page_size=params.page_size
            )

        except Exception as e:
            logger.error(f"[search_merchants] 搜索商家失败: {e}")
            raise

    # --------------------------------------------------------------
    # 营销相关功能
    # --------------------------------------------------------------
    
    def create_promotion(self, merchant_id: str, promotion_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """创建促销活动"""
        try:
            # Pydantic V2语法：验证商家所有权
            self._check_owner(merchant_id, owner_id)

            # Pydantic V2语法：构建促销记录
            record = {
                "merchant_id": merchant_id,
                "name": promotion_data["name"],
                "description": promotion_data.get("description"),
                "promotion_type": promotion_data["promotion_type"],
                "discount_value": promotion_data.get("discount_value"),
                "minimum_purchase": promotion_data.get("minimum_purchase"),
                "maximum_discount": promotion_data.get("maximum_discount"),
                "start_date": promotion_data["start_date"],
                "end_date": promotion_data["end_date"],
                "is_active": promotion_data.get("is_active", True),
                "status": "active",
                "created_at": self._now(),
                "updated_at": self._now(),
            }

            # Pydantic V2语法：插入促销记录
            result = self.supabase.table("promotions").insert(record).execute()

            # Pydantic V2语法：检查插入结果
            if not result.data:
                raise RuntimeError("创建促销活动失败")

            # Pydantic V2语法：返回创建的数据
            return result.data[0]

        except Exception as e:
            logger.error(f"[create_promotion] 创建促销活动失败: {e}")
            raise

    def create_coupon(self, merchant_id: str, coupon_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """创建优惠券"""
        try:
            # Pydantic V2语法：验证商家所有权
            self._check_owner(merchant_id, owner_id)

            # Pydantic V2语法：构建优惠券记录
            record = {
                "merchant_id": merchant_id,
                "code": coupon_data["code"],
                "name": coupon_data["name"],
                "description": coupon_data.get("description"),
                "coupon_type": coupon_data["coupon_type"],
                "discount_type": coupon_data["discount_type"],
                "discount_value": coupon_data["discount_value"],
                "minimum_purchase": coupon_data.get("minimum_purchase"),
                "maximum_discount": coupon_data.get("maximum_discount"),
                "valid_from": coupon_data["valid_from"],
                "valid_to": coupon_data["valid_to"],
                "usage_limit": coupon_data.get("usage_limit"),
                "per_user_limit": coupon_data.get("per_user_limit"),
                "is_active": coupon_data.get("is_active", True),
                "used_count": 0,
                "created_at": self._now(),
                "updated_at": self._now(),
            }

            # Pydantic V2语法：插入优惠券记录
            result = self.supabase.table("coupons").insert(record).execute()

            # Pydantic V2语法：检查插入结果
            if not result.data:
                raise RuntimeError("创建优惠券失败")

            # Pydantic V2语法：返回创建的数据
            return result.data[0]

        except Exception as e:
            logger.error(f"[create_coupon] 创建优惠券失败: {e}")
            raise

    def create_review(self, review_data: ReviewCreate) -> ReviewResponse:
        """创建商家评价"""
        try:
            # Pydantic V2语法：检查商家是否存在
            merchant = self.get_merchant(review_data.merchant_id)
            if not merchant:
                raise ValueError("商家不存在")

            # Pydantic V2语法：构建评价记录
            record = {
                "merchant_id": review_data.merchant_id,
                "user_id": review_data.user_id,
                "rating": review_data.rating,
                "comment": review_data.comment,
                "created_at": self._now(),
                "updated_at": self._now(),
            }

            # Pydantic V2语法：插入评价记录
            result = self.supabase.table("reviews").insert(record).execute()

            # Pydantic V2语法：检查插入结果
            if not result.data:
                raise RuntimeError("创建评价失败")

            # Pydantic V2语法：更新商家的平均评分
            self._update_merchant_rating(review_data.merchant_id)

            # Pydantic V2语法：格式化返回结果
            review = result.data[0]
            return ReviewResponse(
                id=review["id"],
                merchant_id=review["merchant_id"],
                user_id=review["user_id"],
                user_name="匿名用户",  # 实际应用中应从用户表获取用户名
                rating=review["rating"],
                comment=review["comment"],
                created_at=datetime.fromisoformat(review["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(review["updated_at"].replace("Z", "+00:00"))
            )

        except Exception as e:
            logger.error(f"[create_review] 创建评价失败: {e}")
            raise

    def _update_merchant_rating(self, merchant_id: str):
        """更新商家的平均评分"""
        try:
            # Pydantic V2语法：获取所有评价
            result = self.supabase.table("reviews")\
                .select("rating")\
                .eq("merchant_id", merchant_id)\
                .execute()
            
            # Pydantic V2语法：提取评分列表
            ratings = [r["rating"] for r in result.data]
            
            # Pydantic V2语法：计算平均评分
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                review_count = len(ratings)
            else:
                avg_rating = None
                review_count = 0

            # Pydantic V2语法：更新商家评分信息
            self.supabase.table("merchants")\
                .update({
                    "average_rating": avg_rating,
                    "review_count": review_count,
                    "updated_at": self._now()
                })\
                .eq("id", merchant_id)\
                .execute()

        except Exception as e:
            logger.error(f"[_update_merchant_rating] 更新商家评分失败: {e}")
            # 不抛出异常，因为这是辅助功能

    # --------------------------------------------------------------
    # 格式化返回
    # --------------------------------------------------------------
    def _format_merchant_response(self, data: Dict[str, Any]) -> MerchantResponse:
        """格式化商家响应数据"""
        try:
            # Pydantic V2语法：格式化商家响应数据
            return MerchantResponse(
                id=data["id"],
                name=data["name"],
                description=data.get("description"),
                category=BusinessCategory(data["category"]),
                address=data["address"],
                district=data.get("district"),
                province=data.get("province"),
                ward=data.get("ward"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                phone=data["phone"],
                email=data.get("email"),
                website=data.get("website"),
                logo_url=data.get("logo_url"),
                banner_url=data.get("banner_url"),
                status=MerchantStatus(data["status"]),
                owner_id=data["owner_id"],
                created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                average_rating=data.get("average_rating"),
                review_count=data.get("review_count", 0)
            )
        except Exception as e:
            logger.error(f"[_format_merchant_response] 格式化商家响应数据失败: {e}")
            raise