商户系统6财务中心
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, Path
from typing import Optional

from app.core.security import get_current_merchant
from app.api.dependencies import (
    get_merchant_id, get_income_flow_params, get_pagination_params
)
from app.services.finance_service import FinanceService
from app.schemas.finance import (
    DailyIncomeResponse, IncomeFlowResponse, ResponseModel, IncomeFlowParams
)
from app.models.base import PaginationParams

router = APIRouter(prefix="/finances", tags=["财务数据"])

finance_service = FinanceService()


@router.get("/daily-income", response_model=ResponseModel[DailyIncomeResponse], 
            summary="获取日收入数据", 
            description="获取指定日期的商户日收入数据，包括总收入、订单数、净收入等信息")
async def get_daily_income(
    date: Optional[str] = Query(None, description="查询日期 (YYYY-MM-DD)，默认为今天"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取日收入数据"""
    try:
        target_date = date.today()
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("日期格式错误，请使用 YYYY-MM-DD 格式")
        
        income_data = await finance_service.get_daily_income(merchant_id, target_date)
        return ResponseModel.success_response(income_data, "获取日收入数据成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取日收入数据失败: {str(e)}")


@router.get("/income-flow", response_model=ResponseModel[IncomeFlowResponse], 
            summary="获取收入流水", 
            description="获取商户的收入流水记录，支持按日期范围、支付方式、订单状态等条件筛选")
async def get_income_flow(
    params: IncomeFlowParams = Depends(get_income_flow_params),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取收入流水"""
    try:
        income_flow = await finance_service.get_income_flow(merchant_id, params)
        return ResponseModel.success_response(income_flow, "获取收入流水成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取收入流水失败: {str(e)}")


@router.get("/income-summary", response_model=ResponseModel[dict], 
            summary="获取收入汇总", 
            description="获取指定日期范围内的收入汇总信息，包括总收入、订单统计、支付方式分布等")
async def get_income_summary(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取收入汇总"""
    try:
        # 解析日期参数
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("开始日期格式错误，请使用 YYYY-MM-DD 格式")
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("结束日期格式错误，请使用 YYYY-MM-DD 格式")
        
        # 验证日期范围
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        # 这里可以实现收入汇总接口
        # 示例实现
        summary_data = {
            "start_date": parsed_start_date.isoformat() if parsed_start_date else None,
            "end_date": parsed_end_date.isoformat() if parsed_end_date else None,
            "total_income": 15000000,  # 示例数据
            "total_orders": 150,
            "avg_order_value": 100000,
            "payment_method_distribution": {
                "credit_card": 0.6,
                "bank_transfer": 0.3,
                "e_wallet": 0.1
            }
        }
        
        return ResponseModel.success_response(summary_data, "获取收入汇总成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取收入汇总失败: {str(e)}")


@router.get("/real-time-stats", response_model=ResponseModel[dict], 
            summary="获取实时统计", 
            description="获取商户的实时财务统计数据，包括今日收入、订单数、待结算金额等")
async def get_real_time_stats(
    merchant_id: str = Depends(get_merchant_id)
):
    """获取实时统计"""
    try:
        # 这里应该调用实际的服务方法获取实时数据
        stats = {
            "today_income": 1500000,
            "today_orders": 25,
            "pending_settlement": 4500000,
            "month_to_date": 45000000,
            "last_updated": datetime.now().isoformat()
        }
        return ResponseModel.success_response(stats, "获取实时统计成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取实时统计失败: {str(e)}")


@router.get("/income-trend", response_model=ResponseModel[dict], 
            summary="获取收入趋势", 
            description="获取商户的收入趋势数据，支持按日、周、月等维度查看")
async def get_income_trend(
    period: str = Query("7d", description="统计周期: 7d(近7天), 30d(近30天), 12m(近12个月)"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取收入趋势"""
    try:
        # 验证周期参数
        valid_periods = ["7d", "30d", "12m"]
        if period not in valid_periods:
            return ResponseModel.error_response(f"不支持的周期参数，支持的值: {', '.join(valid_periods)}")
        
        # 根据周期生成趋势数据
        if period == "7d":
            trend_data = {
                "labels": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                "data": [2000000, 1800000, 2200000, 2500000, 3000000, 1500000, 1200000]
            }
        elif period == "30d":
            # 简化示例数据
            trend_data = {
                "labels": [f"{i}日" for i in range(1, 31)],
                "data": [2000000 + i * 100000 for i in range(30)]
            }
        else:  # 12m
            trend_data = {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月", 
                          "7月", "8月", "9月", "10月", "11月", "12月"],
                "data": [40000000, 38000000, 42000000, 45000000, 50000000, 48000000,
                        52000000, 55000000, 53000000, 58000000, 60000000, 62000000]
            }
        
        result = {
            "period": period,
            "trend_data": trend_data
        }
        
        return ResponseModel.success_response(result, "获取收入趋势成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取收入趋势失败: {str(e)}")


@router.get("/top-products", response_model=ResponseModel[dict], 
            summary="获取热销商品", 
            description="获取商户的热销商品排行榜，按销售额或销售数量排序")
async def get_top_products(
    by: str = Query("revenue", description="排序方式: revenue(按销售额), quantity(按销售数量)"),
    limit: int = Query(10, description="返回记录数，最大100"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取热销商品"""
    try:
        # 验证参数
        if by not in ["revenue", "quantity"]:
            return ResponseModel.error_response("排序方式参数错误，支持: revenue, quantity")
        
        if limit > 100 or limit <= 0:
            return ResponseModel.error_response("记录数必须在1-100之间")
        
        # 示例数据
        top_products = [
            {"product_name": "商品A", "revenue": 5000000, "quantity": 50},
            {"product_name": "商品B", "revenue": 4500000, "quantity": 45},
            {"product_name": "商品C", "revenue": 4000000, "quantity": 40},
            {"product_name": "商品D", "revenue": 3500000, "quantity": 35},
            {"product_name": "商品E", "revenue": 3000000, "quantity": 30},
        ]
        
        # 根据排序方式调整数据
        if by == "quantity":
            top_products.sort(key=lambda x: x["quantity"], reverse=True)
        else:
            top_products.sort(key=lambda x: x["revenue"], reverse=True)
        
        # 限制返回数量
        top_products = top_products[:limit]
        
        result = {
            "sort_by": by,
            "products": top_products
        }
        
        return ResponseModel.success_response(result, "获取热销商品成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取热销商品失败: {str(e)}")