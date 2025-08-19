-- Create proper normalized schema using lesson_url as main connector
-- This replaces the messy current structure with clean, relational tables

-- 1. Lessons table - main entity
CREATE TABLE IF NOT EXISTS lessons (
    id SERIAL PRIMARY KEY,
    lesson_url VARCHAR(500) UNIQUE NOT NULL,
    lesson_number INTEGER,
    lesson_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Questions table - questions within lessons
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    lesson_id INTEGER REFERENCES lessons(id),
    question_number INTEGER,
    question_text TEXT,
    question_type VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(lesson_id, question_number)
);

-- 3. Users table - normalized user data
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    cohort VARCHAR(100),
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. User activities table - all user interactions
CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    lesson_id INTEGER REFERENCES lessons(id),
    question_id INTEGER REFERENCES questions(id),
    activity_type VARCHAR(100), -- 'lesson_start', 'question_answer', 'lesson_complete', etc.
    activity_data JSONB, -- store additional activity data
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50), -- 'xapi' or 'csv'
    raw_statement_id VARCHAR(255), -- keep reference to original data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. User responses table - specific question responses
CREATE TABLE IF NOT EXISTS user_responses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    question_id INTEGER REFERENCES questions(id),
    response_text TEXT,
    response_value VARCHAR(255),
    is_correct BOOLEAN,
    score_raw NUMERIC,
    score_scaled NUMERIC,
    duration_seconds INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50),
    raw_statement_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_lessons_url ON lessons(lesson_url);
CREATE INDEX IF NOT EXISTS idx_lessons_number ON lessons(lesson_number);
CREATE INDEX IF NOT EXISTS idx_questions_lesson ON questions(lesson_id);
CREATE INDEX IF NOT EXISTS idx_questions_number ON questions(question_number);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_user ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_lesson ON user_activities(lesson_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp ON user_activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_responses_user ON user_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_user_responses_question ON user_responses(question_id);
CREATE INDEX IF NOT EXISTS idx_user_responses_timestamp ON user_responses(timestamp);

-- Insert lessons from existing data
INSERT INTO lessons (lesson_url, lesson_number, lesson_name)
SELECT DISTINCT 
    ce1.extension_value as lesson_url,
    CAST(ce2.extension_value AS INTEGER) as lesson_number,
    CASE 
        WHEN ce1.extension_value = 'https://7taps.com/lessons/screen-habits-awareness' THEN 'Screen Habits Awareness'
        WHEN ce1.extension_value = 'https://7taps.com/lessons/connection-balance' THEN 'Connection Balance'
        WHEN ce1.extension_value = 'https://7taps.com/lessons/device-relationship' THEN 'Device Relationship'
        WHEN ce1.extension_value = 'https://7taps.com/lessons/digital-wellness-foundations' THEN 'Digital Wellness Foundations'
        WHEN ce1.extension_value = 'https://7taps.com/lessons/productivity-focus' THEN 'Productivity Focus'
        ELSE 'Unknown Lesson'
    END as lesson_name
FROM context_extensions_new ce1
LEFT JOIN context_extensions_new ce2 ON ce1.statement_id = ce2.statement_id 
    AND ce2.extension_key = 'https://7taps.com/lesson-number'
WHERE ce1.extension_key = 'https://7taps.com/lesson-url'
    AND ce1.extension_value != ''
ON CONFLICT (lesson_url) DO NOTHING;

-- Insert users from existing data
INSERT INTO users (user_id, cohort, first_seen, last_seen)
SELECT DISTINCT 
    s.actor_id as user_id,
    ce.extension_value as cohort,
    MIN(s.timestamp) as first_seen,
    MAX(s.timestamp) as last_seen
FROM statements_new s
LEFT JOIN context_extensions_new ce ON s.statement_id = ce.statement_id 
    AND ce.extension_key = 'https://7taps.com/cohort'
WHERE s.actor_id IS NOT NULL
GROUP BY s.actor_id, ce.extension_value
ON CONFLICT (user_id) DO UPDATE SET
    last_seen = EXCLUDED.last_seen,
    cohort = COALESCE(EXCLUDED.cohort, users.cohort);

-- Insert questions from existing data
INSERT INTO questions (lesson_id, question_number, question_text, question_type)
SELECT DISTINCT 
    l.id as lesson_id,
    CAST(ce2.extension_value AS INTEGER) as question_number,
    'Question ' || ce2.extension_value as question_text,
    'multiple_choice' as question_type
FROM context_extensions_new ce1
JOIN lessons l ON ce1.extension_value = l.lesson_url
JOIN context_extensions_new ce2 ON ce1.statement_id = ce2.statement_id 
    AND ce2.extension_key = 'https://7taps.com/global-q'
WHERE ce1.extension_key = 'https://7taps.com/lesson-url'
    AND ce1.extension_value != ''
ON CONFLICT (lesson_id, question_number) DO NOTHING;

-- Insert user activities from existing data
INSERT INTO user_activities (user_id, lesson_id, question_id, activity_type, activity_data, timestamp, source, raw_statement_id)
SELECT DISTINCT
    u.id as user_id,
    l.id as lesson_id,
    q.id as question_id,
    s.verb_id as activity_type,
    s.raw_json as activity_data,
    s.timestamp,
    s.source,
    s.statement_id as raw_statement_id
FROM statements_new s
JOIN users u ON s.actor_id = u.user_id
LEFT JOIN context_extensions_new ce1 ON s.statement_id = ce1.statement_id 
    AND ce1.extension_key = 'https://7taps.com/lesson-url'
LEFT JOIN lessons l ON ce1.extension_value = l.lesson_url
LEFT JOIN context_extensions_new ce2 ON s.statement_id = ce2.statement_id 
    AND ce2.extension_key = 'https://7taps.com/global-q'
LEFT JOIN questions q ON l.id = q.lesson_id AND CAST(ce2.extension_value AS INTEGER) = q.question_number
WHERE s.actor_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- Insert user responses from existing data
INSERT INTO user_responses (user_id, question_id, response_text, response_value, is_correct, score_raw, score_scaled, duration_seconds, timestamp, source, raw_statement_id)
SELECT DISTINCT
    u.id as user_id,
    q.id as question_id,
    r.response as response_text,
    r.response as response_value,
    r.success as is_correct,
    r.score_raw,
    r.score_scaled,
    CAST(REPLACE(r.duration, 'PT', '') AS INTEGER) as duration_seconds,
    s.timestamp,
    s.source,
    s.statement_id as raw_statement_id
FROM statements_new s
JOIN users u ON s.actor_id = u.user_id
JOIN results_new r ON s.statement_id = r.statement_id
LEFT JOIN context_extensions_new ce1 ON s.statement_id = ce1.statement_id 
    AND ce1.extension_key = 'https://7taps.com/lesson-url'
LEFT JOIN lessons l ON ce1.extension_value = l.lesson_url
LEFT JOIN context_extensions_new ce2 ON s.statement_id = ce2.statement_id 
    AND ce2.extension_key = 'https://7taps.com/global-q'
LEFT JOIN questions q ON l.id = q.lesson_id AND CAST(ce2.extension_value AS INTEGER) = q.question_number
WHERE s.actor_id IS NOT NULL AND q.id IS NOT NULL
ON CONFLICT DO NOTHING;
