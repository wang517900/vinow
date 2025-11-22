-- init_database_simple.sql - 简化版本
-- 这个版本只创建表结构，不创建策略

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

-- 启用行级安全（如果尚未启用）
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_profiles_phone ON user_profiles(phone);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);

SELECT '✅ 表结构创建完成' as message;