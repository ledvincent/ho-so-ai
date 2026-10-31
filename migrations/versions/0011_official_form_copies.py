"""Keep alternate official copies distinct from exact primary downloads."""
from alembic import op

revision = '0011'
down_revision = '0010'


def upgrade():
    op.execute('ALTER TABLE procedure_form DROP CONSTRAINT procedure_form_association_method_check')
    op.execute("""ALTER TABLE procedure_form ADD CONSTRAINT procedure_form_association_method_check
        CHECK (association_method IN ('direct_download','filename_fallback','official_copy'))""")


def downgrade():
    raise RuntimeError('Official-copy provenance must be retained; restore a backup instead.')
