-- Separate PostgreSQL deployment design. PC pilot currently uses SQLite.
-- Run against a NEW dedicated database only, with an authorised provisioning role.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS book_research;
CREATE TABLE IF NOT EXISTS book_research.books (
 id text PRIMARY KEY,
 title text NOT NULL,
 author text,
 original_path text NOT NULL,
 edition text,
 metadata_status text NOT NULL DEFAULT 'unverified',
 extraction_warnings jsonb NOT NULL DEFAULT '[]',
 imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS book_research.passages (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 book_id text NOT NULL REFERENCES book_research.books(id),
 pdf_page integer NOT NULL,
 page_label text,
 printed_page_verified boolean NOT NULL DEFAULT false,
 section text,
 text text NOT NULL,
 tags text[] NOT NULL DEFAULT '{}',
 tag_method text NOT NULL,
 tag_status text NOT NULL DEFAULT 'unreviewed',
 embedding_model_digest text NOT NULL,
 embedding vector(768),
 search_text tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED
);
CREATE INDEX IF NOT EXISTS passage_vectors ON book_research.passages USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS passage_words ON book_research.passages USING gin (search_text);
CREATE INDEX IF NOT EXISTS passage_tags ON book_research.passages USING gin (tags);
CREATE INDEX IF NOT EXISTS passage_pages ON book_research.passages(book_id,pdf_page);
-- Use a separately provisioned login role for MCP and grant SELECT only on a view
-- excluding original_path. The importer must have a different write-capable role.
CREATE OR REPLACE VIEW book_research.book_catalogue AS
 SELECT id,title,author,edition,metadata_status,extraction_warnings,imported_at
 FROM book_research.books;
