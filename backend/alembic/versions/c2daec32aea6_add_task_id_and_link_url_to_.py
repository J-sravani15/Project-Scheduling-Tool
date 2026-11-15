"""add_task_id_and_link_url_to_notifications

Revision ID: c2daec32aea6
Revises: b62facca1fb0
Create Date: 2026-10-23 21:57:28.449416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2daec32aea6'
down_revision: Union[str, Sequence[str], None] = 'b62facca1fb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('project_notifications', sa.Column('task_id', sa.UUID(), nullable=True))
    op.add_column('project_notifications', sa.Column('link_url', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_project_notifications_task_id'), 'project_notifications', ['task_id'], unique=False)
    op.create_foreign_key('fk_project_notifications_task_id_tasks', 'project_notifications', 'tasks', ['task_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_project_notifications_task_id_tasks', 'project_notifications', type_='foreignkey')
    op.drop_index(op.f('ix_project_notifications_task_id'), table_name='project_notifications')
    op.drop_column('project_notifications', 'link_url')
    op.drop_column('project_notifications', 'task_id')
