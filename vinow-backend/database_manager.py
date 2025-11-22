# database_manager.py - 数据库管理工具
import os
import requests
import json
from supabase import create_client

class DatabaseManager:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
    
    def check_existing_tables(self):
        """检查现有表"""
        print("🔍 检查现有表...")
        try:
            # 检查 user_profiles 表
            result = self.supabase.table("user_profiles").select("count", count="exact").limit(1).execute()
            print("✅ user_profiles 表存在")
        except Exception as e:
            print("❌ user_profiles 表不存在或无法访问")
        
        try:
            # 检查 user_preferences 表
            result = self.supabase.table("user_preferences").select("count", count="exact").limit(1).execute()
            print("✅ user_preferences 表存在")
        except Exception as e:
            print("❌ user_preferences 表不存在或无法访问")
    
    def test_row_level_security(self):
        """测试行级安全"""
        print("\n🔒 测试行级安全...")
        try:
            # 尝试查询所有数据（应该失败，因为没有认证）
            result = self.supabase.table("user_profiles").select("*").execute()
            if result.data:
                print("⚠️  行级安全可能未正确设置 - 可以查询所有数据")
            else:
                print("✅ 行级安全可能已启用 - 查询返回空结果")
        except Exception as e:
            print("✅ 行级安全已启用 - 查询被拒绝")
    
    def create_sample_data(self):
        """创建示例数据（用于测试）"""
        print("\n📝 创建示例数据...")
        try:
            # 注意：这需要先有认证用户
            print("ℹ️  示例数据创建需要先有认证用户")
            print("ℹ️  请先通过认证流程创建用户")
        except Exception as e:
            print(f"❌ 创建示例数据失败: {e}")
    
    def get_database_info(self):
        """获取数据库信息"""
        print("\n📊 数据库信息:")
        print(f"   Supabase URL: {self.supabase_url}")
        print(f"   项目状态: 已连接")
        
        # 获取表数量
        try:
            profiles_count = self.supabase.table("user_profiles").select("count", count="exact").execute()
            preferences_count = self.supabase.table("user_preferences").select("count", count="exact").execute()
            
            print(f"   user_profiles 记录数: {profiles_count.count if hasattr(profiles_count, 'count') else 'N/A'}")
            print(f"   user_preferences 记录数: {preferences_count.count if hasattr(preferences_count, 'count') else 'N/A'}")
        except Exception as e:
            print(f"   ❌ 无法获取表信息: {e}")

def main():
    print("🚀 Vinow 数据库管理工具")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        print("❌ 请先设置 SUPABASE_URL 和 SUPABASE_SERVICE_KEY 环境变量")
        return
    
    manager = DatabaseManager()
    
    # 运行检查
    manager.check_existing_tables()
    manager.test_row_level_security()
    manager.get_database_info()
    
    print("\n" + "=" * 50)
    print("💡 下一步建议:")
    print("   1. 如果表不存在，请在 Supabase SQL 编辑器中运行 init_database_simple.sql")
    print("   2. 如果遇到策略错误，请运行 init_database_fixed.sql")
    print("   3. 测试认证流程会自动创建用户资料")

if __name__ == "__main__":
    main()
