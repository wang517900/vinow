# app/services/analytics_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.database import supabase
from app.models.order import OrderStatus
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """数据分析服务类"""
    
    @staticmethod
    async def get_order_trends(
        merchant_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """获取订单趋势数据"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取每日订单数据
            response = supabase.table("orders").select("created_at, status, paid_amount").eq("merchant_id", merchant_id).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
            
            # 按日期分组统计
            daily_stats = {}
            for order in response.data:
                order_date = datetime.fromisoformat(order["created_at"]).strftime("%Y-%m-%d")
                if order_date not in daily_stats:
                    daily_stats[order_date] = {
                        "date": order_date,
                        "total_orders": 0,
                        "completed_orders": 0,
                        "total_amount": 0
                    }
                
                daily_stats[order_date]["total_orders"] += 1
                daily_stats[order_date]["total_amount"] += order.get("paid_amount", 0)
                
                if order["status"] == OrderStatus.VERIFIED:
                    daily_stats[order_date]["completed_orders"] += 1
            
            # 转换为列表并按日期排序
            trends_data = sorted(daily_stats.values(), key=lambda x: x["date"])
            
            return {
                "period": f"最近{days}天",
                "trends": trends_data
            }
            
        except Exception as e:
            logger.error(f"获取订单趋势失败: {e}")
            return {"period": f"最近{days}天", "trends": []}
    
    @staticmethod
    async def get_verification_hourly_stats(merchant_id: str, days: int = 7) -> Dict[str, Any]:
        """获取核销时间段分布"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            response = supabase.table("verification_records").select("created_at").eq("merchant_id", merchant_id).gte("created_at", start_date.isoformat()).execute()
            
            # 按小时统计
            hourly_stats = {f"{i:02d}:00": 0 for i in range(24)}
            
            for record in response.data:
                hour = datetime.fromisoformat(record["created_at"]).strftime("%H:00")
                hourly_stats[hour] = hourly_stats.get(hour, 0) + 1
            
            return {
                "hourly_distribution": [
                    {"hour": hour, "count": count} 
                    for hour, count in hourly_stats.items()
                ]
            }
            
        except Exception as e:
            logger.error(f"获取核销时间段分布失败: {e}")
            return {"hourly_distribution": []}
    
    @staticmethod
    async def get_top_products(
        merchant_id: str, 
        limit: int = 10, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取热销商品排行"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 获取商品销售数据
            response = supabase.table("orders").select("product_name, product_id, quantity, paid_amount").eq("merchant_id", merchant_id).eq("status", OrderStatus.VERIFIED).gte("verified_at", start_date.isoformat()).execute()
            
            # 统计商品销售
            product_stats = {}
            for order in response.data:
                product_id = order["product_id"]
                if product_id not in product_stats:
                    product_stats[product_id] = {
                        "product_id": product_id,
                        "product_name": order["product_name"],
                        "total_quantity": 0,
                        "total_amount": 0,
                        "order_count": 0
                    }
                
                product_stats[product_id]["total_quantity"] += order["quantity"]
                product_stats[product_id]["total_amount"] += order["paid_amount"]
                product_stats[product_id]["order_count"] += 1
            
            # 按销售金额排序
            sorted_products = sorted(
                product_stats.values(), 
                key=lambda x: x["total_amount"], 
                reverse=True
            )
            
            return sorted_products[:limit]
            
        except Exception as e:
            logger.error(f"获取热销商品失败: {e}")
            return []
    
    @staticmethod
    async def get_daily_report(merchant_id: str, report_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取日报表"""
        try:
            if not report_date:
                report_date = datetime.now()
            
            start_of_day = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = report_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 获取当日订单数据
            orders_response = supabase.table("orders").select("*").eq("merchant_id", merchant_id).gte("created_at", start_of_day.isoformat()).lte("created_at", end_of_day.isoformat()).execute()
            
            # 计算各项指标
            total_orders = len(orders_response.data)
            verified_orders = len([o for o in orders_response.data if o["status"] == OrderStatus.VERIFIED])
            pending_orders = len([o for o in orders_response.data if o["status"] == OrderStatus.PENDING])
            refunded_orders = len([o for o in orders_response.data if o["status"] == OrderStatus.REFUNDED])
            
            total_amount = sum(o["paid_amount"] for o in orders_response.data)
            verified_amount = sum(o["paid_amount"] for o in orders_response.data if o["status"] == OrderStatus.VERIFIED)
            
            # 支付方式分布
            payment_methods = {}
            for order in orders_response.data:
                method = order["payment_method"]
                payment_methods[method] = payment_methods.get(method, 0) + 1
            
            return {
                "report_date": report_date.strftime("%Y-%m-%d"),
                "total_orders": total_orders,
                "verified_orders": verified_orders,
                "pending_orders": pending_orders,
                "refunded_orders": refunded_orders,
                "total_amount": total_amount,
                "verified_amount": verified_amount,
                "verification_rate": round((verified_orders / total_orders * 100), 2) if total_orders > 0 else 0,
                "payment_method_distribution": payment_methods,
                "average_order_value": round(total_amount / total_orders, 2) if total_orders > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"生成日报表失败: {e}")
            return {}
    
    @staticmethod
    async def export_orders_data(
        merchant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "excel"
    ) -> Dict[str, Any]:
        """导出订单数据"""
        try:
            query = supabase.table("orders").select("*").eq("merchant_id", merchant_id)
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            response = query.execute()
            
            # 这里可以集成pandas进行数据导出
            # 简化版本，返回原始数据
            return {
                "total_orders": len(response.data),
                "data": response.data,
                "exported_at": datetime.now().isoformat(),
                "format": format
            }
            
        except Exception as e:
            logger.error(f"导出订单数据失败: {e}")
            return {"total_orders": 0, "data": [], "error": str(e)}

analytics_service = AnalyticsService()"""商家系统 - analytics_service"""

# TODO: 实现商家系统相关功能

商家板块5数据分析
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from app.core.exceptions import DatabaseException, NotFoundException
from app.services.supabase_client import SupabaseClient
from app.models.business import (
    HealthScoreLevel, AlertLevel, PeriodType,
    BusinessMetrics, Alert, BusinessSnapshot, CompetitorAnalysis,
    MarketingCampaign, Review, RevenueTrend
)
from app.schemas.analytics import (
    HealthScoreResponse, CoreMetric, CoreMetricsResponse,
    AlertResponse, AlertSummaryResponse, BusinessSnapshotResponse,
    CompetitorAnalysisResponse, MarketingROIResponse,
    RevenueTrendResponse, RevenueAnalysisResponse, ReviewSummaryResponse,
    DashboardResponse
)


class AnalyticsService:
    """分析服务"""
    
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
    
    async def get_health_score(self, business_date: date) -> HealthScoreResponse:
        """获取健康分数"""
        try:
            metrics = self.supabase.get_business_metrics(business_date.isoformat())
            
            if not metrics:
                logger.warning(f"No business metrics found for date: {business_date}")
                raise NotFoundException("Business metrics not found for the specified date")
            
            # 计算健康等级
            score = metrics['health_score']
            if score >= 90:
                level = HealthScoreLevel.EXCELLENT
            elif score >= 80:
                level = HealthScoreLevel.GOOD
            elif score >= 70:
                level = HealthScoreLevel.WARNING
            else:
                level = HealthScoreLevel.CRITICAL
            
            return HealthScoreResponse(
                score=score,
                level=level,
                better_than_peers=metrics.get('better_than_peers', 85.0),
                date=business_date
            )
        except Exception as e:
            logger.error(f"Failed to get health score: {str(e)}")
            raise DatabaseException("Failed to calculate health score")
    
    async def get_core_metrics(self, business_date: date) -> CoreMetricsResponse:
        """获取核心指标"""
        try:
            metrics = self.supabase.get_business_metrics(business_date.isoformat())
            
            if not metrics:
                raise NotFoundException("Business metrics not found")
            
            # 计算同比变化
            yesterday = business_date - timedelta(days=1)
            yesterday_metrics = self.supabase.get_business_metrics(yesterday.isoformat())
            
            def calculate_change(current, previous):
                if previous and previous > 0:
                    return ((current - previous) / previous) * 100
                return 0.0
            
            core_metrics = [
                CoreMetric(
                    name="到店客流",
                    value=metrics['customer_count'],
                    change_percentage=calculate_change(
                        metrics['customer_count'],
                        yesterday_metrics['customer_count'] if yesterday_metrics else None
                    ),
                    change_direction="up" if metrics['customer_count'] > (yesterday_metrics['customer_count'] if yesterday_metrics else 0) else "down"
                ),
                CoreMetric(
                    name="营业收入",
                    value=f"{metrics['revenue'] / 1000000:.1f}M VND",
                    change_percentage=calculate_change(
                        metrics['revenue'],
                        yesterday_metrics['revenue'] if yesterday_metrics else None
                    ),
                    change_direction="up" if metrics['revenue'] > (yesterday_metrics['revenue'] if yesterday_metrics else 0) else "down"
                ),
                CoreMetric(
                    name="订单数量",
                    value=f"{metrics['order_count']}单",
                    change_percentage=calculate_change(
                        metrics['order_count'],
                        yesterday_metrics['order_count'] if yesterday_metrics else None
                    ),
                    change_direction="up" if metrics['order_count'] > (yesterday_metrics['order_count'] if yesterday_metrics else 0) else "down"
                ),
                CoreMetric(
                    name="客户评分",
                    value=f"{metrics['rating']:.1f}分",
                    change_percentage=0.0,  # 评分变化较小，这里简化处理
                    change_direction="same"
                )
            ]
            
            return CoreMetricsResponse(
                metrics=core_metrics,
                comparison_date=yesterday
            )
        except Exception as e:
            logger.error(f"Failed to get core metrics: {str(e)}")
            raise DatabaseException("Failed to fetch core metrics")
    
    async def get_alerts_summary(self, business_date: date) -> AlertSummaryResponse:
        """获取预警摘要"""
        try:
            alerts_data = self.supabase.get_active_alerts(business_date.isoformat())
            
            critical_count = 0
            warning_count = 0
            normal_count = 0
            alerts = []
            
            for alert_data in alerts_data:
                alert = AlertResponse(
                    id=alert_data['id'],
                    title=alert_data['title'],
                    description=alert_data['description'],
                    level=AlertLevel(alert_data['level']),
                    created_at=datetime.fromisoformat(alert_data['created_at']),
                    is_resolved=alert_data['is_resolved']
                )
                alerts.append(alert)
                
                if alert_data['level'] == AlertLevel.CRITICAL:
                    critical_count += 1
                elif alert_data['level'] == AlertLevel.WARNING:
                    warning_count += 1
                else:
                    normal_count += 1
            
            return AlertSummaryResponse(
                critical=critical_count,
                warning=warning_count,
                normal=normal_count,
                alerts=alerts
            )
        except Exception as e:
            logger.error(f"Failed to get alerts summary: {str(e)}")
            raise DatabaseException("Failed to fetch alerts")
    
    async def get_business_snapshot(self, business_date: date) -> BusinessSnapshotResponse:
        """获取经营快照"""
        try:
            # 这里可以集成 AI 分析逻辑
            # 目前使用模拟数据
            snapshot_data = self.supabase.get_business_metrics(business_date.isoformat())
            
            if not snapshot_data:
                raise NotFoundException("Business snapshot not found")
            
            # 模拟 AI 分析结果
            positive_points = [
                "午市翻台率提升至2.1次",
                "新客转化率35%，超平均水平",
                "招牌菜点击率提升20%"
            ]
            
            improvement_points = [
                "晚高峰等位时间平均28分钟",
                "饮料套餐搭配率仅15%",
                "2星以下评价24小时内未回复"
            ]
            
            return BusinessSnapshotResponse(
                business_date=business_date,
                positive_points=positive_points,
                improvement_points=improvement_points,
                generated_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Failed to get business snapshot: {str(e)}")
            raise DatabaseException("Failed to generate business snapshot")
    
    async def get_competitor_analysis(self, business_date: date) -> CompetitorAnalysisResponse:
        """获取竞对分析"""
        try:
            analysis_data = self.supabase.get_competitor_analysis(business_date.isoformat())
            
            if not analysis_data:
                # 返回默认分析数据
                return CompetitorAnalysisResponse(
                    business_date=business_date,
                    total_competitors=8,
                    rating_rank=2,
                    price_level="中等偏上",
                    customer_flow_rank=3,
                    promotion_intensity="适中"
                )
            
            return CompetitorAnalysisResponse(
                business_date=business_date,
                total_competitors=analysis_data['total_competitors'],
                rating_rank=analysis_data['rating_rank'],
                price_level=analysis_data['price_level'],
                customer_flow_rank=analysis_data['customer_flow_rank'],
                promotion_intensity=analysis_data['promotion_intensity']
            )
        except Exception as e:
            logger.error(f"Failed to get competitor analysis: {str(e)}")
            raise DatabaseException("Failed to fetch competitor analysis")
    
    async def get_marketing_roi(self, days: int = 30) -> MarketingROIResponse:
        """获取营销 ROI"""
        try:
            campaigns_data = self.supabase.get_marketing_campaigns(days)
            
            campaigns = []
            total_investment = 0.0
            total_revenue = 0.0
            
            for campaign in campaigns_data:
                investment = campaign['investment']
                revenue = campaign['revenue_generated']
                roi = ((revenue - investment) / investment) * 100 if investment > 0 else 0
                
                campaigns.append({
                    "name": campaign['name'],
                    "investment": investment,
                    "revenue_generated": revenue,
                    "roi": roi,
                    "new_customers": campaign['new_customers']
                })
                
                total_investment += investment
                total_revenue += revenue
            
            overall_roi = ((total_revenue - total_investment) / total_investment) * 100 if total_investment > 0 else 0
            
            return MarketingROIResponse(
                campaigns=campaigns,
                total_investment=total_investment,
                total_revenue_generated=total_revenue,
                overall_roi=overall_roi
            )
        except Exception as e:
            logger.error(f"Failed to get marketing ROI: {str(e)}")
            raise DatabaseException("Failed to fetch marketing data")
    
    async def get_revenue_analysis(self, start_date: date, end_date: date) -> RevenueAnalysisResponse:
        """获取收入分析"""
        try:
            trends_data = self.supabase.get_revenue_trends(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            trends = []
            period_totals = {
                "morning": 0.0,
                "lunch": 0.0,
                "afternoon": 0.0,
                "evening": 0.0
            }
            
            for trend in trends_data:
                revenue_trend = RevenueTrendResponse(
                    date=datetime.fromisoformat(trend['business_date']).date(),
                    revenue=trend['revenue'],
                    period=trend.get('period')
                )
                trends.append(revenue_trend)
                
                # 累加时段收入
                if trend.get('period'):
                    period_totals[trend['period']] += trend['revenue']
            
            return RevenueAnalysisResponse(
                trends=trends,
                period_totals=period_totals
            )
        except Exception as e:
            logger.error(f"Failed to get revenue analysis: {str(e)}")
            raise DatabaseException("Failed to fetch revenue data")
    
    async def get_review_summary(self, start_date: date, end_date: date) -> ReviewSummaryResponse:
        """获取评价摘要"""
        try:
            summary_data = self.supabase.get_review_summary(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            # 计算平均评分
            total_rating = 0
            total_reviews = 0
            for review in summary_data['reviews']:
                total_rating += review['rating'] * review['count']
                total_reviews += review['count']
            
            average_rating = total_rating / total_reviews if total_reviews > 0 else 0
            
            # 处理关键词频率
            keyword_frequency = {}
            for keyword_data in summary_data['keywords']:
                keyword_frequency[keyword_data['keyword']] = keyword_data['frequency']
            
            return ReviewSummaryResponse(
                total_reviews=total_reviews,
                average_rating=round(average_rating, 1),
                pending_responses=summary_data['pending'],
                critical_reviews=0,  # 这里需要根据实际数据计算
                keyword_frequency=keyword_frequency
            )
        except Exception as e:
            logger.error(f"Failed to get review summary: {str(e)}")
            raise DatabaseException("Failed to fetch review data")
    
    async def get_dashboard_data(self, business_date: date) -> DashboardResponse:
        """获取仪表盘数据"""
        try:
            health_score = await self.get_health_score(business_date)
            core_metrics = await self.get_core_metrics(business_date)
            alerts = await self.get_alerts_summary(business_date)
            snapshot = await self.get_business_snapshot(business_date)
            competitor_analysis = await self.get_competitor_analysis(business_date)
            
            # 获取最近7天的收入趋势
            end_date = business_date
            start_date = business_date - timedelta(days=6)
            revenue_trends = await self.get_revenue_analysis(start_date, end_date)
            
            # 获取最近7天的评价摘要
            review_summary = await self.get_review_summary(start_date, end_date)
            
            return DashboardResponse(
                health_score=health_score,
                core_metrics=core_metrics,
                alerts=alerts,
                snapshot=snapshot,
                competitor_analysis=competitor_analysis,
                revenue_trends=revenue_trends,
                review_summary=review_summary
            )
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {str(e)}")
            raise DatabaseException("Failed to generate dashboard data")

    商家系统7评价管理
    from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.database import supabase

class ReviewAnalyticsService:
    def __init__(self):
        self.supabase = supabase

    async def get_trend_analysis(self, merchant_id: int, days: int = 7) -> Dict[str, Any]:
        """获取评分趋势分析"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 获取指定时间段内的评价数据
        result = self.supabase.table("merchant_reviews").select(
            "rating, created_at"
        ).eq("merchant_id", merchant_id).eq("status", "active").gte(
            "created_at", start_date.isoformat()
        ).lte("created_at", end_date.isoformat()).execute()
        
        if not result.data:
            return {
                "trend_data": [],
                "average_trend": 0.0,
                "direction": "stable"
            }
        
        # 按日期分组计算平均分
        daily_ratings = {}
        for review in result.data:
            date_str = review["created_at"][:10]  # 获取YYYY-MM-DD
            if date_str not in daily_ratings:
                daily_ratings[date_str] = []
            daily_ratings[date_str].append(review["rating"])
        
        # 计算每日平均分
        trend_data = []
        for date_str in sorted(daily_ratings.keys()):
            avg_rating = sum(daily_ratings[date_str]) / len(daily_ratings[date_str])
            trend_data.append({
                "date": date_str,
                "average_rating": round(avg_rating, 1)
            })
        
        # 计算趋势方向
        if len(trend_data) >= 2:
            first_avg = trend_data[0]["average_rating"]
            last_avg = trend_data[-1]["average_rating"]
            trend_change = last_avg - first_avg
            direction = "up" if trend_change > 0 else "down" if trend_change < 0 else "stable"
        else:
            trend_change = 0.0
            direction = "stable"
        
        return {
            "trend_data": trend_data,
            "average_trend": round(trend_change, 1),
            "direction": direction
        }

    async def get_comparison_data(self, merchant_id: int) -> Dict[str, Any]:
        """获取与周边商家的对比数据"""
        # 获取当前商家的统计数据
        merchant_stats = self.supabase.table("review_statistics").select("*").eq("merchant_id", merchant_id).execute()
        
        if not merchant_stats.data:
            return {
                "merchant_rating": 0.0,
                "surrounding_average": 0.0,
                "comparison": "no_data"
            }
        
        merchant_data = merchant_stats.data[0]
        merchant_rating = merchant_data.get("average_rating", 0.0)
        
        # 模拟获取周边商家数据（实际项目中需要根据地理位置查询）
        # 这里简化处理，返回固定值
        surrounding_average = 4.3  # 模拟数据
        
        comparison = "above" if merchant_rating > surrounding_average else "below" if merchant_rating < surrounding_average else "equal"
        
        return {
            "merchant_rating": round(merchant_rating, 1),
            "surrounding_average": surrounding_average,
            "comparison": comparison
        }

    async def update_statistics_cache(self, merchant_id: int) -> bool:
        """更新统计缓存"""
        try:
            # 计算总评价数和平均评分
            reviews_result = self.supabase.table("merchant_reviews").select(
                "id, rating"
            ).eq("merchant_id", merchant_id).eq("status", "active").execute()
            
            if not reviews_result.data:
                # 如果没有评价，设置默认值
                stats_data = {
                    "merchant_id": merchant_id,
                    "total_reviews": 0,
                    "average_rating": 0.0,
                    "reply_rate": 0.0,
                    "last_7_days_trend": 0.0,
                    "updated_at": datetime.utcnow().isoformat()
                }
            else:
                total_reviews = len(reviews_result.data)
                total_rating = sum(review["rating"] for review in reviews_result.data)
                average_rating = total_rating / total_reviews if total_reviews > 0 else 0.0
                
                # 计算回复率
                replied_reviews = 0
                for review in reviews_result.data:
                    reply_result = self.supabase.table("review_replies").select("id").eq("review_id", review["id"]).execute()
                    if reply_result.data:
                        replied_reviews += 1
                
                reply_rate = replied_reviews / total_reviews if total_reviews > 0 else 0.0
                
                # 计算7天趋势
                trend_analysis = await self.get_trend_analysis(merchant_id, 7)
                
                stats_data = {
                    "merchant_id": merchant_id,
                    "total_reviews": total_reviews,
                    "average_rating": round(average_rating, 2),
                    "reply_rate": round(reply_rate, 2),
                    "last_7_days_trend": trend_analysis["average_trend"],
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            # 更新或插入统计数据
            existing = self.supabase.table("review_statistics").select("merchant_id").eq("merchant_id", merchant_id).execute()
            if existing.data:
                # 更新
                result = self.supabase.table("review_statistics").update(stats_data).eq("merchant_id", merchant_id).execute()
            else:
                # 插入
                result = self.supabase.table("review_statistics").insert(stats_data).execute()
            
            return len(result.data) > 0 if result.data else False
            
        except Exception as e:
            print(f"更新统计缓存失败: {e}")
            return False