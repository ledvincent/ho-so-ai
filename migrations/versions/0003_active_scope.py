from alembic import op

revision = '0003'
down_revision = '0002'

def upgrade():
    op.execute('ALTER TABLE procedure ADD COLUMN active boolean NOT NULL DEFAULT false')

def downgrade():
    raise RuntimeError('Restore a backup instead')
