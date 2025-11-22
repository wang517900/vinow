-- init_database_fixed.sql - 修复策略重复创建问题
-- Vinow 后端数据库初始化脚本

-- ==================== 创建表结构 ====================

-- 用户资料表
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID REFERENCES auth.users PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    full_name VARCHAR(100),
    avatar_url TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    date_of_birth DATE,
    gender VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户偏好设置表
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID REFERENCES user_profiles(id) PRIMARY KEY,
    language VARCHAR(10) DEFAULT 'vi',
    notification_enabled BOOLEAN DEFAULT true,
    dietary_restrictions JSONB DEFAULT '{}',
    favorite_cuisines JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== 启用行级安全 ====================

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- ==================== 创建或替换策略 ====================

-- 删除已存在的策略（如果存在）
DO $$ 
BEGIN
    -- 删除 user_profiles 表的策略
    DROP POLICY IF EXISTS "user_profiles_select_policy" ON user_profiles;
    DROP POLICY IF EXISTS "user_profiles_insert_policy" ON user_profiles;
    DROP POLICY IF EXISTS "user_profiles_update_policy" ON user_profiles;
    DROP POLICY IF EXISTS "user_profiles_delete_policy" ON user_profiles;
    
    -- 删除 user_preferences 表的策略
    DROP POLICY IF EXISTS "user_preferences_select_policy" ON user_preferences;
    DROP POLICY IF EXISTS "user_preferences_insert_policy" ON user_preferences;
    DROP POLICY IF EXISTS "user_preferences_update_policy" ON user_preferences;
    DROP POLICY IF EXISTS "user_preferences_delete_policy" ON user_preferences;
    
    -- 删除中文名称的策略（如果之前创建过）
    DROP POLICY IF EXISTS "用户只能访问自己的资料" ON user_profiles;
    DROP POLICY IF EXISTS "用户只能访问自己的偏好设置" ON user_preferences;
EXCEPTION
    WHEN undefined_object THEN 
        NULL; -- 策略不存在，继续执行
END $$;

-- 为 user_profiles 表创建新的策略
CREATE POLICY "user_profiles_select_policy" ON user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "user_profiles_insert_policy" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "user_profiles_update_policy" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "user_profiles_delete_policy" ON user_profiles
    FOR DELETE USING (auth.uid() = id);

-- 为 user_preferences 表创建新的策略
CREATE POLICY "user_preferences_select_policy" ON user_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_preferences_insert_policy" ON user_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_preferences_update_policy" ON user_preferences
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "user_preferences_delete_policy" ON user_preferences
    FOR DELETE USING (auth.uid() = user_id);

-- ==================== 创建索引以提高性能 ====================

-- 用户资料表的索引
CREATE INDEX IF NOT EXISTS idx_user_profiles_phone ON user_profiles(phone);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);

-- 用户偏好表的索引
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- ==================== 设置表注释 ====================

COMMENT ON TABLE user_profiles IS '用户资料表 - 存储用户的基本信息';
COMMENT ON TABLE user_preferences IS '用户偏好设置表 - 存储用户的个性化设置';

-- ==================== 完成消息 ====================

DO $$ 
BEGIN
    RAISE NOTICE '✅ 数据库初始化完成';
    RAISE NOTICE '✅ 表结构创建成功';
    RAISE NOTICE '✅ 行级安全策略设置完成';
    RAISE NOTICE '✅ 索引创建完成';
END $$;