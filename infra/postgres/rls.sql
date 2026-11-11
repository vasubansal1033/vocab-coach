-- Row-level security for per-user tables. Apply after Alembic migrations on Postgres.
-- The app still filters by user_id in SQLAlchemy; RLS is a second layer.
-- Set app.current_user_id on each connection (see vocab.db.set_pg_user_context).

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_lemma_counts ENABLE ROW LEVEL SECURITY;
ALTER TABLE editor_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE drills ENABLE ROW LEVEL SECURITY;
ALTER TABLE drill_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE srs_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE lexicon_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE identities ENABLE ROW LEVEL SECURITY;

CREATE POLICY conversations_owner ON conversations
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY messages_owner ON messages
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY message_lemma_counts_owner ON message_lemma_counts
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY editor_runs_owner ON editor_runs
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY suggestions_owner ON suggestions
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY drills_owner ON drills
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY drill_attempts_owner ON drill_attempts
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY exercises_owner ON exercises
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY exercise_attempts_owner ON exercise_attempts
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY srs_cards_owner ON srs_cards
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY events_owner ON events
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY llm_calls_owner ON llm_calls
  USING (user_id IS NULL OR user_id = current_setting('app.current_user_id', true));
CREATE POLICY lexicon_submissions_owner ON lexicon_submissions
  USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY identities_owner ON identities
  USING (user_id = current_setting('app.current_user_id', true));

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO vocab_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vocab_app;
