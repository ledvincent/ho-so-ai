from alembic import op

revision='0007'
down_revision='0006'


def upgrade():
    op.execute('''CREATE TABLE analysis_baseline (
        id text PRIMARY KEY, configuration jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    ALTER TABLE analysis_run ADD COLUMN baseline_id text REFERENCES analysis_baseline(id);
    CREATE TABLE procedure_profile (
        id bigserial PRIMARY KEY, snapshot_id bigint NOT NULL REFERENCES source_page(id),
        run_id uuid NOT NULL UNIQUE REFERENCES analysis_run(id), baseline_id text NOT NULL REFERENCES analysis_baseline(id),
        profile jsonb NOT NULL, sources jsonb NOT NULL, metadata jsonb NOT NULL,
        output_sha256 text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE procedure_profile_head (
        snapshot_id bigint PRIMARY KEY REFERENCES source_page(id), profile_id bigint NOT NULL REFERENCES procedure_profile(id));
    CREATE TABLE catalog_batch (
        id uuid PRIMARY KEY, baseline_id text NOT NULL REFERENCES analysis_baseline(id),
        status text NOT NULL, report jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE procedure_comparison (
        batch_id uuid NOT NULL REFERENCES catalog_batch(id), left_code text NOT NULL REFERENCES procedure(code),
        right_code text NOT NULL REFERENCES procedure(code), result jsonb NOT NULL,
        PRIMARY KEY(batch_id,left_code,right_code));
    ALTER TABLE search_text ADD COLUMN profile_id bigint REFERENCES procedure_profile(id);
    ''')


def downgrade():
    raise RuntimeError('Restore a backup instead of deleting analysis history')
