# app/content_marketing/services_enhanced.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.database import supabase
from app.content_marketing.models import (
    ContentInDB, ContentCreate, ContentUpdate, ContentStats,
    CollaborationInDB, CollaborationCreate, CollaborationStatus,
    CollaborationApplicationInDB, CollaborationApplicationCreate, ApplicationStatus,
    ContentMarketingDashboard, ContentType, ContentStatus
)
from app.core.exceptions import (
    ContentNotFoundException, CollaborationNotFoundException,
    PermissionDeniedException, ValidationException
)
from app.core.logging import BusinessLogger, AuditLogger
import logging
import uuid

logger = BusinessLogger("content_marketing")

class EnhancedContentMarketingService:
    """增强版内容营销服务（包含完整的错误处理和审计）"""
    
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self.audit_logger = AuditLogger()
    
    def _validate_merchant_access(self, resource_merchant_id: str, operation: str):
        """验证商家访问权限"""
        if resource_merchant_id != self.merchant_id:
            self.audit_logger.log_security_event(
                "UNAUTHORIZED_ACCESS",
                self.merchant_id,
                "unknown",
                {"attempted_access": resource_merchant_id, "operation": operation}
            )
            raise PermissionDeniedException(f"商家 {resource_merchant_id}")
    
    async def create_content(self, content_data: ContentCreate) -> Optional[ContentInDB]:
        """创建内容（增强版）"""
        try:
            logger.log_operation("CREATE_CONTENT", self.merchant_id, title=content_data.title)
            
            # 数据验证
            if content_data.content_type == ContentType.VIDEO and not content_data.video_url:
                raise ValidationException("video_url", "视频类型必须提供视频URL")
            
            if content_data.content_type == ContentType.IMAGE_TEXT and not content_data.image_urls:
                raise ValidationException("image_urls", "图文类型必须提供图片")
            
            content_dict = content_data.model_dump()
            content_dict["tracking_code"] = f"CONTENT_{uuid.uuid4()}"
            content_dict["created_at"] = datetime.now().isoformat()
            content_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").insert(content_dict).execute()
            
            if response.data:
                content = ContentInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_content_operation(
                    "CREATED", self.merchant_id, content.id,
                    {"title": content.title, "type": content.content_type}
                )
                
                return content
            
            return None
            
        except ValidationException:
            raise
        except Exception as e:
            logger.log_error("CREATE_CONTENT", self.merchant_id, e, title=content_data.title)
            raise
    
    async def get_content(self, content_id: str) -> Optional[ContentInDB]:
        """获取内容详情（增强版）"""
        try:
            logger.log_operation("GET_CONTENT", self.merchant_id, content_id=content_id)
            
            response = supabase.table("merchant_orders.cm_contents").select("*").eq("id", content_id).execute()
            
            if not response.data:
                raise ContentNotFoundException(content_id)
            
            content = ContentInDB(**response.data[0])
            
            # 验证权限
            self._validate_merchant_access(content.merchant_id, "GET_CONTENT")
            
            return content
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("GET_CONTENT", self.merchant_id, e, content_id=content_id)
            raise
    
    async def update_content(self, content_id: str, update_data: ContentUpdate) -> Optional[ContentInDB]:
        """更新内容（增强版）"""
        try:
            logger.log_operation("UPDATE_CONTENT", self.merchant_id, content_id=content_id)
            
            # 先获取现有内容验证权限
            existing_content = await self.get_content(content_id)
            if not existing_content:
                raise ContentNotFoundException(content_id)
            
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_contents").update(update_dict).eq("id", content_id).execute()
            
            if response.data:
                content = ContentInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_content_operation(
                    "UPDATED", self.merchant_id, content_id,
                    {"changes": list(update_dict.keys())}
                )
                
                return content
            
            return None
            
        except (ContentNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("UPDATE_CONTENT", self.merchant_id, e, content_id=content_id)
            raise
    
    async def create_collaboration(self, collaboration_data: CollaborationCreate) -> Optional[CollaborationInDB]:
        """创建合作任务（增强版）"""
        try:
            logger.log_operation("CREATE_COLLABORATION", self.merchant_id, title=collaboration_data.title)
            
            # 预算验证
            if collaboration_data.budget_amount and collaboration_data.budget_amount <= 0:
                raise ValidationException("budget_amount", "预算金额必须大于0")
            
            if collaboration_data.commission_rate and not (0 <= collaboration_data.commission_rate <= 100):
                raise ValidationException("commission_rate", "佣金比例必须在0-100之间")
            
            collaboration_dict = collaboration_data.model_dump()
            collaboration_dict["status"] = CollaborationStatus.RECRUITING
            collaboration_dict["created_at"] = datetime.now().isoformat()
            collaboration_dict["updated_at"] = datetime.now().isoformat()
            
            response = supabase.table("merchant_orders.cm_collaborations").insert(collaboration_dict).execute()
            
            if response.data:
                collaboration = CollaborationInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_collaboration_operation(
                    "CREATED", self.merchant_id, collaboration.id,
                    {"title": collaboration.title, "budget": collaboration.budget_amount}
                )
                
                return collaboration
            
            return None
            
        except ValidationException:
            raise
        except Exception as e:
            logger.log_error("CREATE_COLLABORATION", self.merchant_id, e, title=collaboration_data.title)
            raise
    
    async def get_collaboration(self, collaboration_id: str) -> Optional[CollaborationInDB]:
        """获取合作任务详情（增强版）"""
        try:
            logger.log_operation("GET_COLLABORATION", self.merchant_id, collaboration_id=collaboration_id)
            
            response = supabase.table("merchant_orders.cm_collaborations").select("*").eq("id", collaboration_id).execute()
            
            if not response.data:
                raise CollaborationNotFoundException(collaboration_id)
            
            collaboration = CollaborationInDB(**response.data[0])
            
            # 验证权限
            self._validate_merchant_access(collaboration.merchant_id, "GET_COLLABORATION")
            
            return collaboration
            
        except (CollaborationNotFoundException, PermissionDeniedException):
            raise
        except Exception as e:
            logger.log_error("GET_COLLABORATION", self.merchant_id, e, collaboration_id=collaboration_id)
            raise
    
    async def update_application_status(
        self, 
        application_id: str, 
        status: ApplicationStatus,
        final_content_id: Optional[str] = None
    ) -> Optional[CollaborationApplicationInDB]:
        """更新申请状态（增强版）"""
        try:
            logger.log_operation("UPDATE_APPLICATION_STATUS", self.merchant_id, 
                               application_id=application_id, new_status=status)
            
            # 获取申请详情验证权限
            response = supabase.table("merchant_orders.cm_collaboration_applications").select("*").eq("id", application_id).execute()
            
            if not response.data:
                raise BusinessException("申请不存在")
            
            application_data = response.data[0]
            self._validate_merchant_access(application_data["merchant_id"], "UPDATE_APPLICATION")
            
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if status == ApplicationStatus.ACCEPTED:
                update_data["accepted_at"] = datetime.now().isoformat()
            elif status == ApplicationStatus.COMPLETED:
                if not final_content_id:
                    raise ValidationException("final_content_id", "完成申请必须提供最终内容ID")
                update_data["completed_at"] = datetime.now().isoformat()
                update_data["final_content_id"] = final_content_id
            
            response = supabase.table("merchant_orders.cm_collaboration_applications").update(update_data).eq("id", application_id).execute()
            
            if response.data:
                application = CollaborationApplicationInDB(**response.data[0])
                
                # 审计日志
                self.audit_logger.log_collaboration_operation(
                    "APPLICATION_STATUS_CHANGED", 
                    self.merchant_id, 
                    application.collaboration_id,
                    {"application_id": application_id, "new_status": status}
                )
                
                return application
            
            return None
            
        except (BusinessException, PermissionDeniedException, ValidationException):
            raise
        except Exception as e:
            logger.log_error("UPDATE_APPLICATION_STATUS", self.merchant_id, e, 
                           application_id=application_id, status=status)
            raise
    
    # 其他方法也需要类似的增强...