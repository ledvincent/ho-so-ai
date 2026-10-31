from alembic import op
revision = '0009'
down_revision = '0008'
def upgrade():
    op.execute("ALTER TABLE procedure_analysis ADD COLUMN evidence_status jsonb NOT NULL DEFAULT '{}'::jsonb")
def downgrade():
    op.execute('ALTER TABLE procedure_analysis DROP COLUMN evidence_status')
