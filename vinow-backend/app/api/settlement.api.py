商户系统6财务中心
from fastapi import APIRouter, Depends, Query, Body
from typing import Optional
from datetime import date, datetime

from app.core.security import get_current_merchant
from app.api.dependencies import (
    get_merchant_id, get_settlement_history_params, get_pagination_params
)
from app.services.settlement_service import SettlementService
from app.schemas.finance import (
    SettlementStatusResponse, SettlementVerifyRequest, NextSettlementEstimate,
    ResponseModel, SettlementHistoryParams, PaginatedResponse, SettlementHistoryItem
)

router = APIRouter(prefix="/finances/settlement", tags=["结算管理"])

settlement_service = SettlementService()


@router.get("/status", response_model=ResponseModel[SettlementStatusResponse],
            summary="获取结算状态",
            description="获取商户当前的结算状态信息，包括已结算金额、待结算金额、下次结算时间等")
async def get_settlement_status(
    merchant_id: str = Depends(get_merchant_id)
):
    """获取结算状态"""
    try:
        status_data = await settlement_service.get_settlement_status(merchant_id)
        return ResponseModel.success_response(status_data, "获取结算状态成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取结算状态失败: {str(e)}")


@router.get("/history", response_model=ResponseModel[PaginatedResponse[SettlementHistoryItem]],
            summary="获取结算历史",
            description="获取商户的结算历史记录，支持分页查询和状态筛选")
async def get_settlement_history(
    params: SettlementHistoryParams = Depends(get_settlement_history_params),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取结算历史"""
    try:
        history_data = await settlement_service.get_settlement_history(merchant_id, params)
        return ResponseModel.success_response(history_data, "获取结算历史成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取结算历史失败: {str(e)}")


@router.post("/verify", response_model=ResponseModel[bool],
             summary="确认结算",
             description="商户确认已完成的结算记录，需要提供结算ID和验证码")
async def verify_settlement(
    request: SettlementVerifyRequest = Body(..., description="结算确认请求参数"),
    merchant_id: str = Depends(get_merchant_id)
):
    """确认结算"""
    try:
        # 验证必要参数
        if not request.settlement_id:
            return ResponseModel.error_response("结算ID不能为空")
        
        result = await settlement_service.verify_settlement(
            merchant_id, request.settlement_id, request.verification_code
        )
        return ResponseModel.success_response(result, "结算确认成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"结算确认失败: {str(e)}")


@router.get("/next-estimate", response_model=ResponseModel[NextSettlementEstimate],
            summary="获取下次结算预估",
            description="获取商户下次结算的预估信息，包括预估金额、结算日期、剩余天数等")
async def get_next_settlement_estimate(
    merchant_id: str = Depends(get_merchant_id)
):
    """获取下次结算预估"""
    try:
        estimate = await settlement_service.get_next_settlement_estimate(merchant_id)
        return ResponseModel.success_response(estimate, "获取下次结算预估成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取下次结算预估失败: {str(e)}")


@router.post("/request-early", response_model=ResponseModel[dict],
             summary="申请提前结算",
             description="商户申请提前结算指定金额，需要提供申请金额和原因")
async def request_early_settlement(
    amount: float = Query(..., description="申请金额", gt=0),
    reason: str = Query(..., description="申请原因", min_length=1, max_length=500),
    merchant_id: str = Depends(get_merchant_id)
):
    """申请提前结算"""
    try:
        # 参数验证
        if amount <= 0:
            return ResponseModel.error_response("申请金额必须大于0")
        
        if not reason or len(reason.strip()) == 0:
            return ResponseModel.error_response("申请原因不能为空")
        
        if len(reason) > 500:
            return ResponseModel.error_response("申请原因长度不能超过500字符")
        
        # 检查商户是否有足够的待结算金额
        status_data = await settlement_service.get_settlement_status(merchant_id)
        if amount > float(status_data.pending_amount):
            return ResponseModel.error_response("申请金额不能超过待结算金额")
        
        # 这里可以实现提前结算申请逻辑
        # 示例：创建提前结算申请记录
        early_settlement_request = {
            "request_id": f"ES{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant_id": merchant_id,
            "amount": amount,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "estimated_process_time": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=5).isoformat()
        }
        
        # 实际应该保存到数据库
        # await db.insert_data("early_settlement_requests", early_settlement_request)
        
        result = {
            "request_id": early_settlement_request["request_id"],
            "amount": amount,
            "status": "pending",
            "estimated_process_time": early_settlement_request["estimated_process_time"]
        }
        
        return ResponseModel.success_response(result, "提前结算申请已提交")
        
    except Exception as e:
        return ResponseModel.error_response(f"提前结算申请失败: {str(e)}")


@router.get("/details/{settlement_id}", response_model=ResponseModel[dict],
            summary="获取结算详情",
            description="根据结算ID获取详细的结算信息，包括结算明细、费用构成等")
async def get_settlement_details(
    settlement_id: str = Path(..., description="结算记录ID"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取结算详情"""
    try:
        if not settlement_id:
            return ResponseModel.error_response("结算ID不能为空")
        
        # 获取结算记录详情
        settlement_record = await settlement_service._get_settlement_record(settlement_id, merchant_id)
        if not settlement_record:
            return ResponseModel.error_response("结算记录不存在或无权访问")
        
        # 获取结算明细（示例数据）
        settlement_details = {
            "settlement_info": {
                "settlement_no": settlement_record.settlement_no,
                "settlement_date": settlement_record.settlement_date.isoformat(),
                "start_date": settlement_record.start_date.isoformat(),
                "end_date": settlement_record.end_date.isoformat(),
                "status": settlement_record.status.value
            },
            "amount_breakdown": {
                "total_amount": float(settlement_record.total_amount),
                "platform_fee": float(settlement_record.platform_fee),
                "refund_amount": float(getattr(settlement_record, 'refund_amount', 0)),
                "net_amount": float(settlement_record.net_amount)
            },
            "bank_info": {
                "bank_name": getattr(settlement_record, 'bank_name', 'Vietcombank'),
                "bank_account": settlement_record.bank_account
            },
            "order_summary": {
                "total_orders": 150,  # 示例数据
                "successful_orders": 145,
                "refunded_orders": 5
            }
        }
        
        return ResponseModel.success_response(settlement_details, "获取结算详情成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取结算详情失败: {str(e)}")


@router.get("/bank-accounts", response_model=ResponseModel[list],
            summary="获取结算银行账户",
            description="获取商户可用于结算的银行账户列表")
async def get_settlement_bank_accounts(
    merchant_id: str = Depends(get_merchant_id)
):
    """获取结算银行账户"""
    try:
        # 示例银行账户数据
        bank_accounts = [
            {
                "account_id": "acc_001",
                "bank_name": "Vietcombank",
                "account_number": "****6789",
                "account_holder": "商户名称",
                "is_default": True
            },
            {
                "account_id": "acc_002",
                "bank_name": "Techcombank",
                "account_number": "****1234",
                "account_holder": "商户名称",
                "is_default": False
            }
        ]
        
        return ResponseModel.success_response(bank_accounts, "获取银行账户列表成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取银行账户列表失败: {str(e)}")


@router.put("/bank-accounts/default/{account_id}", response_model=ResponseModel[bool],
            summary="设置默认结算账户",
            description="设置商户的默认结算银行账户")
async def set_default_bank_account(
    account_id: str = Path(..., description="银行账户ID"),
    merchant_id: str = Depends(get_merchant_id)
):
    """设置默认结算账户"""
    try:
        if not account_id:
            return ResponseModel.error_response("银行账户ID不能为空")
        
        # 验证账户是否存在且属于该商户
        # 这里应该是实际的数据库验证逻辑
        # account = await db.get_merchant_bank_account(merchant_id, account_id)
        # if not account:
        #     return ResponseModel.error_response("银行账户不存在或无权访问")
        
        # 设置为默认账户
        # await db.set_default_bank_account(merchant_id, account_id)
        
        return ResponseModel.success_response(True, "默认结算账户设置成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"设置默认结算账户失败: {str(e)}")


@router.get("/schedule", response_model=ResponseModel[dict],
            summary="获取结算计划",
            description="获取商户的结算计划信息，包括结算周期、规则等")
async def get_settlement_schedule(
    merchant_id: str = Depends(get_merchant_id)
):
    """获取结算计划"""
    try:
        # 示例结算计划数据
        schedule_info = {
            "settlement_cycle": "weekly",  # weekly, biweekly, monthly
            "settlement_day": "monday",    # 具体的结算日
            "cut_off_time": "23:59",       # 截止时间
            "process_time": 2,             # 处理时间（工作日）
            "min_amount": 100000,          # 最低结算金额
            "next_settlement_date": (date.today().replace(day=1) + timedelta(days=32)).replace(day=5).isoformat()
        }
        
        return ResponseModel.success_response(schedule_info, "获取结算计划成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取结算计划失败: {str(e)}")