内容板块-初始迁移脚本

"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op  # 导入Alembic操作
import sqlalchemy as sa  # 导入SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY  # 导入PostgreSQL特定类型

# revision identifiers, used by Alembic.
revision = '001'  # 修订ID
down_revision = None  # 前一个修订ID（没有前一个）
branch_labels = None  # 分支标签
depends_on = None  # 依赖关系

def upgrade() -> None:
    """升级数据库 - 创建所有表"""
    # 创建内容表
    op.create_table('contents',
        sa.Column('id', UUID(), nullable=False),  # 内容ID
        sa.Column('content_type', sa.String(50), nullable=False),  # 内容类型
        sa.Column('title', sa.String(500), nullable=True),  # 标题
        sa.Column('description', sa.Text(), nullable=True),  # 描述
        sa.Column('author_id', UUID(), nullable=False),  # 作者ID
        sa.Column('author_name', sa.String(200), nullable=True),  # 作者名称
        sa.Column('author_avatar', sa.String(500), nullable=True),  # 作者头像
        sa.Column('target_entity_type', sa.String(100), nullable=True),  # 目标实体类型
        sa.Column('target_entity_id', UUID(), nullable=True),  # 目标实体ID
        sa.Column('target_entity_name', sa.String(200), nullable=True),  # 目标实体名称
        sa.Column('status', sa.String(50), nullable=False),  # 状态
        sa.Column('visibility', sa.String(50), nullable=False),  # 可见性
        sa.Column('is_anonymous', sa.Boolean(), nullable=False),  # 是否匿名
        sa.Column('tags', ARRAY(sa.String()), nullable=True),  # 标签
        sa.Column('categories', ARRAY(sa.String()), nullable=True),  # 分类
        sa.Column('location_data', JSONB(), nullable=True),  # 位置数据
        sa.Column('language', sa.String(10), nullable=False),  # 语言
        sa.Column('like_count', sa.Integer(), nullable=False),  # 点赞数
        sa.Column('comment_count', sa.Integer(), nullable=False),  # 评论数
        sa.Column('share_count', sa.Integer(), nullable=False),  # 分享数
        sa.Column('view_count', sa.Integer(), nullable=False),  # 浏览数
        sa.Column('bookmark_count', sa.Integer(), nullable=False),  # 收藏数
        sa.Column('report_count', sa.Integer(), nullable=False),  # 举报数
        sa.Column('quality_score', sa.Float(), nullable=False),  # 质量评分
        sa.Column('engagement_rate', sa.Float(), nullable=False),  # 互动率
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), nullable=False),  # 更新时间
        sa.Column('published_at', sa.DateTime(), nullable=True),  # 发布时间
        sa.Column('moderated_at', sa.DateTime(), nullable=True),  # 审核时间
        sa.Column('moderator_id', UUID(), nullable=True),  # 审核员ID
        sa.Column('moderation_notes', sa.Text(), nullable=True),  # 审核备注
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.Index('ix_contents_content_type', 'content_type'),  # 内容类型索引
        sa.Index('ix_contents_author_id', 'author_id'),  # 作者ID索引
        sa.Index('ix_contents_target_entity_type', 'target_entity_type'),  # 目标实体类型索引
        sa.Index('ix_contents_target_entity_id', 'target_entity_id'),  # 目标实体ID索引
        sa.Index('ix_contents_status', 'status'),  # 状态索引
        sa.Index('ix_contents_created_at', 'created_at'),  # 创建时间索引
    )
    
    # 创建内容媒体表
    op.create_table('content_media',
        sa.Column('id', UUID(), nullable=False),  # 媒体ID
        sa.Column('content_id', UUID(), nullable=False),  # 内容ID
        sa.Column('file_url', sa.String(1000), nullable=False),  # 文件URL
        sa.Column('file_type', sa.String(50), nullable=False),  # 文件类型
        sa.Column('file_name', sa.String(500), nullable=False),  # 文件名
        sa.Column('file_size', sa.Integer(), nullable=False),  # 文件大小
        sa.Column('mime_type', sa.String(100), nullable=False),  # MIME类型
        sa.Column('duration', sa.Integer(), nullable=True),  # 时长
        sa.Column('width', sa.Integer(), nullable=True),  # 宽度
        sa.Column('height', sa.Integer(), nullable=True),  # 高度
        sa.Column('thumbnail_url', sa.String(1000), nullable=True),  # 缩略图URL
        sa.Column('processing_status', sa.String(50), nullable=False),  # 处理状态
        sa.Column('processing_metadata', JSONB(), nullable=True),  # 处理元数据
        sa.Column('display_order', sa.Integer(), nullable=False),  # 显示顺序
        sa.Column('caption', sa.Text(), nullable=True),  # 标题
        sa.Column('alt_text', sa.String(500), nullable=True),  # 替代文本
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), nullable=False),  # 更新时间
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),  # 外键约束
        sa.Index('ix_content_media_content_id', 'content_id'),  # 内容ID索引
    )
    
    # 创建内容互动表
    op.create_table('content_interactions',
        sa.Column('id', UUID(), nullable=False),  # 互动ID
        sa.Column('content_id', UUID(), nullable=False),  # 内容ID
        sa.Column('user_id', UUID(), nullable=False),  # 用户ID
        sa.Column('interaction_type', sa.String(50), nullable=False),  # 互动类型
        sa.Column('interaction_data', JSONB(), nullable=True),  # 互动数据
        sa.Column('device_fingerprint', sa.String(255), nullable=True),  # 设备指纹
        sa.Column('ip_address', sa.String(45), nullable=True),  # IP地址
        sa.Column('user_agent', sa.String(500), nullable=True),  # 用户代理
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), nullable=False),  # 更新时间
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),  # 外键约束
        sa.Index('ix_content_interactions_content_id', 'content_id'),  # 内容ID索引
        sa.Index('ix_content_interactions_user_id', 'user_id'),  # 用户ID索引
        sa.Index('ix_content_interactions_interaction_type', 'interaction_type'),  # 互动类型索引
        sa.Index('ix_content_interactions_created_at', 'created_at'),  # 创建时间索引
    )
    
    # 创建评价表
    op.create_table('reviews',
        sa.Column('id', UUID(), nullable=False),  # 评价ID
        sa.Column('content_id', UUID(), nullable=False),  # 内容ID
        sa.Column('overall_rating', sa.DECIMAL(2, 1), nullable=False),  # 总体评分
        sa.Column('rating_breakdown', JSONB(), nullable=False),  # 评分细分
        sa.Column('verification_status', sa.String(50), nullable=False),  # 验证状态
        sa.Column('order_id', UUID(), nullable=True),  # 订单ID
        sa.Column('purchase_date', sa.DateTime(), nullable=True),  # 购买日期
        sa.Column('pros', ARRAY(sa.String()), nullable=True),  # 优点
        sa.Column('cons', ARRAY(sa.String()), nullable=True),  # 缺点
        sa.Column('review_tags', ARRAY(sa.String()), nullable=True),  # 评价标签
        sa.Column('helpful_votes', sa.Integer(), nullable=False),  # 有用投票
        sa.Column('unhelpful_votes', sa.Integer(), nullable=False),  # 无用投票
        sa.Column('business_reply', sa.Text(), nullable=True),  # 商家回复
        sa.Column('business_reply_at', sa.DateTime(), nullable=True),  # 商家回复时间
        sa.Column('business_replier_id', UUID(), nullable=True),  # 商家回复人ID
        sa.Column('has_followup', sa.Boolean(), nullable=False),  # 是否有追评
        sa.Column('followup_review_id', UUID(), nullable=True),  # 追评ID
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), nullable=False),  # 更新时间
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.ForeignKeyConstraint(['content_id'], ['contents.id']),  # 内容外键
        sa.ForeignKeyConstraint(['followup_review_id'], ['reviews.id']),  # 追评外键
        sa.UniqueConstraint('content_id'),  # 内容ID唯一约束
        sa.CheckConstraint('overall_rating >= 1.0 AND overall_rating <= 5.0', name='check_rating_range'),  # 评分范围检查
        sa.Index('ix_reviews_content_id', 'content_id'),  # 内容ID索引
        sa.Index('ix_reviews_order_id', 'order_id'),  # 订单ID索引
    )
    
    # 创建评价维度配置表
    op.create_table('review_dimension_configs',
        sa.Column('id', UUID(), nullable=False),  # 配置ID
        sa.Column('business_type', sa.String(100), nullable=False),  # 业务类型
        sa.Column('dimension_name', sa.String(100), nullable=False),  # 维度名称
        sa.Column('dimension_key', sa.String(50), nullable=False),  # 维度键
        sa.Column('display_order', sa.Integer(), nullable=False),  # 显示顺序
        sa.Column('is_required', sa.Boolean(), nullable=False),  # 是否必填
        sa.Column('is_active', sa.Boolean(), nullable=False),  # 是否激活
        sa.Column('display_name_vi', sa.String(200), nullable=True),  # 越南语显示名
        sa.Column('display_name_en', sa.String(200), nullable=True),  # 英语显示名
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.Column('updated_at', sa.DateTime(), nullable=False),  # 更新时间
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.Index('ix_review_dimension_configs_business_type', 'business_type'),  # 业务类型索引
    )
    
    # 创建评价有用性投票表
    op.create_table('review_helpful_votes',
        sa.Column('id', UUID(), nullable=False),  # 投票ID
        sa.Column('review_id', UUID(), nullable=False),  # 评价ID
        sa.Column('user_id', UUID(), nullable=False),  # 用户ID
        sa.Column('is_helpful', sa.Boolean(), nullable=False),  # 是否有用
        sa.Column('device_fingerprint', sa.String(255), nullable=True),  # 设备指纹
        sa.Column('ip_address', sa.String(45), nullable=True),  # IP地址
        sa.Column('created_at', sa.DateTime(), nullable=False),  # 创建时间
        sa.PrimaryKeyConstraint('id'),  # 主键约束
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),  # 评价外键
        sa.CheckConstraint('is_helpful IN (True, False)', name='check_helpful_value'),  # 有用性检查
        sa.Index('ix_review_helpful_votes_review_id', 'review_id'),  # 评价ID索引
        sa.Index('ix_review_helpful_votes_user_id', 'user_id'),  # 用户ID索引
    )
    
    # 插入默认的评价维度配置
    op.bulk_insert(
        sa.table('review_dimension_configs',
            sa.column('id', UUID()),
            sa.column('business_type', sa.String(100)),
            sa.column('dimension_name', sa.String(100)),
            sa.column('dimension_key', sa.String(50)),
            sa.column('display_order', sa.Integer()),
            sa.column('is_required', sa.Boolean()),
            sa.column('is_active', sa.Boolean()),
            sa.column('display_name_vi', sa.String(200)),
            sa.column('display_name_en', sa.String(200)),
            sa.column('created_at', sa.DateTime()),
            sa.column('updated_at', sa.DateTime()),
        ),
        [
            # 餐饮行业维度
            {
                'id': '11111111-1111-1111-1111-111111111111',
                'business_type': 'restaurant',
                'dimension_name': '总体评分',
                'dimension_key': 'overall',
                'display_order': 1,
                'is_required': True,
                'is_active': True,
                'display_name_vi': 'Đánh giá tổng thể',
                'display_name_en': 'Overall Rating',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '11111111-1111-1111-1111-111111111112',
                'business_type': 'restaurant',
                'dimension_name': '味道',
                'dimension_key': 'taste',
                'display_order': 2,
                'is_required': True,
                'is_active': True,
                'display_name_vi': 'Hương vị',
                'display_name_en': 'Taste',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '11111111-1111-1111-1111-111111111113',
                'business_type': 'restaurant',
                'dimension_name': '环境',
                'dimension_key': 'environment',
                'display_order': 3,
                'is_required': False,
                'is_active': True,
                'display_name_vi': 'Môi trường',
                'display_name_en': 'Environment',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '11111111-1111-1111-1111-111111111114',
                'business_type': 'restaurant',
                'dimension_name': '服务',
                'dimension_key': 'service',
                'display_order': 4,
                'is_required': False,
                'is_active': True,
                'display_name_vi': 'Dịch vụ',
                'display_name_en': 'Service',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '11111111-1111-1111-1111-111111111115',
                'business_type': 'restaurant',
                'dimension_name': '性价比',
                'dimension_key': 'value',
                'display_order': 5,
                'is_required': False,
                'is_active': True,
                'display_name_vi': 'Giá trị',
                'display_name_en': 'Value',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            # 美业维度
            {
                'id': '22222222-2222-2222-2222-222222222221',
                'business_type': 'beauty',
                'dimension_name': '总体评分',
                'dimension_key': 'overall',
                'display_order': 1,
                'is_required': True,
                'is_active': True,
                'display_name_vi': 'Đánh giá tổng thể',
                'display_name_en': 'Overall Rating',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '22222222-2222-2222-2222-222222222222',
                'business_type': 'beauty',
                'dimension_name': '技术',
                'dimension_key': 'skill',
                'display_order': 2,
                'is_required': True,
                'is_active': True,
                'display_name_vi': 'Kỹ thuật',
                'display_name_en': 'Skill',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '22222222-2222-2222-2222-222222222223',
                'business_type': 'beauty',
                'dimension_name': '效果',
                'dimension_key': 'result',
                'display_order': 3,
                'is_required': True,
                'is_active': True,
                'display_name_vi': 'Hiệu quả',
                'display_name_en': 'Result',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '22222222-2222-2222-2222-222222222224',
                'business_type': 'beauty',
                'dimension_name': '服务',
                'dimension_key': 'service',
                'display_order': 4,
                'is_required': False,
                'is_active': True,
                'display_name_vi': 'Dịch vụ',
                'display_name_en': 'Service',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
            {
                'id': '22222222-2222-2222-2222-222222222225',
                'business_type': 'beauty',
                'dimension_name': '环境',
                'dimension_key': 'environment',
                'display_order': 5,
                'is_required': False,
                'is_active': True,
                'display_name_vi': 'Môi trường',
                'display_name_en': 'Environment',
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00',
            },
        ]
    )

def downgrade() -> None:
    """降级数据库 - 删除所有表"""
    # 删除表的顺序与创建顺序相反（考虑外键约束）
    op.drop_table('review_helpful_votes')  # 删除评价有用性投票表
    op.drop_table('review_dimension_configs')  # 删除评价维度配置表
    op.drop_table('reviews')  # 删除评价表
    op.drop_table('content_interactions')  # 删除内容互动表
    op.drop_table('content_media')  # 删除内容媒体表
    op.drop_table('contents')  # 删除内容表


    内容板块-数据库迁移脚本

"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建视频内容表
    op.create_table('video_contents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('merchant_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('resolution', sa.String(20), nullable=True),
        sa.Column('format', sa.String(10), nullable=True),
        sa.Column('transcoding_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('transcoding_progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('share_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.String(36), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_contents_user_id'), 'video_contents', ['user_id'], unique=False)
    op.create_index(op.f('ix_video_contents_merchant_id'), 'video_contents', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_video_contents_status'), 'video_contents', ['status'], unique=False)
    op.create_index(op.f('ix_video_contents_created_at'), 'video_contents', ['created_at'], unique=False)

    # 创建视频转码配置表
    op.create_table('video_transcoding_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('video_id', sa.String(36), nullable=False),
        sa.Column('profile_name', sa.String(50), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('video_bitrate', sa.Integer(), nullable=False),
        sa.Column('audio_bitrate', sa.Integer(), nullable=False),
        sa.Column('file_key', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(10), nullable=False, server_default='mp4'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('cdn_url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['video_contents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_transcoding_profiles_video_id'), 'video_transcoding_profiles', ['video_id'], unique=False)

    # 创建视频缩略图表
    op.create_table('video_thumbnails',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('video_id', sa.String(36), nullable=False),
        sa.Column('thumbnail_type', sa.String(20), nullable=False),
        sa.Column('time_offset', sa.Float(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('file_key', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(10), nullable=False, server_default='jpg'),
        sa.Column('cdn_url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['video_contents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_thumbnails_video_id'), 'video_thumbnails', ['video_id'], unique=False)

    # 创建视频分析数据表
    op.create_table('video_analytics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('video_id', sa.String(36), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_viewers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('watch_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_25', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_50', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_75', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_100', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['video_contents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_analytics_video_id'), 'video_analytics', ['video_id'], unique=False)
    op.create_index(op.f('ix_video_analytics_date'), 'video_analytics', ['date'], unique=False)

    # 创建视频用户互动表
    op.create_table('video_interactions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('video_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('interaction_type', sa.String(20), nullable=False),
        sa.Column('watch_duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('watch_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['video_contents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_interactions_video_id'), 'video_interactions', ['video_id'], unique=False)
    op.create_index(op.f('ix_video_interactions_user_id'), 'video_interactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_video_interactions_created_at'), 'video_interactions', ['created_at'], unique=False)
    op.create_index('idx_video_user_interaction', 'video_interactions', ['video_id', 'user_id', 'interaction_type'], unique=False)


def downgrade() -> None:
    op.drop_table('video_interactions')
    op.drop_table('video_analytics')
    op.drop_table('video_thumbnails')
    op.drop_table('video_transcoding_profiles')
    op.drop_table('video_contents')