"""Allow local candidate associations without inventing a download timestamp."""
from alembic import op

revision = '0010'
down_revision = '0009'


def upgrade():
    op.execute('ALTER TABLE procedure_form DROP CONSTRAINT procedure_form_check')
    op.execute('''ALTER TABLE procedure_form ADD CONSTRAINT procedure_form_check CHECK (
        (form_sha256 IS NULL AND fetched_at IS NULL) OR
        (form_sha256 IS NOT NULL AND (fetched_at IS NOT NULL OR association_method='filename_fallback'))
    )''')


def downgrade():
    raise RuntimeError('Local candidates may have unknown retrieval dates; restore a backup instead.')
