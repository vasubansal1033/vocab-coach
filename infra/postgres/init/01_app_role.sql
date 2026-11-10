-- App role used by the FastAPI process. Password comes from the container env
-- only for local compose; production should create the role out of band.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vocab_app') THEN
    CREATE ROLE vocab_app LOGIN PASSWORD 'vocab_app_dev';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE vocab TO vocab_app;
