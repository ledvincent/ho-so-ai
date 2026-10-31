from alembic import op

revision = '0008'
down_revision = '0007'


def upgrade():
    op.execute('''
    CREATE TABLE embedding_space (
        id text PRIMARY KEY, configuration jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE embedding_cache (
        space_id text NOT NULL REFERENCES embedding_space(id), input_hash text NOT NULL,
        input_text text NOT NULL, embedding vector(1024), attempts integer NOT NULL DEFAULT 0,
        retry_after timestamptz, lease_until timestamptz, lease_token uuid, error text,
        PRIMARY KEY(space_id,input_hash));
    CREATE INDEX embedding_cache_pending ON embedding_cache(space_id,retry_after)
        WHERE embedding IS NULL;
    CREATE TABLE rag_release (
        id uuid PRIMARY KEY, space_id text NOT NULL REFERENCES embedding_space(id),
        fingerprint text NOT NULL UNIQUE, status text NOT NULL DEFAULT 'building'
            CHECK(status IN ('building','published')),
        min_similarity double precision CHECK(min_similarity>0 AND min_similarity<=1),
        created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_member (
        release_id uuid NOT NULL REFERENCES rag_release(id), code text NOT NULL REFERENCES procedure(code),
        snapshot_id bigint NOT NULL REFERENCES source_page(id),
        profile_id bigint NOT NULL REFERENCES procedure_profile(id), name text NOT NULL,
        profile jsonb NOT NULL, PRIMARY KEY(release_id,code));
    CREATE TABLE rag_source (
        release_id uuid NOT NULL, code text NOT NULL, id text NOT NULL,
        kind text NOT NULL, title text NOT NULL, url text NOT NULL, locator text NOT NULL,
        body text NOT NULL, PRIMARY KEY(release_id,id),
        FOREIGN KEY(release_id,code) REFERENCES rag_member(release_id,code));
    CREATE TABLE rag_item (
        id bigserial PRIMARY KEY, release_id uuid NOT NULL, code text NOT NULL,
        source_id text, kind text NOT NULL CHECK(kind IN ('routing','evidence')),
        input_hash text NOT NULL, body text NOT NULL, normalized text NOT NULL,
        tsv tsvector NOT NULL, embedding vector(1024),
        start_offset integer, end_offset integer,
        FOREIGN KEY(release_id,code) REFERENCES rag_member(release_id,code),
        FOREIGN KEY(release_id,source_id) REFERENCES rag_source(release_id,id));
    CREATE INDEX rag_item_scope ON rag_item(release_id,kind,code);
    CREATE INDEX rag_item_keywords ON rag_item USING gin(tsv);
    CREATE INDEX rag_item_typo ON rag_item USING gin(normalized gin_trgm_ops);
    CREATE INDEX rag_item_vector ON rag_item USING hnsw(embedding vector_cosine_ops);
    CREATE TABLE rag_head (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
        release_id uuid NOT NULL REFERENCES rag_release(id));
    CREATE INDEX fee_snapshot_method ON fee(snapshot_id,method);
    CREATE INDEX comparison_right ON procedure_comparison(batch_id,right_code);
    CREATE INDEX catalog_completed ON catalog_batch(baseline_id,created_at DESC) WHERE status='complete';
    ''')


def downgrade():
    raise RuntimeError('Restore a backup instead of deleting retrieval releases')
