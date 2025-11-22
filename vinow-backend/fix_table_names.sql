-- fix_table_names.sql - 修复可能的表名拼写错误
-- 这个脚本处理表名拼写不一致的问题

-- 检查所有可能的表名变体
DO $$ 
BEGIN
    -- 检查是否存在拼写错误的表
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_prederences') THEN
        RAISE NOTICE '发现拼写错误的表: user_prederences';
        -- 重命名表
        ALTER TABLE user_prederences RENAME TO user_preferences;
        RAISE NOTICE '✅ 已重命名 user_prederences → user_preferences';
    END IF;
    
    -- 检查其他可能的表名变体
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_preference') THEN
        RAISE NOTICE '发现单数表名: user_preference';
        ALTER TABLE user_preference RENAME TO user_preferences;
        RAISE NOTICE '✅ 已重命名 user_preference → user_preferences';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'userprofile') THEN
        RAISE NOTICE '发现无下划线表名: userprofile';
        ALTER TABLE userprofile RENAME TO user_profiles;
        RAISE NOTICE '✅ 已重命名 userprofile → user_profiles';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_profiles') THEN
        RAISE EXCEPTION '❌ user_profiles 表不存在，请运行完整修复脚本';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_preferences') THEN
        RAISE EXCEPTION '❌ user_preferences 表不存在，请运行完整修复脚本';
    END IF;
    
    RAISE NOTICE '✅ 表名检查完成';
END $$;