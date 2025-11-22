"""
Supabase 数据库客户端模块 - 修复版
"""
from supabase import create_client, Client
from app.core.config import settings

class DatabaseClient:
    """数据库客户端单例类"""
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """获取 Supabase 客户端实例"""
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_KEY
                )
                print("✅ Supabase 客户端初始化成功")
            except Exception as e:
                print(f"❌ Supabase 客户端初始化失败: {e}")
                raise
        return cls._instance
    
    @classmethod
    def health_check(cls) -> bool:
        """数据库健康检查"""
        try:
            client = cls.get_client()
            # 简单的查询测试连接
            result = client.table('user_profiles').select('count', count='exact').limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ 数据库健康检查失败: {e}")
            return False

# 创建全局数据库客户端
supabase: Client = DatabaseClient.get_client()