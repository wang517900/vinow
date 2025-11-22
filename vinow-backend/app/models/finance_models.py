商家板块6财务中心
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum
from pydantic import Field, validator

from app.models.base import BaseDBModel


class SettlementStatus(str, Enum):
    """结算状态枚举"""
    PENDING = "pending"      # 待结算
    PROCESSING = "processing"  # 结算中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消


class ReconciliationStatus(str, Enum):
    """对账状态枚举"""
    PENDING = "pending"       # 待对账
    MATCHED = "matched"       # 对账成功
    MISMATCHED = "mismatched" # 对账不一致
    ERROR = "error"           # 对账错误


class InvoiceStatus(str, Enum):
    """发票状态枚举"""
    PENDING = "pending"     # 待处理
    APPROVED = "approved"   # 已批准
    REJECTED = "rejected"   # 已拒绝
    ISSUED = "issued"       # 已开票
    CANCELLED = "cancelled" # 已取消


class ReportType(str, Enum):
    """报表类型枚举"""
    DAILY = "daily"    # 日报表
    WEEKLY = "weekly"  # 周报表
    MONTHLY = "monthly" # 月报表
    CUSTOM = "custom"   # 自定义报表


class FinanceDailySummary(BaseDBModel):
    """财务日汇总表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    summary_date: date = Field(..., description="汇总日期", index=True)
    total_income: Decimal = Field(..., ge=0, description="总收入", decimal_places=2)
    order_count: int = Field(..., ge=0, description="订单数量")
    successful_orders: int = Field(..., ge=0, description="成功订单数")
    failed_orders: int = Field(..., ge=0, description="失败订单数")
    coupon_deduction: Decimal = Field(Decimal('0'), ge=0, description="优惠券抵扣", decimal_places=2)
    platform_fee: Decimal = Field(Decimal('0'), ge=0, description="平台费用", decimal_places=2)
    settlement_amount: Decimal = Field(Decimal('0'), ge=0, description="结算金额", decimal_places=2)
    refund_amount: Decimal = Field(Decimal('0'), ge=0, description="退款金额", decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        table_name = "finances_daily_summary"
    
    class Indexes:
        unique_together = [("merchant_id", "summary_date")]  # 商户和日期联合唯一


class SettlementRecord(BaseDBModel):
    """结算记录表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    settlement_no: str = Field(..., description="结算单号", max_length=50, unique=True)
    settlement_date: date = Field(..., description="结算日期", index=True)
    start_date: date = Field(..., description="结算周期开始日期")
    end_date: date = Field(..., description="结算周期结束日期")
    total_amount: Decimal = Field(..., ge=0, description="结算总金额", decimal_places=2)
    platform_fee: Decimal = Field(Decimal('0'), ge=0, description="平台费用", decimal_places=2)
    net_amount: Decimal = Field(..., ge=0, description="净结算金额", decimal_places=2)
    bank_account: str = Field(..., description="银行账户", max_length=50)
    bank_name: str = Field(..., description="银行名称", max_length=100)
    status: SettlementStatus = Field(SettlementStatus.PENDING, description="结算状态")
    settled_at: Optional[datetime] = Field(None, description="结算完成时间")
    failure_reason: Optional[str] = Field(None, description="失败原因", max_length=500)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        table_name = "finances_settlement_records"
    
    @validator('net_amount')
    def validate_net_amount(cls, v, values):
        """验证净结算金额是否正确"""
        if 'total_amount' in values and 'platform_fee' in values:
            total = values['total_amount']
            fee = values['platform_fee']
            if v != total - fee:
                raise ValueError('净结算金额应等于总金额减去平台费用')
        return v


class ReconciliationLog(BaseDBModel):
    """对账日志表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    reconciliation_date: date = Field(..., description="对账日期", index=True)
    start_date: date = Field(..., description="对账开始日期")
    end_date: date = Field(..., description="对账结束日期")
    platform_total: Decimal = Field(..., ge=0, description="平台总金额", decimal_places=2)
    bank_total: Decimal = Field(..., ge=0, description="银行总金额", decimal_places=2)
    difference: Decimal = Field(Decimal('0'), description="差异金额", decimal_places=2)
    status: ReconciliationStatus = Field(ReconciliationStatus.PENDING, description="对账状态")
    mismatched_orders: List[str] = Field(default_factory=list, description="不匹配订单列表")
    resolved_orders: List[str] = Field(default_factory=list, description="已解决订单列表")
    notes: Optional[str] = Field(None, description="备注", max_length=1000)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        table_name = "finances_reconciliation_logs"
    
    class Indexes:
        unique_together = [("merchant_id", "reconciliation_date")]  # 商户和对账日期联合唯一


class InvoiceRequest(BaseDBModel):
    """发票申请表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    invoice_no: str = Field(..., description="发票号码", max_length=50, unique=True)
    invoice_type: str = Field(..., description="发票类型", max_length=20)
    invoice_amount: Decimal = Field(..., ge=0, description="发票金额", decimal_places=2)
    tax_amount: Decimal = Field(Decimal('0'), ge=0, description="税额", decimal_places=2)
    buyer_name: str = Field(..., description="购买方名称", max_length=100)
    buyer_tax_id: Optional[str] = Field(None, description="购买方税号", max_length=50)
    invoice_content: str = Field(..., description="发票内容", max_length=500)
    apply_date: date = Field(..., description="申请日期")
    status: InvoiceStatus = Field(InvoiceStatus.PENDING, description="发票状态")
    approved_at: Optional[datetime] = Field(None, description="批准时间")
    issued_at: Optional[datetime] = Field(None, description="开票时间")
    reject_reason: Optional[str] = Field(None, description="拒绝原因", max_length=500)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        table_name = "finances_invoice_requests"
    
    @validator('invoice_amount')
    def validate_invoice_amount(cls, v):
        """验证发票金额"""
        if v <= 0:
            raise ValueError('发票金额必须大于0')
        return v


class ReportExport(BaseDBModel):
    """报表导出记录表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    report_type: ReportType = Field(..., description="报表类型")
    file_name: str = Field(..., description="文件名", max_length=200)
    file_path: str = Field(..., description="文件路径", max_length=500)
    file_size: int = Field(0, ge=0, description="文件大小(字节)")
    export_format: str = Field(..., description="导出格式", max_length=10)
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    download_count: int = Field(0, ge=0, description="下载次数")
    expires_at: datetime = Field(..., description="过期时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        table_name = "finances_report_exports"
    
    @validator('export_format')
    def validate_export_format(cls, v):
        """验证导出格式"""
        allowed_formats = ['xlsx', 'csv', 'pdf']
        if v.lower() not in allowed_formats:
            raise ValueError(f'导出格式必须是以下之一: {allowed_formats}')
        return v.lower()


class FinanceTransaction(BaseDBModel):
    """财务交易明细表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, index=True)
    transaction_no: str = Field(..., description="交易编号", max_length=50, unique=True)
    order_no: str = Field(..., description="订单编号", max_length=50, index=True)
    transaction_type: str = Field(..., description="交易类型", max_length=20)
    amount: Decimal = Field(..., description="交易金额", decimal_places=2)
    balance_before: Decimal = Field(..., description="交易前余额", decimal_places=2)
    balance_after: Decimal = Field(..., description="交易后余额", decimal_places=2)
    status: str = Field(..., description="交易状态", max_length=20)
    description: Optional[str] = Field(None, description="交易描述", max_length=200)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    class Config:
        table_name = "finances_transactions"
    
    class Indexes:
        indexes = ["merchant_id", "order_no", "created_at"]


class FinanceAccount(BaseDBModel):
    """商户财务账户表"""
    
    merchant_id: str = Field(..., description="商户ID", max_length=50, unique=True)
    account_balance: Decimal = Field(Decimal('0'), ge=0, description="账户余额", decimal_places=2)
    frozen_amount: Decimal = Field(Decimal('0'), ge=0, description="冻结金额", decimal_places=2)
    available_balance: Decimal = Field(Decimal('0'), ge=0, description="可用余额", decimal_places=2)
    currency: str = Field("CNY", description="货币类型", max_length=10)
    last_settlement_date: Optional[date] = Field(None, description="最后结算日期")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        table_name = "finances_accounts"
    
    @validator('available_balance')
    def validate_available_balance(cls, v, values):
        """验证可用余额是否正确"""
        if 'account_balance' in values and 'frozen_amount' in values:
            balance = values['account_balance']
            frozen = values['frozen_amount']
            if v != balance - frozen:
                raise ValueError('可用余额应等于账户余额减去冻结金额')
        return v