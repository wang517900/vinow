内容系统-服务层

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
import json

from app.database.supabase_client import db_manager, Tables
from app.core.security import SecurityManager
from app.models.user import UserCreate, UserUpdate, UserResponse, UserProfile, UserInDB
from app.core.exceptions import UserNotFoundException, DatabaseException

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类，提供用户管理相关操作"""
    
    def __init__(self):
        self.db = db_manager
    
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """创建新用户
        
        Args:
            user_data: 用户创建信息
            
        Returns:
            创建成功的用户信息
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            # 检查用户是否已存在
            existing_user = await self.db.select(
                Tables.USERS,
                filters={"email": user_data.email}
            )
            if existing_user:
                raise DatabaseException("用户已存在")
            
            # 创建用户记录
            user_dict = user_data.dict()
            user_dict["password_hash"] = SecurityManager.get_password_hash(user_data.password)
            del user_dict["password"]  # 删除明文密码
            
            # 插入用户数据
            user = await self.db.insert(Tables.USERS, user_dict)
            
            # 创建用户资料
            profile_data = {
                "user_id": user["id"],
                "full_name": user_data.full_name,
                "statistics": {
                    "total_uploads": 0,
                    "total_views": 0,
                    "total_likes": 0,
                    "total_shares": 0
                }
            }
            await self.db.insert(Tables.USER_PROFILES, profile_data)
            
            # 创建创作者成长记录
            growth_data = {
                "user_id": user["id"],
                "level": 1,
                "experience_points": 0,
                "total_uploads": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_shares": 0,
                "quality_rating": 0.0,
                "badges": []
            }
            await self.db.insert(Tables.CREATOR_GROWTH, growth_data)
            
            logger.info(f"用户创建成功: {user['id']}")
            return user
            
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise DatabaseException(f"创建用户失败: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息字典，如果不存在则返回None
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            users = await self.db.select(
                Tables.USERS,
                filters={"id": user_id}
            )
            return users[0] if users else None
        except Exception as e:
            logger.error(f"获取用户失败 {user_id}: {str(e)}")
            raise DatabaseException(f"获取用户失败: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            用户信息字典，如果不存在则返回None
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            users = await self.db.select(
                Tables.USERS,
                filters={"email": email}
            )
            return users[0] if users else None
        except Exception as e:
            logger.error(f"通过邮箱获取用户失败 {email}: {str(e)}")
            raise DatabaseException(f"获取用户失败: {str(e)}")
    
    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有用户列表
        
        Args:
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            用户列表
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            users = await self.db.select(
                Tables.USERS,
                limit=limit,
                offset=offset
            )
            return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            raise DatabaseException(f"获取用户列表失败: {str(e)}")
    
    async def update_user(self, user_id: str, update_data: UserUpdate) -> Dict[str, Any]:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 用户更新信息
            
        Returns:
            更新后的用户信息
            
        Raises:
            UserNotFoundException: 用户不存在
            DatabaseException: 数据库操作异常
        """
        try:
            # 检查用户是否存在
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            # 准备更新数据
            update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                update_dict["updated_at"] = datetime.utcnow().isoformat()
                updated_users = await self.db.update(
                    Tables.USERS,
                    update_dict,
                    {"id": user_id}
                )
                
                # 同时更新用户资料
                profile_updates = {}
                if update_data.full_name:
                    profile_updates["full_name"] = update_data.full_name
                if update_data.avatar_url:
                    profile_updates["avatar_url"] = update_data.avatar_url
                if update_data.bio:
                    profile_updates["bio"] = update_data.bio
                if update_data.location:
                    profile_updates["location"] = update_data.location
                
                if profile_updates:
                    profile_updates["updated_at"] = datetime.utcnow().isoformat()
                    await self.db.update(
                        Tables.USER_PROFILES,
                        profile_updates,
                        {"user_id": user_id}
                    )
                
                logger.info(f"用户信息更新成功: {user_id}")
                return updated_users[0] if updated_users else user
            return user
            
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"更新用户失败 {user_id}: {str(e)}")
            raise DatabaseException(f"更新用户失败: {str(e)}")
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            删除是否成功
            
        Raises:
            UserNotFoundException: 用户不存在
            DatabaseException: 数据库操作异常
        """
        try:
            # 检查用户是否存在
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            # 删除用户相关数据
            await self.db.delete(Tables.CREATOR_GROWTH, {"user_id": user_id})
            await self.db.delete(Tables.USER_PROFILES, {"user_id": user_id})
            await self.db.delete(Tables.USERS, {"id": user_id})
            
            logger.info(f"用户删除成功: {user_id}")
            return True
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"删除用户失败 {user_id}: {str(e)}")
            raise DatabaseException(f"删除用户失败: {str(e)}")
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证
        
        Args:
            email: 用户邮箱
            password: 用户密码
            
        Returns:
            认证成功的用户信息，认证失败返回None
        """
        try:
            user = await self.get_user_by_email(email)
            if not user:
                return None
            
            if not SecurityManager.verify_password(password, user["password_hash"]):
                return None
            
            if not user.get("is_active", True):
                return None
            
            return user
        except Exception as e:
            logger.error(f"用户认证失败 {email}: {str(e)}")
            return None
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改用户密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            修改是否成功
            
        Raises:
            UserNotFoundException: 用户不存在
            DatabaseException: 数据库操作异常
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            # 验证旧密码
            if not SecurityManager.verify_password(old_password, user["password_hash"]):
                raise DatabaseException("旧密码不正确")
            
            # 更新密码
            new_password_hash = SecurityManager.get_password_hash(new_password)
            await self.db.update(
                Tables.USERS,
                {
                    "password_hash": new_password_hash,
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"id": user_id}
            )
            
            logger.info(f"用户密码修改成功: {user_id}")
            return True
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"修改用户密码失败 {user_id}: {str(e)}")
            raise DatabaseException(f"修改密码失败: {str(e)}")
    
    async def reset_password(self, email: str, new_password: str) -> bool:
        """重置用户密码（管理员操作）
        
        Args:
            email: 用户邮箱
            new_password: 新密码
            
        Returns:
            重置是否成功
            
        Raises:
            UserNotFoundException: 用户不存在
            DatabaseException: 数据库操作异常
        """
        try:
            user = await self.get_user_by_email(email)
            if not user:
                raise UserNotFoundException(email)
            
            # 更新密码
            new_password_hash = SecurityManager.get_password_hash(new_password)
            await self.db.update(
                Tables.USERS,
                {
                    "password_hash": new_password_hash,
                    "updated_at": datetime.utcnow().isoformat()
                },
                {"email": email}
            )
            
            logger.info(f"用户密码重置成功: {email}")
            return True
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"重置用户密码失败 {email}: {str(e)}")
            raise DatabaseException(f"重置密码失败: {str(e)}")
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户完整资料
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含用户基本信息、资料和成长记录的完整资料
            
        Raises:
            UserNotFoundException: 用户不存在
            DatabaseException: 数据库操作异常
        """
        try:
            # 获取用户基本信息
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException(user_id)
            
            # 获取用户资料
            profiles = await self.db.select(
                Tables.USER_PROFILES,
                filters={"user_id": user_id}
            )
            profile = profiles[0] if profiles else {}
            
            # 获取创作者成长信息
            growth_records = await self.db.select(
                Tables.CREATOR_GROWTH,
                filters={"user_id": user_id}
            )
            growth = growth_records[0] if growth_records else {}
            
            # 组合返回数据
            result = {
                **user,
                "profile": profile,
                "creator_growth": growth
            }
            
            return result
            
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取用户资料失败 {user_id}: {str(e)}")
            raise DatabaseException(f"获取用户资料失败: {str(e)}")
    
    async def update_user_statistics(self, user_id: str, stats_updates: Dict[str, Any]) -> None:
        """更新用户统计信息
        
        Args:
            user_id: 用户ID
            stats_updates: 统计信息更新内容
            
        Raises:
            DatabaseException: 数据库操作异常
        """
        try:
            # 更新用户资料中的统计信息
            profiles = await self.db.select(
                Tables.USER_PROFILES,
                filters={"user_id": user_id}
            )
            
            if profiles:
                current_stats = profiles[0].get("statistics", {})
                updated_stats = {**current_stats, **stats_updates}
                
                await self.db.update(
                    Tables.USER_PROFILES,
                    {
                        "statistics": updated_stats,
                        "updated_at": datetime.utcnow().isoformat()
                    },
                    {"user_id": user_id}
                )
            
            # 更新创作者成长记录
            growth_records = await self.db.select(
                Tables.CREATOR_GROWTH,
                filters={"user_id": user_id}
            )
            
            if growth_records:
                growth_data = {}
                if "total_uploads" in stats_updates:
                    growth_data["total_uploads"] = stats_updates["total_uploads"]
                if "total_views" in stats_updates:
                    growth_data["total_views"] = stats_updates["total_views"]
                if "total_likes" in stats_updates:
                    growth_data["total_likes"] = stats_updates["total_likes"]
                if "total_shares" in stats_updates:
                    growth_data["total_shares"] = stats_updates["total_shares"]
                
                if growth_data:
                    growth_data["updated_at"] = datetime.utcnow().isoformat()
                    await self.db.update(
                        Tables.CREATOR_GROWTH,
                        growth_data,
                        {"user_id": user_id}
                    )
            
            logger.info(f"用户统计信息更新成功: {user_id}")
            
        except Exception as e:
            logger.error(f"更新用户统计信息失败 {user_id}: {str(e)}")
            raise DatabaseException(f"更新统计信息失败: {str(e)}")