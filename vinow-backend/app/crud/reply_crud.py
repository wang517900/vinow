"""
评价回复相关数据库操作类

本模块提供了对商户评价回复数据的增删改查操作，包括：
- 创建评价回复
- 根据评价ID获取回复
- 更新回复内容
- 删除回复
"""
商家系统7评价管理
from typing import Dict, Any
from datetime import datetime
from supabase import Client
from app.schemas.reply import ReplyCreate

class ReplyCRUD:
    """
    评价回复数据访问层类
    
    负责处理与评价回复相关的数据库操作
    """
    
    def __init__(self, db: Client):
        """
        初始化评价回复数据访问对象
        
        Args:
            db (Client): Supabase数据库客户端实例
        """
        self.db = db

    async def create_reply(self, reply: ReplyCreate) -> Dict[str, Any]:
        """
        创建新的评价回复记录
        
        Args:
            reply (ReplyCreate): 回复创建请求数据
            
        Returns:
            Dict[str, Any]: 创建成功的回复数据，失败返回None
        """
        # 将Pydantic模型转换为字典
        reply_data = reply.model_dump()
        
        # 移除模板ID字段，因为该字段不需要存入数据库
        reply_data.pop("template_id", None)
        
        # 执行数据库插入操作
        result = self.db.table("review_replies").insert(reply_data).execute()
        
        # 如果插入成功，返回第一条数据；否则返回None
        if result.data:
            return result.data[0]
        return None

    async def get_reply_by_review_id(self, review_id: int) -> Dict[str, Any]:
        """
        根据评价ID获取对应的回复信息
        
        Args:
            review_id (int): 评价ID
            
        Returns:
            Dict[str, Any]: 回复数据，如果没有找到则返回None
        """
        # 查询指定评价ID的回复记录
        result = self.db.table("review_replies").select("*").eq("review_id", review_id).execute()
        
        # 如果查询到数据，返回第一条记录；否则返回None
        if result.data:
            return result.data[0]
        return None

    async def update_reply(self, reply_id: int, merchant_id: int, content: str) -> bool:
        """
        更新回复内容
        
        Args:
            reply_id (int): 回复ID
            merchant_id (int): 商户ID（用于权限验证）
            content (str): 新的回复内容
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        # 执行更新操作，更新回复内容和更新时间
        result = self.db.table("review_replies").update(
            {"content": content, "created_at": datetime.utcnow().isoformat()}
        ).eq("id", reply_id).eq("merchant_id", merchant_id).execute()
        
        # 根据更新结果判断是否成功
        return len(result.data) > 0 if result.data else False

    async def delete_reply(self, reply_id: int, merchant_id: int) -> bool:
        """
        删除指定的回复
        
        Args:
            reply_id (int): 回复ID
            merchant_id (int): 商户ID（用于权限验证）
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        # 执行删除操作，根据回复ID和商户ID进行删除
        result = self.db.table("review_replies").delete().eq("id", reply_id).eq("merchant_id", merchant_id).execute()
        
        # 根据删除结果判断是否成功
        return len(result.data) > 0 if result.data else False