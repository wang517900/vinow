商户系统6财务中心
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging
import uuid

from app.database.supabase_client import db
from app.models.finance import (
    ReconciliationLog, ReconciliationStatus, ReconciliationResult,
    PaginatedResponse
)
from app.schemas.finance import ReconciliationHistoryParams
from app.core.exceptions import ReconciliationException

logger = logging.getLogger(__name__)


class ReconciliationService:
    """对账服务"""
    
    async def run_reconciliation(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date,
        force_reconcile: bool = False
    ) -> Optional[ReconciliationResult]:
        """执行对账"""
        try:
            logger.info(f"开始执行对账任务: 商户={merchant_id}, 日期范围={start_date}至{end_date}")
            
            # 检查是否已有对账记录
            if not force_reconcile:
                existing_log = await self._get_existing_reconciliation(
                    merchant_id, start_date, end_date
                )
                if existing_log:
                    logger.info(f"对账记录已存在: {existing_log.id}")
                    return await self._format_reconciliation_result(existing_log)
            
            # 获取平台数据
            platform_data = await self._get_platform_transactions(merchant_id, start_date, end_date)
            
            # 获取银行数据
            bank_data = await self._get_bank_transactions(merchant_id, start_date, end_date)
            
            # 执行对账比对
            reconciliation_result = await self._compare_transactions(
                platform_data, bank_data, merchant_id, start_date, end_date
            )
            
            # 保存对账记录
            reconciliation_log = await self._save_reconciliation_log(reconciliation_result)
            
            logger.info(f"对账完成: {reconciliation_log.id}")
            return await self._format_reconciliation_result(reconciliation_log)
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"执行对账失败: {str(e)}", exc_info=True)
            raise ReconciliationException("执行对账失败")
    
    async def get_reconciliation_history(
        self, 
        merchant_id: str,
        params: ReconciliationHistoryParams
    ) -> PaginatedResponse[ReconciliationResult]:
        """获取对账历史"""
        try:
            logger.info(f"获取商户 {merchant_id} 的对账历史记录")
            
            # 验证分页参数
            if params.limit > 100:
                raise ReconciliationException("单页查询数量不能超过100条")
            
            if params.limit <= 0 or params.offset < 0:
                raise ReconciliationException("分页参数无效")
            
            filters = {"merchant_id": merchant_id}
            
            # 添加日期范围过滤
            if params.start_date and params.end_date:
                filters["reconciliation_date"] = {
                    "gte": params.start_date.isoformat(),
                    "lte": params.end_date.isoformat()
                }
            
            # 添加状态过滤
            if params.status:
                filters["status"] = params.status.value
            
            logs = await db.execute_query(
                "finances_reconciliation_logs",
                filters=filters,
                order_by="reconciliation_date.desc",
                limit=params.limit,
                offset=params.offset
            )
            
            results = []
            for log in logs:
                results.append(await self._format_reconciliation_result(ReconciliationLog(**log)))
            
            # 获取总数
            total = await self._get_reconciliation_count(filters)
            
            logger.debug(f"成功获取到 {len(results)} 条对账历史记录")
            
            return PaginatedResponse.create(
                items=results,
                total=total,
                page=(params.offset // params.limit) + 1 if params.limit > 0 else 1,
                page_size=params.limit
            )
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"获取对账历史失败: {str(e)}", exc_info=True)
            raise ReconciliationException("获取对账历史失败")
    
    async def get_reconciliation_results(
        self, 
        merchant_id: str,
        reconciliation_id: str = None
    ) -> List[ReconciliationResult]:
        """获取对账结果"""
        try:
            logger.info(f"获取商户 {merchant_id} 的对账结果")
            
            filters = {"merchant_id": merchant_id}
            if reconciliation_id:
                filters["id"] = reconciliation_id
            
            logs = await db.execute_query(
                "finances_reconciliation_logs",
                filters=filters,
                order_by="reconciliation_date.desc",
                limit=10
            )
            
            results = []
            for log in logs:
                results.append(await self._format_reconciliation_result(ReconciliationLog(**log)))
            
            logger.debug(f"成功获取到 {len(results)} 条对账结果")
            
            return results
            
        except Exception as e:
            logger.error(f"获取对账结果失败: {str(e)}", exc_info=True)
            raise ReconciliationException("获取对账结果失败")
    
    async def submit_dispute(
        self,
        merchant_id: str,
        reconciliation_id: str,
        order_ids: List[str],
        dispute_reason: str,
        evidence: List[str] = None
    ) -> bool:
        """提交争议申请"""
        try:
            logger.info(f"商户 {merchant_id} 提交争议申请，对账ID: {reconciliation_id}")
            
            # 验证对账记录
            reconciliation_log = await self._get_reconciliation_log(reconciliation_id, merchant_id)
            if not reconciliation_log:
                raise ReconciliationException("对账记录不存在")
            
            if reconciliation_log.status != ReconciliationStatus.MISMATCHED:
                raise ReconciliationException("只有对账不一致的记录可以提交争议")
            
            # 验证订单是否属于对账记录
            valid_orders = await self._validate_dispute_orders(
                order_ids, reconciliation_log.mismatched_orders
            )
            
            if not valid_orders:
                raise ReconciliationException("争议订单不存在于对账记录中")
            
            # 创建争议记录
            dispute_id = await self._create_dispute_record(
                merchant_id,
                reconciliation_id,
                valid_orders,
                dispute_reason,
                evidence or []
            )
            
            # 更新对账记录中的已解决订单
            await self._update_resolved_orders(
                reconciliation_id, valid_orders
            )
            
            logger.info(f"争议申请提交成功: {dispute_id}")
            return True
            
        except ReconciliationException:
            raise
        except Exception as e:
            logger.error(f"提交争议申请失败: {str(e)}", exc_info=True)
            raise ReconciliationException("提交争议申请失败")
    
    async def _get_platform_transactions(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取平台交易数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的平台交易数据，日期范围: {start_date} 至 {end_date}")
            
            # 查询订单数据
            orders = await db.execute_query(
                "orders",
                filters={
                    "merchant_id": merchant_id,
                    "created_at": {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    },
                    "status": "completed"  # 只查询已完成的订单
                }
            )
            
            platform_transactions = []
            for order in orders:
                platform_transactions.append({
                    "order_id": order.get('order_no'),
                    "amount": Decimal(str(order.get('amount', 0))),
                    "transaction_time": datetime.fromisoformat(order.get('created_at')),
                    "payment_method": order.get('payment_method'),
                    "customer_info": order.get('customer_name')
                })
            
            logger.debug(f"获取到 {len(platform_transactions)} 条平台交易记录")
            
            return platform_transactions
            
        except Exception as e:
            logger.error(f"获取平台交易数据失败: {str(e)}", exc_info=True)
            return []
    
    async def _get_bank_transactions(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取银行交易数据"""
        try:
            logger.debug(f"获取商户 {merchant_id} 的银行交易数据，日期范围: {start_date} 至 {end_date}")
            
            # 这里需要根据实际的银行接口或银行对账文件来获取数据
            # 暂时返回模拟数据
            
            # 模拟银行交易数据
            bank_transactions = [
                {
                    "transaction_id": "BANK001",
                    "amount": Decimal("1000000"),
                    "transaction_time": datetime.now(),
                    "reference_no": "ORDER001",
                    "bank_account": "VCB***6789"
                },
                {
                    "transaction_id": "BANK002", 
                    "amount": Decimal("500000"),
                    "transaction_time": datetime.now(),
                    "reference_no": "ORDER002",
                    "bank_account": "VCB***6789"
                }
            ]
            
            logger.debug(f"获取到 {len(bank_transactions)} 条银行交易记录")
            
            return bank_transactions
            
        except Exception as e:
            logger.error(f"获取银行交易数据失败: {str(e)}", exc_info=True)
            return []
    
    async def _compare_transactions(
        self,
        platform_data: List[Dict[str, Any]],
        bank_data: List[Dict[str, Any]],
        merchant_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """比对交易数据"""
        try:
            logger.info(f"开始比对交易数据，平台记录数: {len(platform_data)}, 银行记录数: {len(bank_data)}")
            
            # 计算平台总金额
            platform_total = sum(txn['amount'] for txn in platform_data)
            
            # 计算银行总金额
            bank_total = sum(txn['amount'] for txn in bank_data)
            
            # 计算差异
            difference = platform_total - bank_total
            
            # 查找不匹配的订单
            mismatched_orders = await self._find_mismatched_orders(platform_data, bank_data)
            
            # 确定对账状态
            status = await self._determine_reconciliation_status(
                difference, mismatched_orders
            )
            
            result = {
                "merchant_id": merchant_id,
                "reconciliation_date": date.today(),
                "start_date": start_date,
                "end_date": end_date,
                "platform_total": platform_total,
                "bank_total": bank_total,
                "difference": difference,
                "status": status,
                "mismatched_orders": mismatched_orders,
                "resolved_orders": [],
                "notes": f"自动对账 {start_date} 到 {end_date}",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            logger.info(f"交易比对完成: 状态={status.value}, 差异={difference}")
            
            return result
            
        except Exception as e:
            logger.error(f"比对交易数据失败: {str(e)}", exc_info=True)
            raise ReconciliationException("比对交易数据失败")
    
    async def _find_mismatched_orders(
        self,
        platform_data: List[Dict[str, Any]],
        bank_data: List[Dict[str, Any]]
    ) -> List[str]:
        """查找不匹配的订单"""
        try:
            logger.debug("开始查找不匹配的订单")
            
            mismatched_orders = []
            
            # 创建银行交易的映射（按参考号）
            bank_transactions_map = {}
            for txn in bank_data:
                ref_no = txn.get('reference_no')
                if ref_no:
                    bank_transactions_map[ref_no] = txn
            
            # 检查平台订单在银行数据中是否存在
            for platform_txn in platform_data:
                order_id = platform_txn['order_id']
                bank_txn = bank_transactions_map.get(order_id)
                
                if not bank_txn:
                    mismatched_orders.append(order_id)
                    logger.debug(f"订单 {order_id} 在银行数据中未找到")
                    continue
                
                # 检查金额是否匹配
                if platform_txn['amount'] != bank_txn['amount']:
                    mismatched_orders.append(order_id)
                    logger.debug(f"订单 {order_id} 金额不匹配: 平台={platform_txn['amount']}, 银行={bank_txn['amount']}")
            
            logger.debug(f"找到 {len(mismatched_orders)} 个不匹配的订单")
            
            return mismatched_orders
            
        except Exception as e:
            logger.error(f"查找不匹配订单失败: {str(e)}", exc_info=True)
            return []
    
    async def _determine_reconciliation_status(
        self,
        difference: Decimal,
        mismatched_orders: List[str]
    ) -> ReconciliationStatus:
        """确定对账状态"""
        if difference == 0 and not mismatched_orders:
            return ReconciliationStatus.MATCHED
        elif difference != 0 or mismatched_orders:
            return ReconciliationStatus.MISMATCHED
        else:
            return ReconciliationStatus.ERROR
    
    async def _save_reconciliation_log(self, data: Dict[str, Any]) -> ReconciliationLog:
        """保存对账日志"""
        try:
            logger.info("保存对账日志")
            
            reconciliation_log = ReconciliationLog(
                id=str(uuid.uuid4()),
                **data
            )
            
            await db.insert_data(
                "finances_reconciliation_logs",
                reconciliation_log.dict()
            )
            
            logger.info(f"对账日志保存成功: {reconciliation_log.id}")
            
            return reconciliation_log
            
        except Exception as e:
            logger.error(f"保存对账日志失败: {str(e)}", exc_info=True)
            raise ReconciliationException("保存对账日志失败")
    
    async def _format_reconciliation_result(
        self, 
        reconciliation_log: ReconciliationLog
    ) -> ReconciliationResult:
        """格式化对账结果"""
        logger.debug(f"格式化对账结果: {reconciliation_log.id}")
        
        return ReconciliationResult(
            reconciliation_id=reconciliation_log.id,
            status=reconciliation_log.status,
            platform_total=reconciliation_log.platform_total,
            bank_total=reconciliation_log.bank_total,
            difference=reconciliation_log.difference,
            mismatched_orders=reconciliation_log.mismatched_orders,
            reconciliation_date=reconciliation_log.created_at
        )
    
    async def _get_existing_reconciliation(
        self, 
        merchant_id: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[ReconciliationLog]:
        """获取已存在的对账记录"""
        try:
            logger.debug(f"检查是否存在对账记录: 商户={merchant_id}, 日期范围={start_date}至{end_date}")
            
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={
                    "merchant_id": merchant_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                limit=1
            )
            
            if records:
                reconciliation_log = ReconciliationLog(**records[0])
                logger.debug(f"找到已存在的对账记录: {reconciliation_log.id}")
                return reconciliation_log
            
            logger.debug("未找到已存在的对账记录")
            return None
            
        except Exception as e:
            logger.error(f"获取已存在的对账记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _get_reconciliation_log(
        self, 
        reconciliation_id: str, 
        merchant_id: str
    ) -> Optional[ReconciliationLog]:
        """获取对账记录"""
        try:
            logger.debug(f"获取对账记录: {reconciliation_id}")
            
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={
                    "id": reconciliation_id,
                    "merchant_id": merchant_id
                },
                limit=1
            )
            
            if records:
                reconciliation_log = ReconciliationLog(**records[0])
                logger.debug(f"找到对账记录: {reconciliation_log.id}")
                return reconciliation_log
            
            logger.debug(f"未找到对账记录: {reconciliation_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取对账记录失败: {str(e)}", exc_info=True)
            return None
    
    async def _validate_dispute_orders(
        self, 
        order_ids: List[str], 
        mismatched_orders: List[str]
    ) -> List[str]:
        """验证争议订单"""
        logger.debug(f"验证争议订单: {order_ids}")
        
        valid_orders = []
        for order_id in order_ids:
            if order_id in mismatched_orders:
                valid_orders.append(order_id)
        
        logger.debug(f"验证通过的争议订单: {valid_orders}")
        return valid_orders
    
    async def _create_dispute_record(
        self,
        merchant_id: str,
        reconciliation_id: str,
        order_ids: List[str],
        dispute_reason: str,
        evidence: List[str]
    ) -> str:
        """创建争议记录"""
        try:
            logger.info(f"创建争议记录: 商户={merchant_id}, 对账ID={reconciliation_id}")
            
            dispute_id = str(uuid.uuid4())
            
            dispute_data = {
                "id": dispute_id,
                "merchant_id": merchant_id,
                "reconciliation_id": reconciliation_id,
                "order_ids": order_ids,
                "dispute_reason": dispute_reason,
                "evidence": evidence,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 插入争议记录到数据库
            await db.insert_data("finances_dispute_records", dispute_data)
            
            logger.info(f"争议记录创建成功: {dispute_id}")
            
            return dispute_id
            
        except Exception as e:
            logger.error(f"创建争议记录失败: {str(e)}", exc_info=True)
            raise ReconciliationException("创建争议记录失败")
    
    async def _update_resolved_orders(
        self, 
        reconciliation_id: str, 
        resolved_orders: List[str]
    ):
        """更新已解决订单"""
        try:
            logger.info(f"更新对账记录 {reconciliation_id} 的已解决订单")
            
            # 获取当前对账记录
            records = await db.execute_query(
                "finances_reconciliation_logs",
                filters={"id": reconciliation_id},
                limit=1
            )
            
            if not records:
                logger.warning(f"未找到对账记录: {reconciliation_id}")
                return
            
            current_log = records[0]
            current_resolved = current_log.get('resolved_orders', [])
            
            # 合并已解决订单
            updated_resolved = list(set(current_resolved + resolved_orders))
            
            # 更新记录
            await db.update_data(
                "finances_reconciliation_logs",
                {
                    "resolved_orders": updated_resolved,
                    "updated_at": datetime.now().isoformat()
                },
                {"id": reconciliation_id}
            )
            
            logger.info(f"对账记录 {reconciliation_id} 的已解决订单更新成功")
            
        except Exception as e:
            logger.error(f"更新已解决订单失败: {str(e)}", exc_info=True)
            raise ReconciliationException("更新已解决订单失败")
    
    async def _get_reconciliation_count(self, filters: Dict[str, Any]) -> int:
        """获取对账记录总数"""
        try:
            logger.debug("查询对账记录总数")
            
            # 这里应该调用数据库的 COUNT 方法
            # 示例实现，实际应根据数据库客户端调整
            count = await db.execute_count("finances_reconciliation_logs", filters=filters)
            return count if count else 0
            
        except Exception as e:
            logger.error(f"获取对账记录总数失败: {str(e)}", exc_info=True)
            # 回退到原来的实现方式
            records = await db.execute_query("finances_reconciliation_logs", filters=filters)
            return len(records)

            内容板块-推荐系统服务

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.middleware.auth import get_current_user
from app.schemas.video_schemas import VideoResponse
from app.schemas.response_schemas import StandardResponse
from app.services.recommendation_service import RecommendationService
from app.utils.exceptions import NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("/personalized", response_model=StandardResponse[List[VideoResponse]])
async def get_personalized_recommendations(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取个性化推荐"""
    try:
        recommendations = await RecommendationService.get_personalized_recommendations(
            db, current_user["user_id"], limit
        )
        
        return StandardResponse(
            success=True,
            message="获取个性化推荐成功",
            data=recommendations
        )
    except Exception as e:
        logger.error(f"Get personalized recommendations error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/trending", response_model=StandardResponse[List[VideoResponse]])
async def get_trending_recommendations(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    db: Session = Depends(get_db)
):
    """获取趋势推荐"""
    try:
        recommendations = await RecommendationService.get_trending_videos(db, limit)
        
        return StandardResponse(
            success=True,
            message="获取趋势推荐成功",
            data=recommendations
        )
    except Exception as e:
        logger.error(f"Get trending recommendations error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/popular", response_model=StandardResponse[List[VideoResponse]])
async def get_popular_recommendations(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    db: Session = Depends(get_db)
):
    """获取热门推荐"""
    try:
        recommendations = await RecommendationService.get_popular_videos(db, limit)
        
        return StandardResponse(
            success=True,
            message="获取热门推荐成功",
            data=recommendations
        )
    except Exception as e:
        logger.error(f"Get popular recommendations error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")


@router.get("/content-based/{video_id}", response_model=StandardResponse[List[VideoResponse]])
async def get_content_based_recommendations(
    video_id: str,
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    db: Session = Depends(get_db)
):
    """获取基于内容的推荐"""
    try:
        recommendations = await RecommendationService.get_content_based_recommendations(
            db, video_id, limit
        )
        
        return StandardResponse(
            success=True,
            message="获取内容推荐成功",
            data=recommendations
        )
    except Exception as e:
        logger.error(f"Get content-based recommendations error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器内部错误")



        内容系统


import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
import json
import redis
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.database.supabase_client import db_manager, Tables
from app.models.recommendation import (
    RecommendationRequest, RecommendationResponse, 
    SimilarContentRequest, TrendingContentRequest
)
from app.core.exceptions import DatabaseException
from app.config import settings

logger = logging.getLogger(__name__)

class RecommendationService:
    """推荐服务类"""
    
    def __init__(self):
        self.db = db_manager
        # 初始化Redis客户端用于缓存
        self.redis_client = redis.Redis.from_url(
            settings.redis_url, 
            password=settings.redis_password, 
            decode_responses=True
        )
        # 初始化TF-IDF向量化器
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
    
    async def get_personalized_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """获取个性化推荐"""
        try:
            cache_key = f"recommendations:{request.user_id}:{request.limit}"
            cached_result = self.redis_client.get(cache_key)
            
            if cached_result:
                logger.info(f"从缓存获取推荐结果: {request.user_id}")
                return RecommendationResponse(**json.loads(cached_result))
            
            # 获取用户画像
            user_profile = await self._get_user_profile(request.user_id)
            
            # 获取用户历史行为
            user_behavior = await self._get_user_behavior(request.user_id)
            
            # 多策略推荐
            recommendations = []
            
            # 策略1: 基于内容的推荐
            content_based_recs = await self._get_content_based_recommendations(
                user_profile, user_behavior, request
            )
            recommendations.extend(content_based_recs)
            
            # 策略2: 协同过滤推荐
            collaborative_recs = await self._get_collaborative_recommendations(
                user_profile, user_behavior, request
            )
            recommendations.extend(collaborative_recs)
            
            # 策略3: 热门内容推荐
            trending_recs = await self._get_trending_recommendations(request)
            recommendations.extend(trending_recs)
            
            # 去重和排序
            unique_recommendations = self._deduplicate_and_rank(
                recommendations, user_behavior, request
            )
            
            # 限制返回数量
            final_recommendations = unique_recommendations[:request.limit]
            
            # 构建响应
            response = RecommendationResponse(
                items=final_recommendations,
                total=len(final_recommendations),
                algorithm="hybrid",
                reasoning="基于内容、协同过滤和热门内容的混合推荐"
            )
            
            # 缓存结果（5分钟）
            self.redis_client.setex(
                cache_key, 
                timedelta(minutes=5), 
                json.dumps(response.dict())
            )
            
            logger.info(f"生成个性化推荐成功: {request.user_id}, 数量: {len(final_recommendations)}")
            return response
            
        except Exception as e:
            logger.error(f"生成个性化推荐失败 {request.user_id}: {str(e)}")
            # 降级策略：返回热门内容
            return await self._get_fallback_recommendations(request)
    
    async def _get_user_profile(self, user_id: UUID) -> Dict[str, Any]:
        """获取用户画像"""
        try:
            # 从数据库获取用户资料
            profiles = await self.db.select(
                Tables.USER_PROFILES,
                filters={"user_id": str(user_id)}
            )
            profile = profiles[0] if profiles else {}
            
            # 获取用户互动历史
            interactions = await self.db.select(
                Tables.CONTENT_INTERACTIONS,
                filters={"user_id": str(user_id)}
            )
            
            # 构建用户画像
            user_profile = {
                "user_id": user_id,
                "interests": profile.get("preferences", {}).get("interests", []),
                "viewed_content": [interaction["content_id"] for interaction in interactions],
                "liked_content": [
                    interaction["content_id"] 
                    for interaction in interactions 
                    if interaction["interaction_type"] == "like"
                ],
                "location_preferences": profile.get("location"),
                "content_type_preferences": self._calculate_content_type_preferences(interactions),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return user_profile
            
        except Exception as e:
            logger.error(f"获取用户画像失败 {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "interests": [],
                "viewed_content": [],
                "liked_content": [],
                "location_preferences": None,
                "content_type_preferences": {},
                "last_updated": datetime.utcnow().isoformat()
            }
    
    def _calculate_content_type_preferences(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算用户内容类型偏好"""
        try:
            if not interactions:
                return {}
            
            # 统计各类型内容的互动次数
            type_counts = {}
            total_interactions = len(interactions)
            
            for interaction in interactions:
                # 获取内容类型（这里需要查询内容表，简化处理）
                # 在实际应用中，应该关联内容表获取类型
                content_type = "video"  # 默认类型
                type_counts[content_type] = type_counts.get(content_type, 0) + 1
            
            # 计算偏好分数
            preferences = {}
            for content_type, count in type_counts.items():
                preferences[content_type] = count / total_interactions
            
            return preferences
            
        except Exception as e:
            logger.error(f"计算内容类型偏好失败: {str(e)}")
            return {}
    
    async def _get_user_behavior(self, user_id: UUID) -> Dict[str, Any]:
        """获取用户行为数据"""
        try:
            # 获取用户最近100条互动记录
            interactions = await self.db.select(
                Tables.CONTENT_INTERACTIONS,
                filters={"user_id": str(user_id)},
                columns="*"
            )
            
            # 按时间排序，取最近记录
            interactions.sort(key=lambda x: x["created_at"], reverse=True)
            recent_interactions = interactions[:100]
            
            behavior_data = {
                "recent_views": [
                    interaction for interaction in recent_interactions 
                    if interaction["interaction_type"] == "view"
                ],
                "recent_likes": [
                    interaction for interaction in recent_interactions 
                    if interaction["interaction_type"] == "like"
                ],
                "total_interactions": len(interactions),
                "preferred_categories": self._extract_preferred_categories(recent_interactions)
            }
            
            return behavior_data
            
        except Exception as e:
            logger.error(f"获取用户行为数据失败 {user_id}: {str(e)}")
            return {
                "recent_views": [],
                "recent_likes": [],
                "total_interactions": 0,
                "preferred_categories": []
            }
    
    def _extract_preferred_categories(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """从互动记录中提取偏好分类"""
        try:
            # 简化实现：返回固定分类
            # 在实际应用中，应该分析内容标签和分类
            return ["美食", "旅游", "生活"]
        except Exception as e:
            logger.error(f"提取偏好分类失败: {str(e)}")
            return []
    
    async def _get_content_based_recommendations(
        self, 
        user_profile: Dict[str, Any], 
        user_behavior: Dict[str, Any],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """基于内容的推荐"""
        try:
            # 获取候选内容
            candidate_contents = await self._get_candidate_contents(request)
            
            if not candidate_contents:
                return []
            
            # 基于用户兴趣和内容特征进行匹配
            recommendations = []
            user_interests = user_profile.get("interests", [])
            
            for content in candidate_contents:
                # 计算内容与用户兴趣的匹配度
                content_tags = content.get("tags", [])
                content_categories = content.get("metadata", {}).get("categories", [])
                
                # 简单的标签匹配算法
                match_score = self._calculate_content_match_score(
                    user_interests, content_tags, content_categories
                )
                
                if match_score > 0.1:  # 匹配阈值
                    content["match_score"] = match_score
                    content["recommendation_reason"] = "基于您的兴趣推荐"
                    recommendations.append(content)
            
            # 按匹配度排序
            recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            
            return recommendations[:20]  # 返回前20个
            
        except Exception as e:
            logger.error(f"基于内容推荐失败: {str(e)}")
            return []
    
    async def _get_collaborative_recommendations(
        self, 
        user_profile: Dict[str, Any], 
        user_behavior: Dict[str, Any],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """协同过滤推荐"""
        try:
            # 简化版的协同过滤
            # 在实际应用中，应该使用更复杂的算法
            
            # 获取用户喜欢的内容
            liked_content_ids = user_profile.get("liked_content", [])
            if not liked_content_ids:
                return []
            
            # 找到喜欢相同内容的其他用户
            similar_users = await self._find_similar_users(liked_content_ids)
            
            # 获取这些用户喜欢但当前用户没看过的内容
            recommendations = []
            for user_id in similar_users[:10]:  # 取前10个相似用户
                user_likes = await self._get_user_liked_content(user_id)
                new_content = [
                    content for content in user_likes 
                    if content["id"] not in liked_content_ids and 
                    content["id"] not in user_profile.get("viewed_content", [])
                ]
                recommendations.extend(new_content)
            
            # 去重和排序
            unique_recommendations = []
            seen_ids = set()
            for rec in recommendations:
                if rec["id"] not in seen_ids:
                    rec["match_score"] = 0.5  # 协同过滤的默认分数
                    rec["recommendation_reason"] = "喜欢相似内容的用户也在看"
                    unique_recommendations.append(rec)
                    seen_ids.add(rec["id"])
            
            return unique_recommendations[:20]
            
        except Exception as e:
            logger.error(f"协同过滤推荐失败: {str(e)}")
            return []
    
    async def _get_trending_recommendations(self, request: TrendingContentRequest) -> List[Dict[str, Any]]:
        """获取热门内容推荐"""
        try:
            # 获取最近24小时的热门内容
            time_threshold = datetime.utcnow() - timedelta(hours=24)
            
            # 查询热门内容（按观看数和点赞数排序）
            contents = await self.db.select(
                Tables.CONTENT,
                filters={
                    "moderation_status": "approved",
                    "status": "approved"
                },
                columns="*"
            )
            
            # 计算热度分数
            for content in contents:
                view_count = content.get("view_count", 0)
                like_count = content.get("like_count", 0)
                share_count = content.get("share_count", 0)
                
                # 热度算法：观看数 * 1 + 点赞数 * 2 + 分享数 * 3
                hot_score = view_count * 1 + like_count * 2 + share_count * 3
                content["hot_score"] = hot_score
            
            # 按热度排序
            contents.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
            
            # 添加推荐理由
            for content in contents[:20]:  # 取前20个热门内容
                content["match_score"] = 0.3  # 热门内容的默认分数
                content["recommendation_reason"] = "热门内容"
            
            return contents[:20]
            
        except Exception as e:
            logger.error(f"获取热门内容推荐失败: {str(e)}")
            return []
    
    async def _find_similar_users(self, liked_content_ids: List[str]) -> List[str]:
        """找到相似用户"""
        try:
            if not liked_content_ids:
                return []
            
            # 查询也喜欢这些内容的用户
            similar_users = set()
            for content_id in liked_content_ids[:5]:  # 取前5个喜欢的内容
                interactions = await self.db.select(
                    Tables.CONTENT_INTERACTIONS,
                    filters={
                        "content_id": content_id,
                        "interaction_type": "like"
                    },
                    columns="user_id"
                )
                
                for interaction in interactions:
                    similar_users.add(interaction["user_id"])
            
            # 移除当前用户（如果有）
            similar_users = list(similar_users)
            
            return similar_users[:50]  # 返回前50个相似用户
            
        except Exception as e:
            logger.error(f"查找相似用户失败: {str(e)}")
            return []
    
    async def _get_user_liked_content(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户喜欢的内容"""
        try:
            # 查询用户喜欢的内容
            interactions = await self.db.select(
                Tables.CONTENT_INTERACTIONS,
                filters={
                    "user_id": user_id,
                    "interaction_type": "like"
                },
                columns="content_id"
            )
            
            content_ids = [interaction["content_id"] for interaction in interactions]
            
            if not content_ids:
                return []
            
            # 获取内容详情
            contents = []
            for content_id in content_ids[:20]:  # 取前20个喜欢的内容
                content = await self.db.select(
                    Tables.CONTENT,
                    filters={"id": content_id},
                    columns="*"
                )
                if content:
                    contents.append(content[0])
            
            return contents
            
        except Exception as e:
            logger.error(f"获取用户喜欢内容失败 {user_id}: {str(e)}")
            return []
    
    async def _get_candidate_contents(self, request: RecommendationRequest) -> List[Dict[str, Any]]:
        """获取候选内容"""
        try:
            # 构建查询条件
            filters = {
                "moderation_status": "approved",
                "status": "approved"
            }
            
            if request.content_types:
                filters["content_type"] = [ct.value for ct in request.content_types]
            
            # 查询内容
            contents = await self.db.select(
                Tables.CONTENT,
                filters=filters,
                columns="*"
            )
            
            # 排除已观看的内容
            if request.exclude_viewed:
                # 这里需要用户观看历史，简化处理
                pass
            
            return contents[:100]  # 返回前100个候选内容
            
        except Exception as e:
            logger.error(f"获取候选内容失败: {str(e)}")
            return []
    
    def _calculate_content_match_score(
        self, 
        user_interests: List[str], 
        content_tags: List[str], 
        content_categories: List[str]
    ) -> float:
        """计算内容匹配分数"""
        try:
            if not user_interests:
                return 0.0
            
            # 计算兴趣标签匹配
            interest_match = len(set(user_interests) & set(content_tags))
            
            # 计算分类匹配
            category_match = len(set(user_interests) & set(content_categories))
            
            # 综合匹配分数
            total_match = interest_match + category_match * 0.5
            max_possible = len(user_interests) + len(user_interests) * 0.5
            
            if max_possible == 0:
                return 0.0
            
            return total_match / max_possible
            
        except Exception as e:
            logger.error(f"计算内容匹配分数失败: {str(e)}")
            return 0.0
    
    def _deduplicate_and_rank(
        self, 
        recommendations: List[Dict[str, Any]], 
        user_behavior: Dict[str, Any],
        request: RecommendationRequest
    ) -> List[Dict[str, Any]]:
        """去重和排序推荐结果"""
        try:
            # 去重
            unique_recommendations = []
            seen_ids = set()
            
            for rec in recommendations:
                if rec["id"] not in seen_ids:
                    unique_recommendations.append(rec)
                    seen_ids.add(rec["id"])
            
            # 排序：按匹配分数和内容质量
            unique_recommendations.sort(
                key=lambda x: (
                    x.get("match_score", 0) * 0.7 + 
                    x.get("quality_score", 0) * 0.3
                ),
                reverse=True
            )
            
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"去重和排序推荐结果失败: {str(e)}")
            return recommendations
    
    async def _get_fallback_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """降级推荐策略：返回热门内容"""
        try:
            trending_request = TrendingContentRequest(limit=request.limit)
            trending_recs = await self._get_trending_recommendations(trending_request)
            
            response = RecommendationResponse(
                items=trending_recs,
                total=len(trending_recs),
                algorithm="fallback",
                reasoning="系统繁忙，返回热门内容作为推荐"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"降级推荐也失败: {str(e)}")
            # 最后的手段：返回空推荐
            return RecommendationResponse(
                items=[],
                total=0,
                algorithm="none",
                reasoning="无法生成推荐"
            )
    
    async def get_similar_content(self, request: SimilarContentRequest) -> RecommendationResponse:
        """获取相似内容"""
        try:
            # 获取目标内容
            target_content = await self.db.select(
                Tables.CONTENT,
                filters={"id": str(request.content_id)},
                columns="*"
            )
            
            if not target_content:
                return RecommendationResponse(
                    items=[],
                    total=0,
                    algorithm="similar",
                    reasoning="目标内容不存在"
                )
            
            target_content = target_content[0]
            
            # 获取候选内容
            candidate_contents = await self._get_candidate_contents(
                RecommendationRequest(user_id=UUID(int=0), limit=100)
            )
            
            # 计算相似度
            similar_contents = []
            for content in candidate_contents:
                if content["id"] == request.content_id:
                    continue  # 跳过自身
                
                similarity = self._calculate_content_similarity(target_content, content)
                if similarity > 0.3:  # 相似度阈值
                    content["similarity_score"] = similarity
                    content["recommendation_reason"] = "与您观看的内容相似"
                    similar_contents.append(content)
            
            # 按相似度排序
            similar_contents.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
            # 限制返回数量
            final_contents = similar_contents[:request.limit]
            
            response = RecommendationResponse(
                items=final_contents,
                total=len(final_contents),
                algorithm="similar",
                reasoning="基于内容相似度的推荐"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"获取相似内容失败 {request.content_id}: {str(e)}")
            return RecommendationResponse(
                items=[],
                total=0,
                algorithm="similar",
                reasoning="获取相似内容失败"
            )
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> float:
        """计算内容相似度"""
        try:
            similarity = 0.0
            
            # 标签相似度
            tags1 = set(content1.get("tags", []))
            tags2 = set(content2.get("tags", []))
            if tags1 and tags2:
                tag_similarity = len(tags1 & tags2) / len(tags1 | tags2)
                similarity += tag_similarity * 0.4
            
            # 分类相似度
            categories1 = set(content1.get("metadata", {}).get("categories", []))
            categories2 = set(content2.get("metadata", {}).get("categories", []))
            if categories1 and categories2:
                category_similarity = len(categories1 & categories2) / len(categories1 | categories2)
                similarity += category_similarity * 0.3
            
            # 创作者相似度（如果是同一个创作者）
            if content1.get("creator_id") == content2.get("creator_id"):
                similarity += 0.3
            
            return similarity
            
        except Exception as e:
            logger.error(f"计算内容相似度失败: {str(e)}")
            return 0.0
