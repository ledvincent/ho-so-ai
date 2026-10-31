from alembic import op

revision = '0002'
down_revision = '0001'


def upgrade():
    op.execute("""CREATE TABLE analysis_run (
        id uuid PRIMARY KEY, source_url text NOT NULL, procedure_code text REFERENCES procedure(code),
        started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
        status text NOT NULL, report jsonb NOT NULL DEFAULT '{}');
    CREATE TABLE procedure_analysis (
        snapshot_id bigint PRIMARY KEY REFERENCES source_page(id), run_id uuid NOT NULL REFERENCES analysis_run(id),
        sections jsonb NOT NULL, summary text NOT NULL, issues jsonb NOT NULL,
        readiness text NOT NULL CHECK(readiness IN ('blocked','needs_review','ready')));
    ALTER TABLE form ADD COLUMN pdf_path text;
    ALTER TABLE form ADD COLUMN analysis_issues jsonb NOT NULL DEFAULT '[]';
    CREATE TABLE form_field (
        form_sha256 text NOT NULL REFERENCES form(sha256), field_id text NOT NULL,
        page integer NOT NULL CHECK(page > 0), label text NOT NULL, field_type text NOT NULL,
        bbox jsonb NOT NULL, requiredness text NOT NULL DEFAULT 'unknown',
        owner text NOT NULL DEFAULT 'unknown', profile_key text,
        evidence text NOT NULL, review_status text NOT NULL DEFAULT 'draft',
        PRIMARY KEY(form_sha256,field_id));
    CREATE TABLE rag_chunk (
        id bigserial PRIMARY KEY, snapshot_id bigint NOT NULL REFERENCES source_page(id),
        form_sha256 text REFERENCES form(sha256), section text NOT NULL, position integer NOT NULL,
        text_verbatim text NOT NULL, source_url text NOT NULL, locator text NOT NULL,
        fetched_at timestamptz NOT NULL, embedding vector(1024), embedding_model text,
        tsv tsvector NOT NULL, UNIQUE(snapshot_id,section,position));
    CREATE FUNCTION rag_chunk_tsv() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN NEW.tsv := to_tsvector('simple',unaccent(NEW.text_verbatim)); RETURN NEW; END $$;
    CREATE TRIGGER rag_chunk_tsv BEFORE INSERT OR UPDATE OF text_verbatim ON rag_chunk
        FOR EACH ROW EXECUTE FUNCTION rag_chunk_tsv();
    CREATE INDEX rag_chunk_keywords ON rag_chunk USING gin(tsv);
    CREATE INDEX rag_chunk_vectors ON rag_chunk USING hnsw(embedding vector_cosine_ops);
    """)


def downgrade():
    raise RuntimeError('Restore a backup instead of deleting analysis records')
