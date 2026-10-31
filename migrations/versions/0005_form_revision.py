from alembic import op
revision='0005'
down_revision='0004'
def upgrade():
    op.execute('''ALTER TABLE form ADD COLUMN revision_reference text;
    ALTER TABLE form ADD COLUMN issued_on date;
    ALTER TABLE form ADD COLUMN effective_from date;
    ALTER TABLE form ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
    ALTER TABLE form ADD COLUMN superseded_by_sha256 text REFERENCES form(sha256);
    ALTER TABLE source_page ADD COLUMN published_on date;
    ALTER TABLE source_page ADD COLUMN updated_on date;''')
def downgrade():
    raise RuntimeError('Restore a backup instead')
