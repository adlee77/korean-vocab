-- Korean Vocab App — Supabase Schema
-- Run this in the Supabase SQL editor before seeding data.

-- vocab table (static data, read-only for users)
CREATE TABLE IF NOT EXISTS vocab (
  id BIGINT PRIMARY KEY,
  korean TEXT NOT NULL,
  english TEXT NOT NULL,
  word_type TEXT NOT NULL DEFAULT 'vocab',
  level TEXT NOT NULL DEFAULT '',
  tags TEXT
);

-- user progress
CREATE TABLE IF NOT EXISTS user_progress (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  vocab_id BIGINT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
  memorized BOOLEAN NOT NULL DEFAULT false,
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, vocab_id)
);

-- user deleted/hidden words
CREATE TABLE IF NOT EXISTS user_deleted (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  vocab_id BIGINT NOT NULL REFERENCES vocab(id) ON DELETE CASCADE,
  deleted_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, vocab_id)
);

-- RLS policies
ALTER TABLE vocab ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_deleted ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vocab is public read" ON vocab FOR SELECT USING (true);
CREATE POLICY "users manage own progress" ON user_progress FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users manage own deleted" ON user_deleted FOR ALL USING (auth.uid() = user_id);
