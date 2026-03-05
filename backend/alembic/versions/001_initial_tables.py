"""initial tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('num_rows', sa.Integer()),
        sa.Column('num_columns', sa.Integer()),
        sa.Column('columns_info', sa.JSON()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'experiments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('model_type', sa.String(100), nullable=False),
        sa.Column('target_column', sa.String(255), nullable=False),
        sa.Column('test_size', sa.Float(), default=0.2),
        sa.Column('metrics_json', sa.JSON()),
        sa.Column('model_path', sa.String(500)),
        sa.Column('feature_columns', sa.JSON()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('experiment_id', sa.Integer(), sa.ForeignKey('experiments.id'), nullable=False),
        sa.Column('input_json', sa.JSON(), nullable=False),
        sa.Column('prediction', sa.String(255)),
        sa.Column('probability', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('predictions')
    op.drop_table('experiments')
    op.drop_table('datasets')
