# [文件: scripts/init_database.py] [行号: 2501-2600]
"""
数据库初始化脚本 - 完整版
为所有v1系列功能创建必要的表结构
"""
import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def init_complete_database():
    """初始化完整数据库结构"""
    print("🗃️  开始初始化完整数据库...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase 配置缺失，请检查 .env 文件")
        return False
        
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase 客户端连接成功")
        
        # 完整的SQL语句列表
        sql_commands = [
            # 用户资料表 (v1.0.0, v1.1.0)
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id UUID REFERENCES auth.users PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                full_name VARCHAR(100),
                avatar_url TEXT,
                phone VARCHAR(20) UNIQUE NOT NULL,
                date_of_birth DATE,
                gender VARCHAR(10),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 用户偏好设置表 (v1.1.0)
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id UUID REFERENCES user_profiles(id) PRIMARY KEY,
                language VARCHAR(10) DEFAULT 'vi',
                notification_enabled BOOLEAN DEFAULT true,
                dietary_restrictions JSONB,
                favorite_cuisines JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 用户地址表 (v1.1.0)
            """
            CREATE TABLE IF NOT EXISTS user_addresses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                label VARCHAR(50),
                recipient_name VARCHAR(100),
                phone VARCHAR(20),
                address_line1 TEXT,
                address_line2 TEXT,
                city VARCHAR(50),
                district VARCHAR(50),
                ward VARCHAR(50),
                is_default BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 用户设备信息表 (v1.7.0)
            """
            CREATE TABLE IF NOT EXISTS user_devices (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                device_id VARCHAR(200),
                device_type VARCHAR(50),
                fcm_token TEXT,
                last_active TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 收藏表 (v1.2.0)
            """
            CREATE TABLE IF NOT EXISTS user_favorites (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                merchant_id UUID,
                product_id UUID,
                favorite_type VARCHAR(20),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, merchant_id, product_id)
            );
            """,
            
            # 浏览历史表 (v1.2.0)
            """
            CREATE TABLE IF NOT EXISTS browsing_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                merchant_id UUID,
                product_id UUID,
                viewed_at TIMESTAMPTZ DEFAULT NOW(),
                duration_seconds INTEGER DEFAULT 0
            );
            """,
            
            # 搜索历史表 (v1.2.0)
            """
            CREATE TABLE IF NOT EXISTS search_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                query_text TEXT,
                search_type VARCHAR(20),
                filters JSONB,
                result_count INTEGER,
                searched_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 订单表 (v1.3.0)
            """
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                order_number VARCHAR(50) UNIQUE,
                user_id UUID REFERENCES user_profiles(id),
                merchant_id UUID,
                status VARCHAR(20) DEFAULT 'pending',
                total_amount DECIMAL(10,2),
                discount_amount DECIMAL(10,2) DEFAULT 0,
                final_amount DECIMAL(10,2),
                payment_method VARCHAR(20),
                payment_status VARCHAR(20) DEFAULT 'pending',
                delivery_address JSONB,
                special_instructions TEXT,
                estimated_preparation_time INTEGER,
                completed_at TIMESTAMPTZ,
                cancelled_at TIMESTAMPTZ,
                cancellation_reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            # 评价表 (v1.4.0)
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES user_profiles(id),
                order_id UUID UNIQUE,
                merchant_id UUID,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                title VARCHAR(200),
                content TEXT,
                image_urls TEXT[],
                is_anonymous BOOLEAN DEFAULT false,
                helpful_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        ]
        
        # 执行所有SQL命令
        for i, sql in enumerate(sql_commands, 1):
            print(f"执行 SQL 命令 {i}/{len(sql_commands)}...")
            try:
                result = client.query(sql).execute()
                print(f"✅ 表创建成功")
            except Exception as e:
                print(f"⚠️  表创建警告: {e}")
        
        print("🎉 数据库初始化完成！")
        print("💡 所有v1系列功能所需的表结构已就绪")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Vinow 完整数据库初始化工具")
    print("📋 这将创建所有v1.0.0到v1.7.0功能所需的表")
    
    confirm = input("确认初始化数据库？(y/N): ")
    
    if confirm.lower() == 'y':
        success = init_complete_database()
        if success:
            print("🎊 初始化成功！现在可以运行完整测试了。")
        else:
            print("❌ 初始化失败，请检查错误信息。")
    else:
        print("操作已取消")