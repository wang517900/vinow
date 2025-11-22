# app/content_marketing/api.py
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form
from app.content_marketing.services import ContentMarketingService
from app.content_marketing.models import (
    ContentInDB, ContentCreate, ContentUpdate, ContentStats,
    CollaborationInDB, CollaborationCreate, CollaborationStatus,
    CollaborationApplicationInDB, CollaborationApplicationCreate, ApplicationStatus,
    ContentMarketingDashboard, ContentType, ContentStatus
)
from app.schemas.order import OrderResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_content_service(merchant_id: str = Query(..., description="商家ID")):
    """获取内容营销服务实例"""
    return ContentMarketingService(merchant_id)

# ===== 内容管理API =====

@router.post("/contents", response_model=OrderResponse)
async def create_content(
    content_data: ContentCreate,
    service: ContentMarketingService = Depends(get_content_service)
):
    """创建内容"""
    content = await service.create_content(content_data)
    if not content:
        raise HTTPException(status_code=400, detail="创建内容失败")
    
    return OrderResponse(message="内容创建成功", data=content)

@router.get("/contents", response_model=OrderResponse)
async def list_contents(
    content_type: Optional[ContentType] = Query(None, description="内容类型"),
    status: Optional[ContentStatus] = Query(None, description="内容状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取内容列表"""
    contents, total_count = await service.list_contents(content_type, status, page, page_size)
    
    return OrderResponse(
        message="获取内容列表成功",
        data={
            "contents": contents,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    )

@router.get("/contents/{content_id}", response_model=OrderResponse)
async def get_content(
    content_id: str,
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取内容详情"""
    content = await service.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    return OrderResponse(message="获取内容成功", data=content)

@router.put("/contents/{content_id}", response_model=OrderResponse)
async def update_content(
    content_id: str,
    update_data: ContentUpdate,
    service: ContentMarketingService = Depends(get_content_service)
):
    """更新内容"""
    content = await service.update_content(content_id, update_data)
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在或更新失败")
    
    return OrderResponse(message="内容更新成功", data=content)

@router.get("/contents/{content_id}/stats", response_model=OrderResponse)
async def get_content_stats(
    content_id: str,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取内容统计数据"""
    stats = await service.get_content_stats(content_id, days)
    
    return OrderResponse(message="获取内容统计成功", data=stats)

# ===== 合作任务API =====

@router.post("/collaborations", response_model=OrderResponse)
async def create_collaboration(
    collaboration_data: CollaborationCreate,
    service: ContentMarketingService = Depends(get_content_service)
):
    """创建合作任务"""
    collaboration = await service.create_collaboration(collaboration_data)
    if not collaboration:
        raise HTTPException(status_code=400, detail="创建合作任务失败")
    
    return OrderResponse(message="合作任务创建成功", data=collaboration)

@router.get("/collaborations", response_model=OrderResponse)
async def list_collaborations(
    status: Optional[CollaborationStatus] = Query(None, description="任务状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取合作任务列表"""
    collaborations, total_count = await service.list_collaborations(status, page, page_size)
    
    return OrderResponse(
        message="获取合作任务列表成功",
        data={
            "collaborations": collaborations,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    )

@router.post("/collaborations/{collaboration_id}/applications", response_model=OrderResponse)
async def create_application(
    collaboration_id: str,
    application_data: CollaborationApplicationCreate,
    service: ContentMarketingService = Depends(get_content_service)
):
    """创建合作申请"""
    application_data.collaboration_id = collaboration_id
    application = await service.create_application(application_data)
    if not application:
        raise HTTPException(status_code=400, detail="创建合作申请失败")
    
    return OrderResponse(message="合作申请提交成功", data=application)

@router.get("/applications", response_model=OrderResponse)
async def list_applications(
    collaboration_id: Optional[str] = Query(None, description="合作任务ID"),
    status: Optional[ApplicationStatus] = Query(None, description="申请状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取合作申请列表"""
    applications, total_count = await service.list_applications(collaboration_id, status, page, page_size)
    
    return OrderResponse(
        message="获取合作申请列表成功",
        data={
            "applications": applications,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    )

@router.put("/applications/{application_id}/status", response_model=OrderResponse)
async def update_application_status(
    application_id: str,
    status: ApplicationStatus,
    final_content_id: Optional[str] = Query(None, description="最终内容ID"),
    service: ContentMarketingService = Depends(get_content_service)
):
    """更新申请状态"""
    application = await service.update_application_status(application_id, status, final_content_id)
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在或更新失败")
    
    return OrderResponse(message="申请状态更新成功", data=application)

# ===== 数据看板API =====

@router.get("/dashboard", response_model=OrderResponse)
async def get_content_dashboard(
    service: ContentMarketingService = Depends(get_content_service)
):
    """获取内容营销数据看板"""
    dashboard_data = await service.get_dashboard_data()
    
    return OrderResponse(message="获取数据看板成功", data=dashboard_data)