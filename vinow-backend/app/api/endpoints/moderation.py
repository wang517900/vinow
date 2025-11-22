内容系统
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from pydantic import BaseModel

from app.models.moderation import (
    ModerationDecision, ModerationResult, ModerationQueueItem, ModerationStats,
    ModerationAction, ModerationPriority
)
from app.services.moderation_service import ModerationService
from app.api.v1.dependencies import (
    GetModerationService, GetCurrentActiveUser, RequireModerator, RequireAdmin
)
from app.utils.logger import logger

# 创建审核路由
router = APIRouter(prefix="/moderation", tags=["moderation"])

class ModerationQueueResponse(BaseModel):
    """审核队列响应模型"""
    items: List[ModerationQueueItem]
    total: int
    page: int
    size: int

class BulkModerationDecision(BaseModel):
    """批量审核决定模型"""
    content_ids: List[str]
    action: ModerationAction
    reason: str
    risk_level: Optional[str] = "medium"

class ModeratorWorkload(BaseModel):
    """审核员工作负载模型"""
    moderator_id: str
    assigned_count: int
    completed_today: int
    average_processing_time: float

@router.post("/content/{content_id}/submit")
async def submit_content_for_moderation(
    content_id: str,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """提交内容进行审核
    
    将指定内容提交到审核队列，等待审核员处理。
    """
    try:
        queue_item = await moderation_service.submit_for_moderation(content_id)
        
        return {
            "message": "内容已提交审核",
            "queue_item_id": queue_item.id,
            "priority": queue_item.priority
        }
        
    except Exception as e:
        logger.error(f"提交内容审核失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="提交审核失败"
        )

@router.get("/queue", response_model=ModerationQueueResponse)
async def get_moderation_queue(
    status: str = Query("pending", description="队列状态: pending, assigned, completed"),
    priority: str = Query(None, description="优先级过滤: low, normal, high"),
    assigned_to: str = Query(None, description="分配给指定审核员"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    page: int = Query(1, ge=1, description="页码"),
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)
):
    """获取审核队列（需要审核员权限）
    
    获取当前审核队列中的内容，支持状态、优先级和审核员过滤。
    """
    try:
        # 构建过滤条件
        filters = {"status": status}
        if priority:
            filters["priority"] = priority
        if assigned_to:
            filters["assigned_to"] = assigned_to
        
        # 获取审核队列项
        queue_items = await moderation_service.db.select(
            "moderation_queue",
            filters=filters,
            limit=limit * page  # 获取足够的数据用于分页
        )
        
        # 按创建时间排序
        queue_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # 分页处理
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = queue_items[start_idx:end_idx]
        
        # 转换为模型对象
        items = [ModerationQueueItem(**item) for item in paginated_items]
        
        response = ModerationQueueResponse(
            items=items,
            total=len(queue_items),
            page=page,
            size=len(items)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"获取审核队列失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审核队列失败"
        )

@router.post("/queue/{queue_item_id}/assign")
async def assign_moderation_task(
    queue_item_id: str,
    moderator_id: str = Query(..., description="审核员ID"),
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireAdmin)  # 只有管理员可以分配任务
):
    """分配审核任务给审核员
    
    管理员将审核任务分配给指定的审核员。
    """
    try:
        success = await moderation_service.assign_moderation_task(queue_item_id, moderator_id)
        
        if success:
            return {"message": "审核任务分配成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="审核任务分配失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配审核任务失败 {queue_item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分配审核任务失败"
        )

@router.post("/content/{content_id}/decision")
async def submit_moderation_decision(
    content_id: str,
    decision: ModerationDecision,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)  # 需要审核员权限
):
    """提交审核决定
    
    审核员对内容做出最终审核决定。
    """
    try:
        moderator_id = str(current_user["id"])
        result = await moderation_service.process_moderation_decision(
            content_id, decision, moderator_id
        )
        
        return {
            "message": "审核决定已提交",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"提交审核决定失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="提交审核决定失败"
        )

@router.post("/content/bulk-decision")
async def submit_bulk_moderation_decisions(
    bulk_decision: BulkModerationDecision,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)
):
    """批量提交审核决定
    
    审核员可以批量处理多个内容的审核决定。
    """
    try:
        moderator_id = str(current_user["id"])
        
        # 构建决策列表
        decisions = []
        for content_id in bulk_decision.content_ids:
            decision = ModerationDecision(
                action=bulk_decision.action,
                reason=bulk_decision.reason,
                risk_level=bulk_decision.risk_level
            )
            decisions.append((content_id, decision))
        
        # 批量处理
        results = await moderation_service.bulk_process_moderation_decisions(
            decisions, moderator_id
        )
        
        success_count = sum(results)
        failed_count = len(results) - success_count
        
        return {
            "message": f"批量审核完成: {success_count} 成功, {failed_count} 失败",
            "success_count": success_count,
            "failed_count": failed_count
        }
        
    except Exception as e:
        logger.error(f"批量提交审核决定失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="批量提交审核决定失败"
        )

@router.get("/stats", response_model=ModerationStats)
async def get_moderation_stats(
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)  # 需要审核员权限
):
    """获取审核统计信息
    
    获取系统的整体审核统计信息，包括待处理、已批准、已拒绝等内容的数量。
    """
    try:
        stats = await moderation_service.get_moderation_stats()
        return stats
        
    except Exception as e:
        logger.error(f"获取审核统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审核统计失败"
        )

@router.get("/content/{content_id}/status")
async def get_content_moderation_status(
    content_id: str,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(GetCurrentActiveUser)
):
    """获取内容审核状态
    
    获取指定内容的当前审核状态和历史记录。
    """
    try:
        # 获取内容信息
        from app.services.content_service import ContentService
        content_service = ContentService()
        content = await content_service.get_content_by_id(content_id)
        
        # 获取审核结果
        results = await moderation_service.db.select(
            "moderation_results",
            filters={"content_id": content_id},
            columns="*"
        )
        
        # 获取队列信息
        queue_items = await moderation_service.db.select(
            "moderation_queue",
            filters={"content_id": content_id},
            columns="*"
        )
        
        response = {
            "content_id": content_id,
            "moderation_status": content.get("moderation_status"),
            "content_status": content.get("status"),
            "latest_result": results[0] if results else None,
            "queue_info": queue_items[0] if queue_items else None,
            "history": results  # 完整的审核历史
        }
        
        return response
        
    except Exception as e:
        logger.error(f"获取内容审核状态失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审核状态失败"
        )

@router.get("/content/{content_id}/history", response_model=List[ModerationResult])
async def get_content_moderation_history(
    content_id: str,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)
):
    """获取内容审核历史
    
    获取指定内容的所有审核历史记录。
    """
    try:
        history = await moderation_service.get_content_moderation_history(content_id)
        return history
        
    except Exception as e:
        logger.error(f"获取内容审核历史失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审核历史失败"
        )

@router.post("/content/{content_id}/requeue")
async def requeue_content_for_review(
    content_id: str,
    reason: str = Body(..., embed=True, description="重新审核原因"),
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)
):
    """重新排队内容进行审核
    
    将已审核的内容重新提交到审核队列进行复审。
    """
    try:
        success = await moderation_service.requeue_content_for_review(content_id, reason)
        
        if success:
            return {"message": "内容已重新排队审核"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重新排队审核失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新排队审核失败 {content_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新排队审核失败"
        )

@router.put("/queue/{queue_item_id}/priority")
async def update_moderation_priority(
    queue_item_id: str,
    priority: ModerationPriority,
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireModerator)
):
    """更新审核优先级
    
    更新指定审核任务的优先级。
    """
    try:
        updated = await moderation_service.db.update(
            "moderation_queue",
            {
                "priority": priority.value,
                "updated_at": "now()"
            },
            {"id": queue_item_id}
        )
        
        if updated:
            return {"message": "审核优先级更新成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审核任务不存在"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新审核优先级失败 {queue_item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新审核优先级失败"
        )

@router.get("/moderators/workload", response_model=List[ModeratorWorkload])
async def get_moderator_workload(
    moderation_service: ModerationService = Depends(GetModerationService),
    current_user: Dict[str, Any] = Depends(RequireAdmin)
):
    """获取审核员工作负载
    
    获取所有审核员的工作负载统计信息。
    """
    try:
        # 这里应该查询数据库获取审核员工作负载信息
        # 由于当前实现中没有相关表结构，我们返回模拟数据
        
        # 在实际实现中，应该查询:
        # 1. 每个审核员分配的任务数量
        # 2. 每个审核员今日完成的任务数量
        # 3. 每个审核员的平均处理时间
        
        workload_data = [
            ModeratorWorkload(
                moderator_id="mod1",
                assigned_count=15,
                completed_today=8,
                average_processing_time=120.5
            ),
            ModeratorWorkload(
                moderator_id="mod2",
                assigned_count=8,
                completed_today=5,
                average_processing_time=95.2
            )
        ]
        
        return workload_data
        
    except Exception as e:
        logger.error(f"获取审核员工作负载失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取审核员工作负载失败"
        )