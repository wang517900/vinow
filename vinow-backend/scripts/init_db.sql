商家系统板块5内容营销

-- 创建业务指标表
CREATE TABLE IF NOT EXISTS business_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    customer_count INTEGER NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    order_count INTEGER NOT NULL,
    rating DECIMAL(3,2) NOT NULL,
    health_score INTEGER NOT NULL CHECK (health_score >= 0 AND health_score <= 100),
    competitor_count INTEGER DEFAULT 0,
    rating_rank INTEGER DEFAULT 1,
    better_than_peers DECIMAL(5,2) DEFAULT 0,
    morning_revenue DECIMAL(15,2),
    lunch_revenue DECIMAL(15,2),
    afternoon_revenue DECIMAL(15,2),
    evening_revenue DECIMAL(15,2),
    customer_count_yesterday INTEGER,
    revenue_yesterday DECIMAL(15,2),
    order_count_yesterday INTEGER,
    rating_yesterday DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date)
);

-- 创建预警表
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    level VARCHAR(20) NOT NULL CHECK (level IN ('critical', 'warning', 'normal')),
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    business_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建收入趋势表
CREATE TABLE IF NOT EXISTS revenue_trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date DATE NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    period VARCHAR(20) CHECK (period IN ('morning', 'lunch', 'afternoon', 'evening')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建竞对分析表
CREATE TABLE IF NOT EXISTS competitor_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date DATE NOT NULL,
    total_competitors INTEGER NOT NULL,
    rating_rank INTEGER NOT NULL,
    price_level VARCHAR(50) NOT NULL,
    customer_flow_rank INTEGER NOT NULL,
    promotion_intensity VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_date)
);

-- 创建营销活动表
CREATE TABLE IF NOT EXISTS marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    investment DECIMAL(15,2) NOT NULL,
    revenue_generated DECIMAL(15,2) NOT NULL,
    new_customers INTEGER NOT NULL,
    roi DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建评价表
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date DATE NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    keywords TEXT[] DEFAULT '{}',
    is_responded BOOLEAN DEFAULT FALSE,
    response TEXT,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建评价关键词表
CREATE TABLE IF NOT EXISTS review_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date DATE NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    frequency INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_date, keyword)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_business_metrics_date ON business_metrics(date);
CREATE INDEX IF NOT EXISTS idx_alerts_date_resolved ON alerts(business_date, is_resolved);
CREATE INDEX IF NOT EXISTS idx_revenue_trends_date ON revenue_trends(business_date);
CREATE INDEX IF NOT EXISTS idx_reviews_date_rating ON reviews(business_date, rating);
CREATE INDEX IF NOT EXISTS idx_reviews_responded ON reviews(is_responded);

-- 插入示例数据
INSERT INTO business_metrics (
    date, customer_count, revenue, order_count, rating, health_score,
    competitor_count, rating_rank, better_than_peers,
    morning_revenue, lunch_revenue, afternoon_revenue, evening_revenue
) VALUES (
    CURRENT_DATE, 156, 12800000, 89, 4.7, 85,
    8, 2, 92.0,
    1200000, 5800000, 900000, 6900000
) ON CONFLICT (date) DO UPDATE SET
    customer_count = EXCLUDED.customer_count,
    revenue = EXCLUDED.revenue,
    order_count = EXCLUDED.order_count,
    rating = EXCLUDED.rating,
    health_score = EXCLUDED.health_score,
    updated_at = NOW();

-- 创建更新时间的触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_business_metrics_updated_at BEFORE UPDATE ON business_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_revenue_trends_updated_at BEFORE UPDATE ON revenue_trends FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();