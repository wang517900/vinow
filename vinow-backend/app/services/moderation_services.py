内容系统
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio

from app.database.supabase_client import db_manager, Tables
from app.models.moderation import (
    ModerationDecision, ModerationResult, ModerationQueueItem,
    AutomatedModerationResult, ModerationStats, ModerationAction, ModerationPriority
)
from app.core.exceptions import ContentNotFoundException, DatabaseException
from app.utils.logger import logger

class ModerationService:
    """内容审核服务类 - 处理内容审核相关的业务逻辑"""
    
    def __init__(self):
        """初始化审核服务"""
        self.db = db_manager
        # 敏感词库（简化实现，实际应该从数据库或文件加载）
        self.sensitive_words = [
            "暴力", "色情", "赌博", "毒品", "诈骗",
            "political_sensitive_term1", "political_sensitive_term2"  # 示例敏感词
        ]
    
    async def submit_for_moderation(self, content_id: str) -> ModerationQueueItem:
        """提交内容进行审核
        
        Args:
            content_id: 内容ID
            
        Returns:
            审核队列项
            
        Raises:
            ContentNotFoundException: 内容不存在
            DatabaseException: 数据库操作异常
        """
        try:
            # 检查内容是否存在
            content = await self.db.select(
                Tables.CONTENT,
                filters={"id": content_id}
            )
            if not content:
                raise ContentNotFoundException(content_id)
            
            # 检查是否已在审核队列中
            existing_queue = await self.db.select(
                Tables.MODERATION_QUEUE,
                filters={"content_id": content_id}
            )
            
            if existing_queue:
                logger.info(f"内容已在审核队列中: {content_id}")
                return ModerationQueueItem(**existing_queue[0])
            
            # 确定审核优先级
            priority = await self._determine_priority(content[0])
            
            # 创建审核队列项
            queue_item = {
                "id": str(uuid4()),
                "content_id": content_id,
                "priority": priority.value,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 插入审核队列
            result = await self.db.insert(Tables.MODERATION_QUEUE, queue_item)
            
            # 自动审核
            await self._perform_automated_moderation(content_id)
            
            logger.info(f"内容提交审核成功: {content_id}, 优先级: {priority}")
            return ModerationQueueItem(**result)
            
        except ContentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"提交审核失败 {content_id}: {str(e)}")
            raise DatabaseException(f"提交审核失败: {str(e)}")
    
    async def _determine_priority(self, content: Dict[str, Any]) -> ModerationPriority:
        """确定审核优先级
        
        Args:
            content: 内容数据
            
        Returns:
            审核优先级枚举值
        """
        try:
            # 基于内容特征确定优先级
            creator_id = content.get("creator_id")
            content_type = content.get("content_type")
            
            # 检查创作者历史
            creator_content = await self.db.select(
                Tables.CONTENT,
                filters={"creator_id": creator_id}
            )
            
            # 新创作者或高风险内容类型需要更高优先级
            if len(creator_content) <= 3:  # 新创作者
                return ModerationPriority.HIGH
            elif content_type == "video":  # 视频内容需要更严格审核
                return ModerationPriority.HIGH
            else:
                return ModerationPriority.NORMAL
                
        except Exception as e:
            logger.error(f"确定审核优先级失败: {str(e)}")
            return ModerationPriority.NORMAL
    
    async def _perform_automated_moderation(self, content_id: str) -> AutomatedModerationResult:
        """执行自动审核
        
        Args:
            content_id: 内容ID
            
        Returns:
            自动审核结果
        """
        try:
            # 获取内容详情
            content = await self.db.select(
                Tables.CONTENT,
                filters={"id": content_id}
            )
            if not content:
                raise ContentNotFoundException(content_id)
            
            content_data = content[0]
            
            # 执行各种自动审核检查
            text_checks = await self._check_text_content(content_data)
            metadata_checks = await self._check_metadata(content_data)
            
            # 综合风险评估
            risk_factors = []
            confidence = 0.8  # 默认置信度
            
            if text_checks["has_sensitive_words"]:
                risk_factors.append("包含敏感词汇")
                confidence = 0.95
            
            if metadata_checks["suspicious_metadata"]:
                risk_factors.append("元数据异常")
                confidence = min(confidence, 0.7)
            
            # 决定推荐操作
            if risk_factors:
                recommended_action = ModerationAction.NEEDS_REVIEW
                status = "needs_review"
            else:
                recommended_action = ModerationAction.APPROVE
                status = "approved"
            
            # 创建自动审核结果
            auto_result = AutomatedModerationResult(
                content_id=UUID(content_id),
                status=status,
                confidence=confidence,
                risk_factors=risk_factors,
                recommended_action=recommended_action
            )
            
            # 如果自动审核通过，直接更新内容状态
            if recommended_action == ModerationAction.APPROVE:
                await self._update_content_moderation_status(
                    content_id, "approved", "自动审核通过"
                )
                
                # 更新审核队列状态
                await self.db.update(
                    Tables.MODERATION_QUEUE,
                    {
                        "status": "completed",
                        "updated_at": datetime.utcnow().isoformat()
                    },
                    {"content_id": content_id}
                )
            
            logger.info(f"自动审核完成: {content_id}, 操作: {recommended_action}, 置信度: {confidence}")
            return auto_result
            
        except Exception as e:
            logger.error(f"自动审核失败 {content_id}: {str(e)}")
            # 返回需要人工审核的结果
            return AutomatedModerationResult(
                content_id=UUID(content_id),
                status="needs_review",
                confidence=0.0,
                risk_factors=["自动审核失败"],
                recommended_action=ModerationAction.NEEDS_REVIEW
            )
    
    async def _check_text_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """检查文本内容
        
        Args:
            content: 内容数据
            
        Returns:
            文本检查结果
        """
        try:
            title = content.get("title", "")
            description = content.get("description", "")
            tags = content.get("tags", [])
            
            # 合并所有文本内容
            all_text = f"{title} {description} {' '.join(tags)}"
            
            # 检查敏感词
            has_sensitive_words = False
            found_sensitive_words = []
            
            for word in self.sensitive_words:
                if word in all_text:
                    has_sensitive_words = True
                    found_sensitive_words.append(word)
            
            return {
                "has_sensitive_words": has_sensitive_words,
                "found_sensitive_words": found_sensitive_words,
                "text_length": len(all_text)
            }
            
        except Exception as e:
            logger.error(f"文本内容检查失败: {str(e)}")
            return {"has_sensitive_words": False, "found_sensitive_words": [], "text_length": 0}
    
    async def _check_metadata(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """检查元数据
        
        Args:
            content: 内容数据
            
        Returns:
            元数据检查结果
        """
        try:
            metadata = content.get("metadata", {})
            suspicious_metadata = False
            issues = []
            
            # 检查文件大小异常
            file_size = content.get("file_size", 0)
            if file_size > 100 * 1024 * 1024:  # 100MB
                suspicious_metadata = True
                issues.append("文件大小异常")
            
            # 检查标签数量
            tags = content.get("tags", [])
            if len(tags) > 20:  # 标签过多
                suspicious_metadata = True
                issues.append("标签数量过多")
            
            # 检查地理位置信息
            location = content.get("location")
            if location and isinstance(location, dict):
                # 这里可以添加地理位置检查逻辑
                pass
            
            return {
                "suspicious_metadata": suspicious_metadata,
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"元数据检查失败: {str(e)}")
            return {"suspicious_metadata": False, "issues": []}
    
    async def get_moderation_queue(self, status: str = "pending", limit: int = 50) -> List[ModerationQueueItem]:
        """获取审核队列
        
        Args:
            status: 审核状态筛选
            limit: 返回数量限制
            
        Returns:
            审核队列项列表
        """
        try:
            filters = {}
            if status:
                filters["status"] = status
            
            queue_items = await self.db.select(
                Tables.MODERATION_QUEUE,
                filters=filters,
                columns="*"
            )
            
            # 按优先级和创建时间排序
            queue_items.sort(key=lambda x: (
                x.get("priority", "normal"),
                x.get("created_at", "")
            ))
            
            # 限制返回数量
            limited_items = queue_items[:limit]
            
            # 转换为模型对象
            result = []
            for item in limited_items:
                result.append(ModerationQueueItem(**item))
            
            return result
            
        except Exception as e:
            logger.error(f"获取审核队列失败: {str(e)}")
            return []
    
    async def assign_moderation_task(self, queue_item_id: str, moderator_id: str) -> bool:
        """分配审核任务给审核员
        
        Args:
            queue_item_id: 审核队列项ID
            moderator_id: 审核员ID
            
        Returns:
            是否分配成功
        """
        try:
            # 更新审核队列项
            updated = await self.db.update(
                Tables.MODERATION_QUEUE,
                {
                    "assigned_to": moderator_id,
                    "status": "assigned",
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"id": queue_item_id}
            )
            
            if updated:
                logger.info(f"审核任务分配成功: {queue_item_id} -> {moderator_id}")
                return True
            else:
                logger.warning(f"审核任务分配失败: {queue_item_id}")
                return False
                
        except Exception as e:
            logger.error(f"分配审核任务失败 {queue_item_id}: {str(e)}")
            return False
    
    async def process_moderation_decision(
        self, 
        content_id: str, 
        decision: ModerationDecision, 
        moderator_id: Optional[str] = None
    ) -> ModerationResult:
        """处理审核决定
        
        Args:
            content_id: 内容ID
            decision: 审核决定
            moderator_id: 审核员ID（可选）
            
        Returns:
            审核结果
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            # 创建审核结果记录
            result_data = {
                "id": str(uuid4()),
                "content_id": content_id,
                "moderator_id": moderator_id,
                "status": decision.action.value,
                "reason": decision.reason,
                "risk_level": decision.risk_level.value if decision.risk_level else "medium",
                "automated": moderator_id is None,  # 如果没有审核员ID，则是自动审核
                "reviewed_at": datetime.utcnow().isoformat()
            }
            
            # 保存审核结果
            result = await self.db.insert(Tables.MODERATION_RESULTS, result_data)
            
            # 更新内容状态
            await self._update_content_moderation_status(
                content_id, decision.action.value, decision.reason
            )
            
            # 更新审核队列状态
            await self.db.update(
                Tables.MODERATION_QUEUE,
                {
                    "status": "completed",
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"content_id": content_id}
            )
            
            # 如果是拒绝，记录原因并可能采取进一步行动
            if decision.action.value == "rejected":
                await self._handle_rejected_content(content_id, decision.reason)
            
            logger.info(f"审核决定处理完成: {content_id}, 操作: {decision.action}, 原因: {decision.reason}")
            return ModerationResult(**result)
            
        except Exception as e:
            logger.error(f"处理审核决定失败 {content_id}: {str(e)}")
            raise DatabaseException(f"处理审核决定失败: {str(e)}")
    
    async def _update_content_moderation_status(
        self, 
        content_id: str, 
        status: str, 
        reason: Optional[str] = None
    ):
        """更新内容审核状态
        
        Args:
            content_id: 内容ID
            status: 审核状态
            reason: 原因（可选）
        """
        try:
            update_data = {
                "moderation_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 如果审核通过，更新内容状态为已批准
            if status == "approved":
                update_data["status"] = "approved"
                update_data["published_at"] = datetime.utcnow().isoformat()
            
            await self.db.update(
                Tables.CONTENT,
                update_data,
                {"id": content_id}
            )
            
            logger.info(f"内容审核状态更新: {content_id} -> {status}")
            
        except Exception as e:
            logger.error(f"更新内容审核状态失败 {content_id}: {str(e)}")
            raise
    
    async def _handle_rejected_content(self, content_id: str, reason: str):
        """处理被拒绝的内容
        
        Args:
            content_id: 内容ID
            reason: 拒绝原因
        """
        try:
            # 记录拒绝原因，可以通知创作者等
            # 这里可以添加更复杂的逻辑，如累计拒绝次数、暂停创作者权限等
            logger.info(f"内容被拒绝: {content_id}, 原因: {reason}")
            
            # 更新内容状态为已拒绝
            await self.db.update(
                Tables.CONTENT,
                {
                    "status": "rejected",
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"id": content_id}
            )
            
        except Exception as e:
            logger.error(f"处理被拒绝内容失败 {content_id}: {str(e)}")
    
    async def get_moderation_stats(self) -> ModerationStats:
        """获取审核统计信息
        
        Returns:
            审核统计信息
        """
        try:
            # 获取各种状态的计数
            queue_items = await self.db.select(Tables.MODERATION_QUEUE, columns="status")
            results = await self.db.select(Tables.MODERATION_RESULTS, columns="*")
            
            # 统计各状态数量
            status_counts = {}
            for item in queue_items:
                status = item.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # 计算平均处理时间（简化实现）
            total_processing_time = 0
            processed_count = 0
            
            for result in results:
                if result.get("reviewed_at") and result.get("created_at"):
                    # 这里需要计算时间差，简化处理
                    processed_count += 1
            
            average_processing_time = total_processing_time / max(processed_count, 1)
            
            # 审核员绩效（简化实现）
            moderator_performance = {
                "total_reviews": len(results),
                "average_accuracy": 0.95,  # 假设准确率
                "top_moderators": []  # 可以添加具体审核员数据
            }
            
            stats = ModerationStats(
                total_pending=status_counts.get("pending", 0),
                total_approved=len([r for r in results if r.get("status") == "approved"]),
                total_rejected=len([r for r in results if r.get("status") == "rejected"]),
                total_needs_review=status_counts.get("needs_review", 0),
                average_processing_time=average_processing_time,
                moderator_performance=moderator_performance
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取审核统计失败: {str(e)}")
            # 返回默认统计
            return ModerationStats(
                total_pending=0,
                total_approved=0,
                total_rejected=0,
                total_needs_review=0,
                average_processing_time=0.0,
                moderator_performance={}
            )
    
    async def get_content_moderation_history(self, content_id: str) -> List[ModerationResult]:
        """获取内容审核历史
        
        Args:
            content_id: 内容ID
            
        Returns:
            审核历史列表
        """
        try:
            results = await self.db.select(
                Tables.MODERATION_RESULTS,
                filters={"content_id": content_id},
                order_by="reviewed_at DESC"
            )
            
            return [ModerationResult(**result) for result in results]
            
        except Exception as e:
            logger.error(f"获取内容审核历史失败 {content_id}: {str(e)}")
            return []
    
    async def bulk_process_moderation_decisions(
        self, 
        decisions: List[tuple], 
        moderator_id: str
    ) -> List[bool]:
        """批量处理审核决定
        
        Args:
            decisions: 决定列表 [(content_id, decision), ...]
            moderator_id: 审核员ID
            
        Returns:
            处理结果列表
        """
        results = []
        for content_id, decision in decisions:
            try:
                await self.process_moderation_decision(content_id, decision, moderator_id)
                results.append(True)
            except Exception as e:
                logger.error(f"批量处理审核决定失败 {content_id}: {str(e)}")
                results.append(False)
        
        return results
    
    async def requeue_content_for_review(self, content_id: str, reason: str = "重新审核") -> bool:
        """重新排队内容进行审核
        
        Args:
            content_id: 内容ID
            reason: 重新审核原因
            
        Returns:
            是否重新排队成功
        """
        try:
            # 检查内容是否存在
            content = await self.db.select(
                Tables.CONTENT,
                filters={"id": content_id}
            )
            if not content:
                logger.warning(f"重新排队内容失败，内容不存在: {content_id}")
                return False
            
            # 检查是否已在审核队列中
            existing_queue = await self.db.select(
                Tables.MODERATION_QUEUE,
                filters={"content_id": content_id}
            )
            
            if existing_queue:
                # 更新现有队列项
                await self.db.update(
                    Tables.MODERATION_QUEUE,
                    {
                        "status": "pending",
                        "priority": "high",  # 高优先级
                        "updated_at": datetime.utcnow().isoformat()
                    },
                    {"content_id": content_id}
                )
            else:
                # 创建新的审核队列项
                queue_item = {
                    "id": str(uuid4()),
                    "content_id": content_id,
                    "priority": "high",
                    "status": "pending",
                    "requeue_reason": reason,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                await self.db.insert(Tables.MODERATION_QUEUE, queue_item)
            
            logger.info(f"内容重新排队成功: {content_id}, 原因: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"重新排队内容失败 {content_id}: {str(e)}")
            return False

# 全局审核服务实例
moderation_service = ModerationService()