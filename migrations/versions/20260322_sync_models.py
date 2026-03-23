"""synchronize models

Revision ID: 20260322_sync_models
Revises: 13765f1c46ca
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260322_sync_models'
down_revision: Union[str, Sequence[str], None] = '13765f1c46ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to match SQLAlchemy models."""
    # Adjust users table: if an old users table exists with different columns,
    # recreate it to match current models. This migration is written to be
    # idempotent in a fresh DB and may be destructive on existing data.

    # Drop users table if exists (this mirrors a schema sync; if you need to
    # preserve data, perform a proper migration instead).
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'users' in inspector.get_table_names():
        op.drop_table('users')

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('senha', sa.String(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    # Create agendamentos table
    if 'agendamentos' not in inspector.get_table_names():
        op.create_table(
            'agendamentos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data', sa.Date(), nullable=False),
            sa.Column('hora', sa.Time(), nullable=False),
            sa.UniqueConstraint('data', 'hora', name='uq_agendamentos_data_hora'),
        )

    # Create pagamentos table
    if 'pagamentos' not in inspector.get_table_names():
        op.create_table(
            'pagamentos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data_vencimento', sa.Date(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('comprovante', sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema: drop the tables created here and restore previous users table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'pagamentos' in inspector.get_table_names():
        op.drop_table('pagamentos')

    if 'agendamentos' in inspector.get_table_names():
        op.drop_table('agendamentos')

    if 'users' in inspector.get_table_names():
        op.drop_table('users')

    # Recreate the original users table as in the previous revision
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
