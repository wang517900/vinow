商户系统6财务中心
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Optional
from datetime import datetime, date, timedelta
import os

from app.core.security import get_current_merchant
from app.api.dependencies import get_merchant_id, get_report_params
from app.services.report_service import ReportService
from app.schemas.finance import (
    ReportExportRequest, ReportExportResponse, FinancialReportData,
    ResponseModel, ReportType
)
from app.utils.export_utils import ExportUtils

router = APIRouter(prefix="/finances/reports", tags=["报表系统"])

report_service = ReportService()
export_utils = ExportUtils()


@router.get("/daily", response_model=ResponseModel[FinancialReportData],
            summary="获取日报表",
            description="获取指定日期的商户日报表数据，包括收入、订单、退款等统计信息")
async def get_daily_report(
    date: Optional[str] = Query(None, description="查询日期 (YYYY-MM-DD)，默认为今天"),
    include_details: bool = Query(False, description="是否包含明细数据"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取日报表"""
    try:
        report_date = datetime.now().date()
        if date:
            try:
                report_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("日期格式错误，请使用 YYYY-MM-DD 格式")
        
        report_data = await report_service.generate_daily_report(
            merchant_id, report_date, include_details
        )
        return ResponseModel.success_response(report_data, "获取日报表成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取日报表失败: {str(e)}")


@router.get("/weekly", response_model=ResponseModel[FinancialReportData],
            summary="获取周报表",
            description="获取指定日期范围的商户周报表数据")
async def get_weekly_report(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    include_details: bool = Query(False, description="是否包含明细数据"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取周报表"""
    try:
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("开始日期格式错误，请使用 YYYY-MM-DD 格式")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return ResponseModel.error_response("结束日期格式错误，请使用 YYYY-MM-DD 格式")
        
        # 验证日期范围
        if start_dt and end_dt and start_dt > end_dt:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        report_data = await report_service.generate_weekly_report(
            merchant_id, start_dt, end_dt, include_details
        )
        return ResponseModel.success_response(report_data, "获取周报表成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取周报表失败: {str(e)}")


@router.get("/monthly", response_model=ResponseModel[FinancialReportData],
            summary="获取月报表",
            description="获取指定月份的商户月报表数据")
async def get_monthly_report(
    month: Optional[str] = Query(None, description="月份 (YYYY-MM)"),
    include_details: bool = Query(False, description="是否包含明细数据"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取月报表"""
    try:
        report_month = datetime.now().date().replace(day=1)
        if month:
            try:
                report_month = datetime.strptime(month, "%Y-%m").date()
                # 确保是月份的第一天
                report_month = report_month.replace(day=1)
            except ValueError:
                return ResponseModel.error_response("月份格式错误，请使用 YYYY-MM 格式")
        
        report_data = await report_service.generate_monthly_report(
            merchant_id, report_month, include_details
        )
        return ResponseModel.success_response(report_data, "获取月报表成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取月报表失败: {str(e)}")


@router.post("/export", response_model=ResponseModel[ReportExportResponse],
             summary="导出报表",
             description="导出指定类型的报表数据为文件")
async def export_report(
    request: ReportExportRequest = Body(..., description="报表导出请求参数"),
    merchant_id: str = Depends(get_merchant_id)
):
    """导出报表"""
    try:
        # 参数验证
        if not request.report_type:
            return ResponseModel.error_response("报表类型不能为空")
        
        if request.format not in ["excel", "csv"]:
            return ResponseModel.error_response("不支持的导出格式，支持: excel, csv")
        
        # 验证日期范围
        if request.start_date and request.end_date and request.start_date > request.end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        # 检查日期范围合理性
        if request.start_date and request.end_date:
            date_diff = (request.end_date - request.start_date).days
            if date_diff > 365:
                return ResponseModel.error_response("导出日期范围不能超过365天")
        
        export_result = await report_service.export_report(merchant_id, request)
        return ResponseModel.success_response(export_result, "报表导出成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"报表导出失败: {str(e)}")


@router.get("/export-history", response_model=ResponseModel[list],
            summary="获取导出历史",
            description="获取商户的报表导出历史记录")
async def get_export_history(
    limit: int = Query(10, ge=1, le=50, description="返回记录数，范围1-50"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取导出历史"""
    try:
        history = await report_service.get_export_history(merchant_id, limit)
        return ResponseModel.success_response(history, "获取导出历史成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取导出历史失败: {str(e)}")


@router.get("/download/{filename}",
            summary="下载报表文件",
            description="根据文件名下载已导出的报表文件")
async def download_report(
    filename: str,
    merchant_id: str = Depends(get_merchant_id)
):
    """下载报表文件"""
    try:
        # 验证文件名参数
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 验证文件是否存在且属于该商户
        export_record = await _validate_file_access(filename, merchant_id)
        
        file_path = export_record.file_path
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查文件是否过期
        if hasattr(export_record, 'expires_at') and export_record.expires_at:
            expires_at = datetime.fromisoformat(export_record.expires_at)
            if datetime.now() > expires_at:
                raise HTTPException(status_code=410, detail="文件已过期")
        
        # 更新下载次数
        await _update_download_count(export_record.id)
        
        # 返回文件下载
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")


@router.delete("/export/{export_id}", response_model=ResponseModel[bool],
               summary="删除导出记录",
               description="删除指定的报表导出记录及其文件")
async def delete_export_record(
    export_id: str,
    merchant_id: str = Depends(get_merchant_id)
):
    """删除导出记录"""
    try:
        # 验证记录ID参数
        if not export_id:
            return ResponseModel.error_response("导出记录ID不能为空")
        
        # 验证记录所有权
        from app.database.supabase_client import db
        
        records = await db.execute_query(
            "finances_report_exports",
            filters={"id": export_id, "merchant_id": merchant_id},
            limit=1
        )
        
        if not records:
            return ResponseModel.error_response("导出记录不存在或无权访问")
        
        # 删除文件
        file_path = records[0].get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                # 记录日志但不中断删除过程
                print(f"删除文件失败: {str(e)}")
        
        # 删除数据库记录
        await db.delete_data(
            "finances_report_exports",
            {"id": export_id}
        )
        
        return ResponseModel.success_response(True, "删除导出记录成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"删除导出记录失败: {str(e)}")


@router.get("/summary", response_model=ResponseModel[dict],
            summary="获取报表汇总",
            description="获取商户的报表汇总统计信息")
async def get_report_summary(
    report_type: ReportType = Query(..., description="报表类型: daily, weekly, monthly"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取报表汇总"""
    try:
        # 参数验证
        if not report_type:
            return ResponseModel.error_response("报表类型不能为空")
        
        # 验证日期范围
        if start_date and end_date and start_date > end_date:
            return ResponseModel.error_response("开始日期不能晚于结束日期")
        
        # 设置默认日期范围
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        # 这里应该实现报表汇总逻辑
        # 示例数据
        summary_data = {
            "report_type": report_type.value,
            "period": f"{start_date} 至 {end_date}",
            "total_income": 15000000,
            "total_orders": 150,
            "avg_order_value": 100000,
            "refund_rate": 2.5,
            "growth_rate": 15.0
        }
        
        return ResponseModel.success_response(summary_data, "获取报表汇总成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取报表汇总失败: {str(e)}")


@router.get("/trends", response_model=ResponseModel[dict],
            summary="获取趋势分析",
            description="获取商户的财务数据趋势分析")
async def get_report_trends(
    period: str = Query("7d", description="统计周期: 7d(近7天), 30d(近30天), 12m(近12个月)"),
    merchant_id: str = Depends(get_merchant_id)
):
    """获取趋势分析"""
    try:
        # 验证周期参数
        valid_periods = ["7d", "30d", "12m"]
        if period not in valid_periods:
            return ResponseModel.error_response(f"不支持的周期参数，支持: {', '.join(valid_periods)}")
        
        # 这里应该实现趋势分析逻辑
        # 示例数据
        if period == "7d":
            trend_data = {
                "labels": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                "income": [2000000, 1800000, 2200000, 2500000, 3000000, 1500000, 1200000],
                "orders": [20, 18, 22, 25, 30, 15, 12]
            }
        elif period == "30d":
            trend_data = {
                "labels": [f"{i}日" for i in range(1, 31)],
                "income": [2000000 + i * 100000 for i in range(30)],
                "orders": [20 + i for i in range(30)]
            }
        else:  # 12m
            trend_data = {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月", 
                          "7月", "8月", "9月", "10月", "11月", "12月"],
                "income": [40000000, 38000000, 42000000, 45000000, 50000000, 48000000,
                          52000000, 55000000, 53000000, 58000000, 60000000, 62000000],
                "orders": [400, 380, 420, 450, 500, 480, 520, 550, 530, 580, 600, 620]
            }
        
        result = {
            "period": period,
            "trend_data": trend_data
        }
        
        return ResponseModel.success_response(result, "获取趋势分析成功")
        
    except Exception as e:
        return ResponseModel.error_response(f"获取趋势分析失败: {str(e)}")


async def _validate_file_access(filename: str, merchant_id: str):
    """验证文件访问权限"""
    from app.database.supabase_client import db
    
    records = await db.execute_query(
        "finances_report_exports",
        filters={"file_name": filename, "merchant_id": merchant_id},
        limit=1
    )
    
    if not records:
        raise HTTPException(status_code=404, detail="文件不存在或无权访问")
    
    return records[0]


async def _update_download_count(export_id: str):
    """更新下载次数"""
    from app.database.supabase_client import db
    
    records = await db.execute_query(
        "finances_report_exports",
        filters={"id": export_id},
        limit=1
    )
    
    if records:
        current_count = records[0].get('download_count', 0)
        await db.update_data(
            "finances_report_exports",
            {"download_count": current_count + 1},
            {"id": export_id}
        )