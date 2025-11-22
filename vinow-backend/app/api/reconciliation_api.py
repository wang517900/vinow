商户系统6财务中心
from fastapi import APIRouter, Depends, Query, Body
from typing import Optional, List
from datetime import date, datetime

from app.core.security import get_current_merchant
from app.api.dependencies import get_merchant_id, get_pagination_params
from app.services.reconciliation_service import ReconciliationService
from app.schemas.finance import (
    ReconciliationRunRequest, ReconciliationResult, DisputeApplicationRequest,
    ResponseModel, ReconciliationHistoryParams, PaginatedResponse
)

router = APIRouter(prefix="/finances/reconciliation", tags=["对账中心"])

reconciliation_service = ReconciliationService()


@router.post("/run", response_model=ResponseModel[ReconciliationResult],
             summary="执行对账",
             description="执行指定日期范围的对账任务，支持强制重新对账")
async def run_reconciliation(
    request: ReconciliationRunRequest = Body(..., description="对账执行请求参数"),
    merchant_id: str = Depends(get_merchant_id)
):
    """执行对账"""
    try:
        # 参数验证
        if not request.start_date or not request.end_date:
            return ResponseModel.error_response("开始日期和结束日期不能为空")
        
        if request.start_date > request.end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        # 检查日期范围是否合理（不超过3个月）
        date_diff = (request.end_date - request.start_date).days
        if date_diff > 90:
            return ResponseModel.error_response("对账日期范围不能超过90天")
        
        result = await reconciliation_service.run_reconciliation(
            merchant_id, 
            request.start_date, 
            request.end_date,
            request.force_reconcile
        )
        
        if result:
            return ResponseModel.success_response(result, "对账执行成功")
        else:
            return ResponseModel.error_response("对账执行失败")
            
    except Exception as e:
        return ResponseModel.error_response(f"对账执行失败: {str(e)}")


@router.get("/history", response_model=ResponseModel[PaginatedResponse[ReconciliationResult]],
            summary="获取对账历史",
            description="获取商户的对账历史记录，支持分页查询和状态筛选")
async def get_reconciliation_history(
    params: ReconciliationHistoryParams = Depends(get_pagination_params),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取对账历史"""
    try:
        # 参数验证
        if params.start_date and params.end_date and params.start_date > params.end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        results = await reconciliation_service.get_reconciliation_history(
            merchant_id, params
        )
        return ResponseModel.success_response(results, "获取对账历史成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取对账历史失败: {str(e)}")


@router.get("/results", response_model=ResponseModel[List[ReconciliationResult]],
            summary="获取对账结果",
            description="获取指定对账记录的详细结果信息")
async def get_reconciliation_results(
    reconciliation_id: Optional[str] = Query(None, description="对账记录ID"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取对账结果"""
    try:
        results = await reconciliation_service.get_reconciliation_results(
            merchant_id, reconciliation_id
        )
        return ResponseModel.success_response(results, "获取对账结果成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取对账结果失败: {str(e)}")


@router.post("/dispute", response_model=ResponseModel[bool],
             summary="提交争议申请",
             description="对对账不一致的订单提交争议申请，需要提供相关证据")
async def submit_dispute(
    request: DisputeApplicationRequest = Body(..., description="争议申请请求参数"),
    merchant_id: str = Depends(get_merchant_id)
):
    """提交争议申请"""
    try:
        # 参数验证
        if not request.reconciliation_id:
            return ResponseModel.error_response("对账记录ID不能为空")
        
        if not request.order_ids or len(request.order_ids) == 0:
            return ResponseModel.error_response("争议订单列表不能为空")
        
        if not request.dispute_reason or len(request.dispute_reason.strip()) == 0:
            return ResponseModel.error_response("争议原因不能为空")
        
        if len(request.dispute_reason) > 1000:
            return ResponseModel.error_response("争议原因长度不能超过1000字符")
        
        if request.evidence and len(request.evidence) > 10:
            return ResponseModel.error_response("证据文件数量不能超过10个")
        
        result = await reconciliation_service.submit_dispute(
            merchant_id,
            request.reconciliation_id,
            request.order_ids,
            request.dispute_reason,
            request.evidence
        )
        
        if result:
            return ResponseModel.success_response(result, "争议申请提交成功")
        else:
            return ResponseModel.error_response("争议申请提交失败")
            
    except Exception as e:
        return ResponseModel.error_response(f"争议申请提交失败: {str(e)}")


@router.get("/dispute-history", response_model=ResponseModel[dict],
            summary="获取争议历史",
            description="获取商户提交的争议申请历史记录，支持分页查询")
async def get_dispute_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="争议状态: pending, resolved, rejected"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取争议历史"""
    try:
        # 参数验证
        if page <= 0:
            return ResponseModel.error_response("页码必须大于0")
        
        if page_size <= 0 or page_size > 100:
            return ResponseModel.error_response("每页数量必须在1-100之间")
        
        # 验证状态参数
        valid_statuses = [None, "pending", "resolved", "rejected"]
        if status and status not in valid_statuses:
            return ResponseModel.error_response("争议状态参数错误")
        
        # 这里应该实现争议历史查询逻辑
        # 示例数据
        dispute_history = {
            "items": [
                {
                    "dispute_id": "DISP001",
                    "reconciliation_id": "REC001",
                    "order_id": "ORDER001",
                    "amount": 1000000,
                    "status": "resolved",
                    "created_at": "2023-01-01T10:00:00",
                    "resolved_at": "2023-01-05T15:00:00"
                }
            ],
            "total": 1,
            "page": page,
            "page_size": page_size,
            "total_pages": 1
        }
        
        return ResponseModel.success_response(dispute_history, "获取争议历史成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取争议历史失败: {str(e)}")


@router.get("/mismatch-analysis", response_model=ResponseModel[dict],
            summary="获取不匹配分析",
            description="对指定对账记录中的不匹配项进行详细分析")
async def get_mismatch_analysis(
    reconciliation_id: str = Query(..., description="对账记录ID"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取不匹配分析"""
    try:
        # 参数验证
        if not reconciliation_id:
            return ResponseModel.error_response("对账记录ID不能为空")
        
        # 验证对账记录是否存在且属于该商户
        reconciliation_result = await reconciliation_service.get_reconciliation_results(
            merchant_id, reconciliation_id
        )
        
        if not reconciliation_result:
            return ResponseModel.error_response("对账记录不存在或无权访问")
        
        # 这里应该实现不匹配分析逻辑
        # 示例数据
        analysis_data = {
            "reconciliation_id": reconciliation_id,
            "total_mismatched": 5,
            "amount_difference": 2500000,
            "common_causes": [
                "银行入账延迟",
                "退款处理差异",
                "手续费计算差异"
            ],
            "suggestions": [
                "检查银行流水是否完整",
                "核实退款订单状态",
                "核对手续费计算规则"
            ],
            "mismatch_details": [
                {
                    "order_id": "ORDER001",
                    "platform_amount": 1000000,
                    "bank_amount": 980000,
                    "difference": 20000,
                    "cause": "手续费扣除"
                },
                {
                    "order_id": "ORDER002",
                    "platform_amount": 500000,
                    "bank_amount": 0,
                    "difference": 500000,
                    "cause": "银行未入账"
                }
            ]
        }
        
        return ResponseModel.success_response(analysis_data, "获取不匹配分析成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取不匹配分析失败: {str(e)}")


@router.get("/{reconciliation_id}", response_model=ResponseModel[ReconciliationResult],
            summary="获取对账详情",
            description="根据对账ID获取详细的对账结果信息")
async def get_reconciliation_detail(
    reconciliation_id: str = Path(..., description="对账记录ID"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取对账详情"""
    try:
        # 参数验证
        if not reconciliation_id:
            return ResponseModel.error_response("对账记录ID不能为空")
        
        results = await reconciliation_service.get_reconciliation_results(
            merchant_id, reconciliation_id
        )
        
        if not results:
            return ResponseModel.error_response("对账记录不存在或无权访问")
        
        return ResponseModel.success_response(results[0], "获取对账详情成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取对账详情失败: {str(e)}")


@router.get("/summary", response_model=ResponseModel[dict],
            summary="获取对账汇总",
            description="获取商户的对账汇总统计信息")
async def get_reconciliation_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取对账汇总"""
    try:
        # 参数验证
        if start_date and end_date and start_date > end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        # 设置默认日期范围（最近30天）
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        # 这里应该实现对账汇总逻辑
        # 示例数据
        summary_data = {
            "period": f"{start_date} 至 {end_date}",
            "total_reconciliations": 4,
            "matched_count": 3,
            "mismatched_count": 1,
            "match_rate": 75.0,
            "total_disputes": 2,
            "resolved_disputes": 1,
            "total_amount": 50000000,
            "discrepancy_amount": 1500000
        }
        
        return ResponseModel.success_response(summary_data, "获取对账汇总成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取对账汇总失败: {str(e)}")


@router.post("/{reconciliation_id}/export", response_model=ResponseModel[dict],
             summary="导出对账报告",
             description="导出指定对账记录的详细报告")
async def export_reconciliation_report(
    reconciliation_id: str = Path(..., description="对账记录ID"),
    format: str = Query("excel", description="导出格式: excel, csv, pdf"),
    merchant_id: str = Depends(get_merchant_id)
):
    """导出对账报告"""
    try:
        # 参数验证
        if not reconciliation_id:
            return ResponseModel.error_response("对账记录ID不能为空")
        
        valid_formats = ["excel", "csv", "pdf"]
        if format not in valid_formats:
            return ResponseModel.error_response(f"不支持的导出格式，支持: {', '.join(valid_formats)}")
        
        # 验证对账记录是否存在
        results = await reconciliation_service.get_reconciliation_results(
            merchant_id, reconciliation_id
        )
        
        if not results:
            return ResponseModel.error_response("对账记录不存在或无权访问")
        
        # 这里应该实现导出逻辑
        # 示例响应
        export_info = {
            "export_id": f"EXP{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "reconciliation_id": reconciliation_id,
            "format": format,
            "file_url": f"https://example.com/reports/{reconciliation_id}.{format}",
            "file_size": "2.5MB",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        return ResponseModel.success_response(export_info, "对账报告导出任务已启动")
        
    except Exception as e:
        return ResponseModel.error_response(f"导出对账报告失败: {str(e)}")