# -*- coding: utf-8 -*-
"""商家系统 - product_service"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from supabase import Client
from app.models.product_models import (
    ProductCreate, ProductUpdate, ProductResponse, ProductStatus,
    ProductType, PriceType, ProductVariant, ProductSearchParams,
    ProductListResponse, BulkUpdateStatus, StockUpdate, BulkStockUpdate,
    ProductCategory, ProductTag
)

logger = logging.getLogger(__name__)

class ProductService:
    """商品服务类"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    async def create_product(self, product_data: ProductCreate, owner_id: str) -> ProductResponse:
        """创建商品"""
        try:
            # 验证商家所有权
            merchant = self.supabase.table("merchants")\
                .select("id, owner_id")\
                .eq("id", product_data.merchant_id)\
                .execute()
            
            if not merchant.data:
                raise ValueError("商家不存在")
            
            if merchant.data[0]["owner_id"] != owner_id:
                raise PermissionError("无权为该商家创建商品")
            
            # 检查商品名称是否重复（同一商家内）
            existing_product = self.supabase.table("products")\
                .select("id")\
                .eq("name", product_data.name)\
                .eq("merchant_id", product_data.merchant_id)\
                .execute()
            
            if existing_product.data:
                raise ValueError("该商家下已存在相同名称的商品")
            
            # 检查分类是否存在
            if product_data.category_ids:
                categories = self.supabase.table("product_categories")\
                    .select("id")\
                    .in_("id", product_data.category_ids)\
                    .execute()
                
                if len(categories.data) != len(product_data.category_ids):
                    raise ValueError("部分分类不存在")
            
            # 检查标签是否存在
            if product_data.tag_ids:
                tags = self.supabase.table("product_tags")\
                    .select("id")\
                    .in_("id", product_data.tag_ids)\
                    .execute()
                
                if len(tags.data) != len(product_data.tag_ids):
                    raise ValueError("部分标签不存在")
            
            # 创建商品记录
            product_record = {
                "name": product_data.name,
                "description": product_data.description,
                "short_description": product_data.short_description,
                "product_type": product_data.product_type.value,
                "price_type": product_data.price_type.value,
                "merchant_id": product_data.merchant_id,
                "status": ProductStatus.DRAFT.value,
                "is_featured": product_data.is_featured,
                "is_available_online": product_data.is_available_online,
                "requires_shipping": product_data.requires_shipping,
                "is_taxable": product_data.is_taxable,
                "seo_title": product_data.seo_title,
                "seo_description": product_data.seo_description,
                "slug": product_data.slug,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入商品
            product_result = self.supabase.table("products").insert(product_record).execute()
            
            if not product_result.data:
                raise Exception("创建商品失败")
            
            product_id = product_result.data[0]["id"]
            
            # 插入商品规格
            variants_data = []
            for variant in product_data.variants:
                variant_record = {
                    "product_id": product_id,
                    "sku": variant.sku,
                    "name": variant.name,
                    "price": float(variant.price),
                    "original_price": float(variant.original_price) if variant.original_price else None,
                    "cost_price": float(variant.cost_price) if variant.cost_price else None,
                    "stock_quantity": variant.stock_quantity,
                    "stock_threshold": variant.stock_threshold,
                    "weight": variant.weight,
                    "dimensions": variant.dimensions,
                    "barcode": variant.barcode,
                    "is_default": variant.is_default,
                    "sort_order": variant.sort_order,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                variants_data.append(variant_record)
            
            variants_result = self.supabase.table("product_variants").insert(variants_data).execute()
            
            if not variants_result.data:
                # 回滚商品创建
                self.supabase.table("products").delete().eq("id", product_id).execute()
                raise Exception("创建商品规格失败")
            
            # 关联分类
            if product_data.category_ids:
                category_relations = [
                    {"product_id": product_id, "category_id": category_id}
                    for category_id in product_data.category_ids
                ]
                self.supabase.table("product_category_relations").insert(category_relations).execute()
            
            # 关联标签
            if product_data.tag_ids:
                tag_relations = [
                    {"product_id": product_id, "tag_id": tag_id}
                    for tag_id in product_data.tag_ids
                ]
                self.supabase.table("product_tag_relations").insert(tag_relations).execute()
            
            return await self._get_product_with_details(product_id)
            
        except Exception as e:
            logger.error(f"创建商品失败: {str(e)}")
            raise
    
    async def get_product(self, product_id: str) -> Optional[ProductResponse]:
        """获取商品详情"""
        try:
            return await self._get_product_with_details(product_id)
        except Exception as e:
            logger.error(f"获取商品失败: {str(e)}")
            raise
    
    async def update_product(self, product_id: str, update_data: ProductUpdate, owner_id: str) -> Optional[ProductResponse]:
        """更新商品信息"""
        try:
            # 验证商品所有权
            product = self.supabase.table("products")\
                .select("id, merchant_id")\
                .eq("id", product_id)\
                .execute()
            
            if not product.data:
                return None
            
            merchant_id = product.data[0]["merchant_id"]
            
            # 验证商家所有权
            merchant = self.supabase.table("merchants")\
                .select("owner_id")\
                .eq("id", merchant_id)\
                .execute()
            
            if not merchant.data or merchant.data[0]["owner_id"] != owner_id:
                raise PermissionError("无权更新该商品")
            
            # 构建更新数据
            update_fields = {}
            for field, value in update_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    if hasattr(value, 'value'):  # 处理枚举类型
                        update_fields[field] = value.value
                    else:
                        update_fields[field] = value
            
            # 如果是名称更新，检查重复
            if 'name' in update_fields:
                existing_product = self.supabase.table("products")\
                    .select("id")\
                    .eq("name", update_fields['name'])\
                    .eq("merchant_id", merchant_id)\
                    .neq("id", product_id)\
                    .execute()
                
                if existing_product.data:
                    raise ValueError("该商家下已存在相同名称的商品")
            
            update_fields["updated_at"] = datetime.utcnow().isoformat()
            
            # 执行更新
            result = self.supabase.table("products")\
                .update(update_fields)\
                .eq("id", product_id)\
                .execute()
            
            if not result.data:
                return None
            
            # 更新分类关联
            if update_data.category_ids is not None:
                # 删除旧关联
                self.supabase.table("product_category_relations")\
                    .delete()\
                    .eq("product_id", product_id)\
                    .execute()
                
                # 创建新关联
                if update_data.category_ids:
                    category_relations = [
                        {"product_id": product_id, "category_id": category_id}
                        for category_id in update_data.category_ids
                    ]
                    self.supabase.table("product_category_relations").insert(category_relations).execute()
            
            # 更新标签关联
            if update_data.tag_ids is not None:
                # 删除旧关联
                self.supabase.table("product_tag_relations")\
                    .delete()\
                    .eq("product_id", product_id)\
                    .execute()
                
                # 创建新关联
                if update_data.tag_ids:
                    tag_relations = [
                        {"product_id": product_id, "tag_id": tag_id}
                        for tag_id in update_data.tag_ids
                    ]
                    self.supabase.table("product_tag_relations").insert(tag_relations).execute()
            
            return await self._get_product_with_details(product_id)
            
        except Exception as e:
            logger.error(f"更新商品失败: {str(e)}")
            raise
    
    async def delete_product(self, product_id: str, owner_id: str) -> bool:
        """删除商品（软删除）"""
        try:
            # 验证商品所有权
            product = self.supabase.table("products")\
                .select("id, merchant_id")\
                .eq("id", product_id)\
                .execute()
            
            if not product.data:
                return False
            
            merchant_id = product.data[0]["merchant_id"]
            
            merchant = self.supabase.table("merchants")\
                .select("owner_id")\
                .eq("id", merchant_id)\
                .execute()
            
            if not merchant.data or merchant.data[0]["owner_id"] != owner_id:
                raise PermissionError("无权删除该商品")
            
            # 软删除：更新状态为 deleted
            result = self.supabase.table("products")\
                .update({
                    "status": ProductStatus.DELETED.value,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", product_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"删除商品失败: {str(e)}")
            raise
    
    async def list_products(self, merchant_id: str, page: int = 1, page_size: int = 20) -> ProductListResponse:
        """获取商家的商品列表"""
        try:
            # 计算分页
            start_index = (page - 1) * page_size
            
            # 查询商品列表
            result = self.supabase.table("products")\
                .select("*")\
                .eq("merchant_id", merchant_id)\
                .neq("status", ProductStatus.DELETED.value)\
                .order("created_at", desc=True)\
                .range(start_index, start_index + page_size - 1)\
                .execute()
            
            # 查询总数
            count_result = self.supabase.table("products")\
                .select("id", count="exact")\
                .eq("merchant_id", merchant_id)\
                .neq("status", ProductStatus.DELETED.value)\
                .execute()
            
            total_count = count_result.count or 0
            total_pages = (total_count + page_size - 1) // page_size
            
            # 获取商品详情
            products = []
            for product_data in result.data:
                product_detail = await self._get_product_with_details(product_data["id"])
                if product_detail:
                    products.append(product_detail)
            
            return ProductListResponse(
                products=products,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            raise
    
    async def search_products(self, search_params: ProductSearchParams) -> ProductListResponse:
        """搜索商品"""
        try:
            query = self.supabase.table("products").select("*")
            
            # 只搜索非删除状态的商品
            query = query.neq("status", ProductStatus.DELETED.value)
            
            # 应用搜索条件
            if search_params.query:
                query = query.or_(f"name.ilike.%{search_params.query}%,description.ilike.%{search_params.query}%,short_description.ilike.%{search_params.query}%")
            
            if search_params.merchant_id:
                query = query.eq("merchant_id", search_params.merchant_id)
            
            if search_params.category_id:
                # 通过关联表查询指定分类的商品
                product_ids_result = self.supabase.table("product_category_relations")\
                    .select("product_id")\
                    .eq("category_id", search_params.category_id)\
                    .execute()
                
                if product_ids_result.data:
                    product_ids = [item["product_id"] for item in product_ids_result.data]
                    query = query.in_("id", product_ids)
                else:
                    # 如果没有找到关联商品，则返回空结果
                    query = query.eq("id", "0")  # 不存在的ID，确保返回空结果
            
            if search_params.product_type:
                query = query.eq("product_type", search_params.product_type.value)
            
            if search_params.status:
                query = query.eq("status", search_params.status.value)
            
            if search_params.is_featured is not None:
                query = query.eq("is_featured", search_params.is_featured)
            
            # 价格筛选
            if search_params.min_price is not None:
                # 注意：这里需要先获取商品详情才能准确筛选价格
                pass  # 简化处理，在实际应用中可能需要更复杂的查询
            
            if search_params.max_price is not None:
                # 注意：这里需要先获取商品详情才能准确筛选价格
                pass  # 简化处理，在实际应用中可能需要更复杂的查询
            
            # 库存筛选
            if search_params.in_stock_only:
                # 注意：这里需要先获取商品详情才能准确筛选库存
                pass  # 简化处理，在实际应用中可能需要更复杂的查询
            
            # 排序
            sort_order = "desc" if search_params.sort_order == "desc" else "asc"
            query = query.order(search_params.sort_by, desc=(sort_order == "desc"))
            
            # 分页
            start_index = (search_params.page - 1) * search_params.page_size
            query = query.range(start_index, start_index + search_params.page_size - 1)
            
            result = query.execute()
            
            # 查询总数
            count_query = self.supabase.table("products").select("id", count="exact")\
                .neq("status", ProductStatus.DELETED.value)
            
            if search_params.query:
                count_query = count_query.or_(f"name.ilike.%{search_params.query}%,description.ilike.%{search_params.query}%,short_description.ilike.%{search_params.query}%")
            
            if search_params.merchant_id:
                count_query = count_query.eq("merchant_id", search_params.merchant_id)
            
            if search_params.category_id:
                if product_ids_result.data:
                    count_query = count_query.in_("id", product_ids)
                else:
                    count_query = count_query.eq("id", "0")  # 不存在的ID
            
            if search_params.product_type:
                count_query = count_query.eq("product_type", search_params.product_type.value)
            
            if search_params.status:
                count_query = count_query.eq("status", search_params.status.value)
            
            if search_params.is_featured is not None:
                count_query = count_query.eq("is_featured", search_params.is_featured)
            
            count_result = count_query.execute()
            total_count = count_result.count or 0
            total_pages = (total_count + search_params.page_size - 1) // search_params.page_size
            
            # 获取商品详情
            products = []
            for product_data in result.data:
                product_detail = await self._get_product_with_details(product_data["id"])
                if product_detail:
                    # 进一步筛选（如价格、库存等）
                    if search_params.min_price is not None and product_detail.price < search_params.min_price:
                        continue
                    if search_params.max_price is not None and product_detail.price > search_params.max_price:
                        continue
                    if search_params.in_stock_only and product_detail.total_stock <= 0:
                        continue
                    products.append(product_detail)
            
            return ProductListResponse(
                products=products,
                total_count=total_count,
                page=search_params.page,
                page_size=search_params.page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"搜索商品失败: {str(e)}")
            raise
    
    async def bulk_update_status(self, update_data: BulkUpdateStatus, owner_id: str) -> bool:
        """批量更新商品状态"""
        try:
            # 验证商品所有权
            products = self.supabase.table("products")\
                .select("id, merchant_id")\
                .in_("id", update_data.product_ids)\
                .execute()
            
            if not products.data:
                return False
            
            # 获取所有涉及的商家ID
            merchant_ids = list(set([p["merchant_id"] for p in products.data]))
            
            # 验证用户对这些商家的所有权
            merchants = self.supabase.table("merchants")\
                .select("id, owner_id")\
                .in_("id", merchant_ids)\
                .execute()
            
            merchant_owners = {m["id"]: m["owner_id"] for m in merchants.data}
            
            for product in products.data:
                if merchant_owners.get(product["merchant_id"]) != owner_id:
                    raise PermissionError(f"无权更新商品 {product['id']}")
            
            # 批量更新状态
            result = self.supabase.table("products")\
                .update({
                    "status": update_data.status.value,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .in_("id", update_data.product_ids)\
                .execute()
            
            # 如果状态变为active，记录上架时间
            if update_data.status == ProductStatus.ACTIVE:
                # 获取当前时间作为上架时间
                published_time = datetime.utcnow().isoformat()
                
                # 为所有状态变为active的商品设置上架时间（仅对之前未上架的商品）
                for product_id in update_data.product_ids:
                    product_check = self.supabase.table("products")\
                        .select("published_at")\
                        .eq("id", product_id)\
                        .execute()
                    
                    if product_check.data and not product_check.data[0].get("published_at"):
                        self.supabase.table("products")\
                            .update({
                                "published_at": published_time
                            })\
                            .eq("id", product_id)\
                            .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"批量更新商品状态失败: {str(e)}")
            raise
    
    async def update_stock(self, product_id: str, stock_updates: BulkStockUpdate, owner_id: str) -> bool:
        """更新商品库存"""
        try:
            # 验证商品所有权
            product = self.supabase.table("products")\
                .select("id, merchant_id")\
                .eq("id", product_id)\
                .execute()
            
            if not product.data:
                return False
            
            merchant_id = product.data[0]["merchant_id"]
            
            merchant = self.supabase.table("merchants")\
                .select("owner_id")\
                .eq("id", merchant_id)\
                .execute()
            
            if not merchant.data or merchant.data[0]["owner_id"] != owner_id:
                raise PermissionError("无权更新该商品库存")
            
            # 获取现有规格
            variants = self.supabase.table("product_variants")\
                .select("sku, stock_quantity")\
                .eq("product_id", product_id)\
                .execute()
            
            variant_stock = {v["sku"]: v["stock_quantity"] for v in variants.data}
            
            # 执行库存更新
            for update in stock_updates.updates:
                if update.variant_sku not in variant_stock:
                    raise ValueError(f"规格SKU不存在: {update.variant_sku}")
                
                current_stock = variant_stock[update.variant_sku]
                new_stock = current_stock
                
                if update.operation == "set":
                    new_stock = update.quantity
                elif update.operation == "increment":
                    new_stock = current_stock + update.quantity
                elif update.operation == "decrement":
                    new_stock = current_stock - update.quantity
                else:
                    raise ValueError(f"不支持的操作类型: {update.operation}")
                
                if new_stock < 0:
                    raise ValueError(f"库存不能为负数: {update.variant_sku}")
                
                # 更新库存
                self.supabase.table("product_variants")\
                    .update({
                        "stock_quantity": new_stock,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("sku", update.variant_sku)\
                    .eq("product_id", product_id)\
                    .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"更新商品库存失败: {str(e)}")
            raise
    
    async def _get_product_with_details(self, product_id: str) -> Optional[ProductResponse]:
        """获取商品完整详情"""
        try:
            # 获取商品基础信息
            product_result = self.supabase.table("products").select("*").eq("id", product_id).execute()
            
            if not product_result.data:
                return None
            
            product_data = product_result.data[0]
            
            # 获取商品规格
            variants_result = self.supabase.table("product_variants")\
                .select("*")\
                .eq("product_id", product_id)\
                .order("sort_order")\
                .execute()
            
            # 计算总库存和库存预警
            total_stock = sum(v["stock_quantity"] for v in variants_result.data)
            low_stock_alert = any(
                v["stock_quantity"] <= v["stock_threshold"] 
                for v in variants_result.data 
                if v["stock_threshold"] > 0
            )
            
            # 获取默认规格的价格信息
            default_variant = next((v for v in variants_result.data if v["is_default"]), None)
            if not default_variant:
                default_variant = variants_result.data[0] if variants_result.data else None
            
            price = Decimal(str(default_variant["price"])) if default_variant else Decimal("0")
            original_price = Decimal(str(default_variant["original_price"])) if default_variant and default_variant["original_price"] else None
            
            # 获取分类信息
            # 首先获取商品的分类关联
            category_relations_result = self.supabase.table("product_category_relations")\
                .select("category_id")\
                .eq("product_id", product_id)\
                .execute()
            
            category_ids = [rel["category_id"] for rel in category_relations_result.data] if category_relations_result.data else []
            
            categories = []
            if category_ids:
                categories_result = self.supabase.table("product_categories")\
                    .select("*")\
                    .in_("id", category_ids)\
                    .execute()
                
                categories = [
                    ProductCategory(
                        id=cat["id"],
                        name=cat["name"],
                        parent_id=cat.get("parent_id"),
                        level=cat.get("level", 1),
                        sort_order=cat.get("sort_order", 0),
                        is_active=cat.get("is_active", True)
                    )
                    for cat in categories_result.data
                ]
            
            # 获取标签信息
            # 首先获取商品的标签关联
            tag_relations_result = self.supabase.table("product_tag_relations")\
                .select("tag_id")\
                .eq("product_id", product_id)\
                .execute()
            
            tag_ids = [rel["tag_id"] for rel in tag_relations_result.data] if tag_relations_result.data else []
            
            tags = []
            if tag_ids:
                tags_result = self.supabase.table("product_tags")\
                    .select("*")\
                    .in_("id", tag_ids)\
                    .execute()
                
                tags = [
                    ProductTag(
                        id=tag["id"],
                        name=tag["name"],
                        color=tag.get("color"),
                        is_active=tag.get("is_active", True)
                    )
                    for tag in tags_result.data
                ]
            
            # 获取统计信息（评价相关）
            reviews_result = self.supabase.table("product_reviews")\
                .select("rating")\
                .eq("product_id", product_id)\
                .execute()
            
            ratings = [review["rating"] for review in reviews_result.data] if reviews_result.data else []
            average_rating = sum(ratings) / len(ratings) if ratings else None
            review_count = len(ratings)
            
            # 处理日期格式
            created_at = product_data["created_at"]
            updated_at = product_data["updated_at"]
            published_at = product_data.get("published_at")
            
            # 确保日期格式正确
            if isinstance(created_at, str):
                # 处理可能的日期格式
                if created_at.endswith('Z'):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_at = datetime.fromisoformat(created_at)
            
            if isinstance(updated_at, str):
                if updated_at.endswith('Z'):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                else:
                    updated_at = datetime.fromisoformat(updated_at)
            
            if published_at and isinstance(published_at, str):
                if published_at.endswith('Z'):
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    published_at = datetime.fromisoformat(published_at)
            
            return ProductResponse(
                id=product_data["id"],
                name=product_data["name"],
                description=product_data.get("description"),
                short_description=product_data.get("short_description"),
                product_type=ProductType(product_data["product_type"]),
                price_type=PriceType(product_data["price_type"]),
                status=ProductStatus(product_data["status"]),
                merchant_id=product_data["merchant_id"],
                price=price,
                original_price=original_price,
                total_stock=total_stock,
                low_stock_alert=low_stock_alert,
                categories=categories,
                tags=tags,
                is_featured=product_data.get("is_featured", False),
                is_available_online=product_data.get("is_available_online", True),
                requires_shipping=product_data.get("requires_shipping", True),
                is_taxable=product_data.get("is_taxable", True),
                seo_title=product_data.get("seo_title"),
                seo_description=product_data.get("seo_description"),
                slug=product_data.get("slug"),
                view_count=product_data.get("view_count", 0),
                sale_count=product_data.get("sale_count", 0),
                average_rating=average_rating,
                review_count=review_count,
                created_at=created_at,
                updated_at=updated_at,
                published_at=published_at
            )
            
        except Exception as e:
            logger.error(f"获取商品详情失败: {str(e)}")
            return None