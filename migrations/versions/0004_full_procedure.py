from alembic import op

revision = '0004'
down_revision = '0003'

def upgrade():
    op.execute("""ALTER TABLE source_page ADD COLUMN document_json jsonb;
    ALTER TABLE procedure_analysis ADD COLUMN facts_ready boolean NOT NULL DEFAULT false;
    ALTER TABLE procedure_form ADD COLUMN association_method text NOT NULL DEFAULT 'direct_download'
        CHECK (association_method IN ('direct_download','filename_fallback'));
    CREATE TABLE form_family (
        code text PRIMARY KEY,
        preferred_sha256 text NOT NULL REFERENCES form(sha256),
        selection_basis text NOT NULL
    );""")

def downgrade():
    raise RuntimeError('Restore a backup instead')
