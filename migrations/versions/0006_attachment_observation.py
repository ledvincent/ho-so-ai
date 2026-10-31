from alembic import op

revision = '0006'
down_revision = '0005'


def upgrade():
    op.execute('''CREATE TABLE attachment_observation (
        id bigserial PRIMARY KEY,
        run_id uuid REFERENCES analysis_run(id),
        snapshot_id bigint REFERENCES source_page(id),
        source_url text NOT NULL,
        original_filename text,
        form_sha256 text REFERENCES form(sha256),
        fetched_at timestamptz NOT NULL,
        status text NOT NULL CHECK(status IN ('downloaded','failed','historical_download')),
        error text,
        CHECK ((status='failed') = (form_sha256 IS NULL))
    );
    CREATE INDEX attachment_observation_source ON attachment_observation(snapshot_id,source_url);
    ALTER TABLE form ADD COLUMN mapping_metadata jsonb NOT NULL DEFAULT '{}';''')


def downgrade():
    raise RuntimeError('Restore a backup instead of deleting source observations')
