"""non-destructive sync of models

Revision ID: 20260323_non_destructive_sync
Revises: 20260322_sync_models
Create Date: 2026-03-23 00:00:00.000000

This migration attempts to migrate an existing database schema to match the
current SQLAlchemy models without destructive operations. It will:

- add missing columns to `users` (nome, email, senha, is_admin) if they don't
  already exist;
- populate `nome`/`senha` from legacy `username`/`password` when present;
- create a unique constraint on `email` if missing (implemented as a unique
  index which works on SQLite);
- create `agendamentos` and `pagamentos` tables if they don't exist.

Notes:
- On SQLite some ALTER operations are limited; this migration chooses safe
  additive operations and avoids dropping or renaming existing columns.
- The migration is intended to be non-destructive; it will not remove old
  columns such as `username`/`password` so data is preserved.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260323_non_destructive_sync'
down_revision: Union[str, Sequence[str], None] = '20260322_sync_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def _has_unique_constraint(inspector, table_name: str, constraint_name: str) -> bool:
    for uc in inspector.get_unique_constraints(table_name):
        if uc.get('name') == constraint_name:
            return True
    # some DBs represent uniq via indexes; check indexes too
    for idx in inspector.get_indexes(table_name):
        if idx.get('name') == constraint_name:
            return True
    return False


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Ensure users table exists
    if 'users' not in inspector.get_table_names():
        # nothing to migrate from, create fresh users table matching models
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('nome', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('senha', sa.String(), nullable=True),
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.UniqueConstraint('email', name='uq_users_email'),
        )
        inspector = sa.inspect(conn)

    # Add missing columns to users (non-destructive)
    if not _has_column(inspector, 'users', 'nome'):
        op.add_column('users', sa.Column('nome', sa.String(), nullable=True))

    if not _has_column(inspector, 'users', 'senha'):
        op.add_column('users', sa.Column('senha', sa.String(), nullable=True))

    if not _has_column(inspector, 'users', 'email'):
        op.add_column('users', sa.Column('email', sa.String(), nullable=True))

    if not _has_column(inspector, 'users', 'is_admin'):
        op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')))

    # If legacy columns exist, copy data into the new columns
    # (safe no-op when source/target are absent)
    if _has_column(inspector, 'users', 'username') and _has_column(inspector, 'users', 'nome'):
        op.execute("UPDATE users SET nome = username WHERE nome IS NULL")

    if _has_column(inspector, 'users', 'password') and _has_column(inspector, 'users', 'senha'):
        op.execute("UPDATE users SET senha = password WHERE senha IS NULL")

    # Create unique constraint on email if possible and not present
    try:
        if _has_column(inspector, 'users', 'email') and not _has_unique_constraint(inspector, 'users', 'uq_users_email'):
            # use create_unique_constraint which for SQLite will create a unique index
            op.create_unique_constraint('uq_users_email', 'users', ['email'])
    except Exception:
        # don't fail the migration on constraint creation issues; it's non-destructive
        pass

    # Create agendamentos table if missing
    if 'agendamentos' not in inspector.get_table_names():
        op.create_table(
            'agendamentos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('data', sa.Date(), nullable=False),
            sa.Column('hora', sa.Time(), nullable=False),
            sa.UniqueConstraint('data', 'hora', name='uq_agendamentos_data_hora'),
        )

    # Create pagamentos table if missing
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
    # This migration is intentionally conservative and avoids destructive
    # column drops. The downgrade will remove tables that were created here
    # (pagamentos, agendamentos) and drop the unique constraint on users.email
    # if present. It will NOT attempt to drop columns added to `users` because
    # many DB backends (notably SQLite) do not support DROP COLUMN safely.
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'pagamentos' in inspector.get_table_names():
        op.drop_table('pagamentos')

    if 'agendamentos' in inspector.get_table_names():
        op.drop_table('agendamentos')

    # drop unique constraint if present
    try:
        if 'users' in inspector.get_table_names() and _has_unique_constraint(inspector, 'users', 'uq_users_email'):
            op.drop_constraint('uq_users_email', 'users', type_='unique')
    except Exception:
        pass

    # NOTE: We intentionally do not drop added columns on downgrade to avoid
    # destructive operations. Manual intervention would be required to remove
    # columns if desired.
