-- Create normalized schema for 7taps analytics
-- This replaces the current flat structure with proper relational tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS context_extensions CASCADE;
DROP TABLE IF EXISTS results CASCADE;
DROP TABLE IF EXISTS statements CASCADE;
DROP TABLE IF EXISTS activities CASCADE;
DROP TABLE IF EXISTS actors CASCADE;

-- 1. Actors table - normalized user data
CREATE TABLE actors (
    actor_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    account_name VARCHAR(255),
    account_homepage VARCHAR(500),
    source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Activities table - learning activities/cards
CREATE TABLE activities (
    activity_id VARCHAR(500) PRIMARY KEY,
    name TEXT,
    type VARCHAR(100), -- 'card', 'lesson', 'quiz', etc.
    description TEXT,
    lesson_number INTEGER,
    global_q_number INTEGER,
    pdf_page INTEGER,
    source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Statements table - core xAPI statements
CREATE TABLE statements (
    statement_id VARCHAR(255) PRIMARY KEY,
    actor_id VARCHAR(255) REFERENCES actors(actor_id),
    activity_id VARCHAR(500) REFERENCES activities(activity_id),
    verb_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    version VARCHAR(50),
    authority_actor_id VARCHAR(255),
    stored TIMESTAMPTZ,
    source VARCHAR(50) NOT NULL, -- 'csv' or 'xapi'
    raw_json JSONB, -- for audit/debug
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Results table - statement results and responses
CREATE TABLE results (
    statement_id VARCHAR(255) PRIMARY KEY REFERENCES statements(statement_id),
    success BOOLEAN,
    completion BOOLEAN,
    score_raw DECIMAL(10,2),
    score_scaled DECIMAL(5,4),
    score_min DECIMAL(10,2),
    score_max DECIMAL(10,2),
    duration VARCHAR(100),
    response TEXT, -- free-text responses from focus group
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Context extensions table - flexible metadata
CREATE TABLE context_extensions (
    id SERIAL PRIMARY KEY,
    statement_id VARCHAR(255) REFERENCES statements(statement_id),
    extension_key VARCHAR(255) NOT NULL,
    extension_value TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_actors_email ON actors(email);
CREATE INDEX idx_actors_source ON actors(source);
CREATE INDEX idx_statements_actor_id ON statements(actor_id);
CREATE INDEX idx_statements_activity_id ON statements(activity_id);
CREATE INDEX idx_statements_verb_id ON statements(verb_id);
CREATE INDEX idx_statements_timestamp ON statements(timestamp);
CREATE INDEX idx_statements_source ON statements(source);
CREATE INDEX idx_context_extensions_statement_id ON context_extensions(statement_id);
CREATE INDEX idx_context_extensions_key ON context_extensions(extension_key);

-- Create updated_at trigger for actors table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_actors_updated_at BEFORE UPDATE ON actors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for easy querying
CREATE OR REPLACE VIEW vw_focus_group_responses AS
SELECT 
    s.statement_id,
    a.name as learner_name,
    a.email as learner_email,
    act.name as activity_name,
    act.type as activity_type,
    act.lesson_number,
    act.global_q_number,
    s.verb_id,
    s.timestamp,
    r.response,
    r.success,
    r.completion
FROM statements s
JOIN actors a ON s.actor_id = a.actor_id
JOIN activities act ON s.activity_id = act.activity_id
LEFT JOIN results r ON s.statement_id = r.statement_id
WHERE s.source = 'csv'
ORDER BY s.timestamp DESC;

CREATE OR REPLACE VIEW vw_user_progress AS
SELECT 
    a.actor_id,
    a.name as learner_name,
    a.email as learner_email,
    COUNT(s.statement_id) as total_statements,
    COUNT(DISTINCT s.activity_id) as unique_activities,
    COUNT(CASE WHEN r.completion = true THEN 1 END) as completed_activities,
    MIN(s.timestamp) as first_activity,
    MAX(s.timestamp) as last_activity,
    a.source
FROM actors a
LEFT JOIN statements s ON a.actor_id = s.actor_id
LEFT JOIN results r ON s.statement_id = r.statement_id
GROUP BY a.actor_id, a.name, a.email, a.source
ORDER BY total_statements DESC;

-- Create function to normalize actor_id
CREATE OR REPLACE FUNCTION normalize_actor_id(
    p_email VARCHAR(255),
    p_account_name VARCHAR(255),
    p_name VARCHAR(255)
) RETURNS VARCHAR(255) AS $$
BEGIN
    -- Clean and normalize email
    IF p_email IS NOT NULL AND p_email != '' THEN
        -- Remove 'mailto:' prefix and convert to lowercase
        RETURN LOWER(REPLACE(p_email, 'mailto:', ''));
    END IF;
    
    -- Use account name if available
    IF p_account_name IS NOT NULL AND p_account_name != '' THEN
        RETURN LOWER(p_account_name);
    END IF;
    
    -- Fallback to name
    IF p_name IS NOT NULL AND p_name != '' THEN
        RETURN LOWER(p_name);
    END IF;
    
    -- Final fallback
    RETURN 'unknown_actor';
END;
$$ LANGUAGE plpgsql;
