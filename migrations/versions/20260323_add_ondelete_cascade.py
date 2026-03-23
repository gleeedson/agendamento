"""add ondelete cascade to foreign keys

Revision ID: 20260323_add_ondelete_cascade
Revises: 20260323_non_destructive_sync
Create Date: 2026-03-23 12:00:00.000000

This migration updates the `agendamentos` and `pagamentos` tables to use
FOREIGN KEY ... ON DELETE CASCADE. For SQLite this requires recreating the
tables; the migration copies existing data into the new tables to preserve
content (non-destructive).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260323_add_ondelete_cascade'
down_revision: Union[str, Sequence[str], None] = '20260323_non_destructive_sync'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Update agendamentos
    if _table_exists(inspector, 'agendamentos'):
        op.create_table(
            'agendamentos_new',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('data', sa.Date(), nullable=False),
            sa.Column('hora', sa.Time(), nullable=False),
            sa.UniqueConstraint('data', 'hora', name='uq_agendamentos_data_hora'),
        )

        # copy data
        op.execute('INSERT INTO agendamentos_new (id, id_usuario, data, hora) SELECT id, id_usuario, data, hora FROM agendamentos')
        op.drop_table('agendamentos')
        op.rename_table('agendamentos_new', 'agendamentos')
    else:
        op.create_table(
            'agendamentos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('data', sa.Date(), nullable=False),
            sa.Column('hora', sa.Time(), nullable=False),
            sa.UniqueConstraint('data', 'hora', name='uq_agendamentos_data_hora'),
        )

    # Update pagamentos
    if _table_exists(inspector, 'pagamentos'):
        op.create_table(
            'pagamentos_new',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('data_vencimento', sa.Date(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('comprovante', sa.String(), nullable=True),
        )

        # copy data
        op.execute("INSERT INTO pagamentos_new (id, id_usuario, data_vencimento, status, comprovante) SELECT id, id_usuario, data_vencimento, status, comprovante FROM pagamentos")
        op.drop_table('pagamentos')
        op.rename_table('pagamentos_new', 'pagamentos')
    else:
        op.create_table(
            'pagamentos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('data_vencimento', sa.Date(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('comprovante', sa.String(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Recreate original agendamentos without ON DELETE CASCADE
    if _table_exists(inspector, 'agendamentos'):
        op.create_table(
            'agendamentos_old',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data', sa.Date(), nullable=False),
            sa.Column('hora', sa.Time(), nullable=False),
            sa.UniqueConstraint('data', 'hora', name='uq_agendamentos_data_hora'),
        )
        op.execute('INSERT INTO agendamentos_old (id, id_usuario, data, hora) SELECT id, id_usuario, data, hora FROM agendamentos')
        op.drop_table('agendamentos')
        op.rename_table('agendamentos_old', 'agendamentos')

    # Recreate original pagamentos without ON DELETE CASCADE
    if _table_exists(inspector, 'pagamentos'):
        op.create_table(
            'pagamentos_old',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data_vencimento', sa.Date(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('comprovante', sa.String(), nullable=True),
        )
        op.execute("INSERT INTO pagamentos_old (id, id_usuario, data_vencimento, status, comprovante) SELECT id, id_usuario, data_vencimento, status, comprovante FROM pagamentos")
        op.drop_table('pagamentos')
        op.rename_table('pagamentos_old', 'pagamentos')
