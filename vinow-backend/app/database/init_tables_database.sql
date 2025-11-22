内容系统
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户资料表
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    bio TEXT,
    location JSONB,
    preferences JSONB DEFAULT '{}',
    social_links JSONB DEFAULT '{}',
    statistics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 内容表
CREATE TABLE IF NOT EXISTS content (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content_type VARCHAR(50) NOT NULL,
    media_urls JSONB NOT NULL,
    thumbnail_url VARCHAR(500),
    creator_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tags JSONB DEFAULT '[]',
    location JSONB,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'draft',
    moderation_status VARCHAR(50) DEFAULT 'pending',
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    duration INTEGER,
    file_size BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- 内容互动表
CREATE TABLE IF NOT EXISTS content_interactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    duration FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, content_id, interaction_type)
);

-- 内容质量评分表
CREATE TABLE IF NOT EXISTS content_quality_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    completeness_score FLOAT DEFAULT 0.0,
    engagement_score FLOAT DEFAULT 0.0,
    creator_score FLOAT DEFAULT 0.0,
    freshness_score FLOAT DEFAULT 0.0,
    media_quality_score FLOAT DEFAULT 0.0,
    overall_score FLOAT DEFAULT 0.0,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id)
);

-- 审核队列表
CREATE TABLE IF NOT EXISTS moderation_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    priority VARCHAR(50) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    assigned_to UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 审核结果表
CREATE TABLE IF NOT EXISTS moderation_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    moderator_id UUID REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    reason TEXT,
    risk_level VARCHAR(50),
    automated BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创作者成长表
CREATE TABLE IF NOT EXISTS creator_growth (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    total_uploads INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    quality_rating FLOAT DEFAULT 0.0,
    badges JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(100),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 内容标签关联表
CREATE TABLE IF NOT EXISTS content_tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, tag_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_content_creator_id ON content(creator_id);
CREATE INDEX IF NOT EXISTS idx_content_status ON content(status);
CREATE INDEX IF NOT EXISTS idx_content_moderation_status ON content(moderation_status);
CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at);
CREATE INDEX IF NOT EXISTS idx_content_interactions_user_id ON content_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_content_interactions_content_id ON content_interactions(content_id);
CREATE INDEX IF NOT EXISTS idx_content_interactions_type ON content_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_moderation_queue_status ON moderation_queue(status);
CREATE INDEX IF NOT EXISTS idx_moderation_queue_priority ON moderation_queue(priority);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要 updated_at 的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_moderation_queue_updated_at BEFORE UPDATE ON moderation_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();