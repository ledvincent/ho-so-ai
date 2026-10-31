CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE procedure (
    code text PRIMARY KEY CHECK (code ~ '^[0-9]\.[0-9]{6}$'),
    audience text NOT NULL CHECK (audience IN ('citizen', 'foreigner')),
    current_snapshot_id bigint
);
CREATE TABLE source_page (
    id bigserial PRIMARY KEY,
    procedure_code text NOT NULL REFERENCES procedure(code),
    source_url text NOT NULL,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    fetched_at timestamptz NOT NULL,
    raw_path text NOT NULL,
    parser_version text NOT NULL,
    name text NOT NULL,
    status text NOT NULL CHECK (status IN ('parsed', 'needs_source_details')),
    issues jsonb NOT NULL DEFAULT '[]',
    UNIQUE (procedure_code, sha256, parser_version),
    UNIQUE (procedure_code, id)
);
ALTER TABLE procedure ADD CONSTRAINT current_snapshot_fk FOREIGN KEY (code, current_snapshot_id)
    REFERENCES source_page(procedure_code, id);
CREATE TABLE fact (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    kind text NOT NULL CHECK (kind IN ('steps', 'agency', 'conditions')),
    position integer NOT NULL,
    text_verbatim text NOT NULL CHECK (length(text_verbatim) > 0),
    UNIQUE (snapshot_id, kind, position)
);
CREATE TABLE requirement (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    position integer NOT NULL,
    group_heading text NOT NULL,
    text_verbatim text NOT NULL CHECK (length(text_verbatim) > 0),
    originals integer NOT NULL CHECK (originals >= 0),
    copies integer NOT NULL CHECK (copies >= 0),
    UNIQUE (snapshot_id, position)
);
CREATE TABLE submission_method (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    position integer NOT NULL,
    method text NOT NULL,
    processing_time_verbatim text NOT NULL,
    description_verbatim text NOT NULL,
    UNIQUE (snapshot_id, position)
);
CREATE TABLE fee (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    method text NOT NULL,
    text_verbatim text NOT NULL,
    amount numeric CHECK (amount >= 0),
    currency text CHECK (currency IN ('VND', 'USD')),
    condition_verbatim text,
    condition_status text NOT NULL CHECK (condition_status IN ('missing', 'not_separately_stated', 'captured')),
    detail_refs jsonb NOT NULL DEFAULT '[]',
    CHECK ((amount IS NULL) = (currency IS NULL)),
    CHECK (condition_status != 'captured' OR length(condition_verbatim) > 0)
);
CREATE TABLE form (
    sha256 text PRIMARY KEY CHECK (length(sha256) = 64),
    raw_path text NOT NULL,
    fields_json jsonb,
    review_status text NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft', 'reviewed')),
    reviewed_by text,
    reviewed_at timestamptz,
    CHECK (review_status != 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND fields_json IS NOT NULL))
);
CREATE TABLE procedure_form (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    source_url text NOT NULL,
    label text NOT NULL,
    form_sha256 text REFERENCES form(sha256),
    fetched_at timestamptz,
    UNIQUE (snapshot_id, source_url),
    UNIQUE (snapshot_id, id),
    CHECK ((form_sha256 IS NULL) = (fetched_at IS NULL))
);
CREATE TABLE requirement_form (
    requirement_id bigint NOT NULL REFERENCES requirement(id),
    procedure_form_id bigint NOT NULL REFERENCES procedure_form(id),
    PRIMARY KEY (requirement_id, procedure_form_id)
);
CREATE TABLE search_text (
    id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES source_page(id),
    kind text NOT NULL CHECK (kind IN ('name', 'summary', 'example_query', 'alias')),
    lang text NOT NULL,
    text text NOT NULL,
    embedding vector(1024),
    embedding_model text,
    tsv tsvector NOT NULL,
    UNIQUE (snapshot_id, kind, lang, text),
    CHECK ((embedding IS NULL) = (embedding_model IS NULL))
);
CREATE FUNCTION search_text_tsv() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.tsv := to_tsvector('simple', unaccent(NEW.text));
    RETURN NEW;
END $$;
CREATE TRIGGER search_text_tsv BEFORE INSERT OR UPDATE OF text ON search_text
FOR EACH ROW EXECUTE FUNCTION search_text_tsv();
CREATE INDEX search_text_vector ON search_text USING hnsw (embedding vector_cosine_ops);
CREATE INDEX search_text_keywords ON search_text USING gin (tsv);
CREATE INDEX search_text_trigrams ON search_text USING gin (text gin_trgm_ops);
CREATE INDEX search_text_snapshot ON search_text(snapshot_id);
