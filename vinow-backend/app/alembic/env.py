内容系统-数据库迁移脚本

import os  # 导入操作系统模块
import sys  # 导入系统模块
from logging.config import fileConfig  # 导入日志配置
from sqlalchemy import engine_from_config, pool  # 导入SQLAlchemy引擎和连接池
from alembic import context  # 导入Alembic上下文
from app.config import settings  # 导入应用配置
from app.database.connection import Base  # 导入数据库基础类
from app.models.content_models import Content, ContentMedia, ContentInteraction  # 导入内容模型
from app.models.review_models import Review, ReviewDimensionConfig, ReviewHelpfulVote  # 导入评价模型

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 这是Alembic Config对象，提供对配置值的访问
config = context.config

# 设置SQLAlchemy URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 设置目标元数据
target_metadata = Base.metadata

# 其他配置值可以在alembic.ini文件中设置
# 例如：python_home = .

def run_migrations_offline() -> None:
    """
    在'离线'模式下运行迁移
    
    这里配置上下文只使用URL，不使用引擎
    虽然跳过引擎创建，但我们不需要在这里可用
    """
    # 获取数据库URL
    url = config.get_main_option("sqlalchemy.url")
    # 配置上下文
    context.configure(
        url=url,  # 数据库URL
        target_metadata=target_metadata,  # 目标元数据
        literal_binds=True,  # 字面绑定
        dialect_opts={"paramstyle": "named"},  # 方言选项
    )

    # 在事务中运行迁移
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    在'在线'模式下运行迁移
    
    在这种情况下，我们需要创建一个引擎并与上下文关联
    """
    # 从配置中获取连接配置
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # 配置部分
        prefix="sqlalchemy.",  # 前缀
        poolclass=pool.NullPool,  # 连接池类
    )

    # 连接数据库
    with connectable.connect() as connection:
        # 配置上下文
        context.configure(
            connection=connection,  # 数据库连接
            target_metadata=target_metadata,  # 目标元数据
            compare_type=True,  # 比较类型
            compare_server_default=True,  # 比较服务器默认值
        )

        # 在事务中运行迁移
        with context.begin_transaction():
            context.run_migrations()

# 根据模式选择运行方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()