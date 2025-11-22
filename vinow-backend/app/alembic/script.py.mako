"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op  # 导入Alembic操作
import sqlalchemy as sa  # 导入SQLAlchemy
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}  # 修订ID
down_revision = ${repr(down_revision)}  # 前一个修订ID
branch_labels = ${repr(branch_labels)}  # 分支标签
depends_on = ${repr(depends_on)}  # 依赖关系

def upgrade() -> None:
    """升级数据库"""
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    """降级数据库"""
    ${downgrades if downgrades else "pass"}