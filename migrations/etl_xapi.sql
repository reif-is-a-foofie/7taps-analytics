-- ETL script to migrate existing xAPI data to normalized schema
-- This processes the existing statements_flat table

-- First, migrate actors from existing data
INSERT INTO actors (actor_id, name, email, account_name, account_homepage, source)
SELECT DISTINCT
    normalize_actor_id(
        CASE 
            WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
            THEN raw_statement->'actor'->>'mbox'
            ELSE NULL
        END,
        CASE 
            WHEN raw_statement->'actor'->'account'->>'name' IS NOT NULL 
            THEN raw_statement->'actor'->'account'->>'name'
            ELSE NULL
        END,
        CASE 
            WHEN raw_statement->'actor'->>'name' IS NOT NULL 
            THEN raw_statement->'actor'->>'name'
            ELSE NULL
        END
    ) as actor_id,
    raw_statement->'actor'->>'name' as name,
    CASE 
        WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
        THEN LOWER(REPLACE(raw_statement->'actor'->>'mbox', 'mailto:', ''))
        ELSE NULL
    END as email,
    raw_statement->'actor'->'account'->>'name' as account_name,
    raw_statement->'actor'->'account'->>'homePage' as account_homepage,
    'xapi' as source
FROM statements_flat
WHERE raw_statement IS NOT NULL
ON CONFLICT (actor_id) DO NOTHING;

-- Migrate activities from existing data
INSERT INTO activities (activity_id, name, type, description, source)
SELECT DISTINCT
    raw_statement->'object'->>'id' as activity_id,
    CASE 
        WHEN raw_statement->'object'->'definition'->'name'->>'en-US' IS NOT NULL 
        THEN raw_statement->'object'->'definition'->'name'->>'en-US'
        ELSE raw_statement->'object'->>'id'
    END as name,
    raw_statement->'object'->>'objectType' as type,
    CASE 
        WHEN raw_statement->'object'->'definition'->'description'->>'en-US' IS NOT NULL 
        THEN raw_statement->'object'->'definition'->'description'->>'en-US'
        ELSE NULL
    END as description,
    'xapi' as source
FROM statements_flat
WHERE raw_statement IS NOT NULL
ON CONFLICT (activity_id) DO NOTHING;

-- Migrate statements from existing data
INSERT INTO statements (
    statement_id, 
    actor_id, 
    activity_id, 
    verb_id, 
    timestamp, 
    version, 
    authority_actor_id, 
    stored, 
    source, 
    raw_json
)
SELECT 
    raw_statement->>'id' as statement_id,
    normalize_actor_id(
        CASE 
            WHEN raw_statement->'actor'->>'mbox' IS NOT NULL 
            THEN raw_statement->'actor'->>'mbox'
            ELSE NULL
        END,
        CASE 
            WHEN raw_statement->'actor'->'account'->>'name' IS NOT NULL 
            THEN raw_statement->'actor'->'account'->>'name'
            ELSE NULL
        END,
        CASE 
            WHEN raw_statement->'actor'->>'name' IS NOT NULL 
            THEN raw_statement->'actor'->>'name'
            ELSE NULL
        END
    ) as actor_id,
    raw_statement->'object'->>'id' as activity_id,
    raw_statement->'verb'->>'id' as verb_id,
    (raw_statement->>'timestamp')::timestamptz as timestamp,
    raw_statement->>'version' as version,
    CASE 
        WHEN raw_statement->'authority'->'account'->>'name' IS NOT NULL 
        THEN raw_statement->'authority'->'account'->>'name'
        ELSE NULL
    END as authority_actor_id,
    (raw_statement->>'stored')::timestamptz as stored,
    'xapi' as source,
    raw_statement as raw_json
FROM statements_flat
WHERE raw_statement IS NOT NULL
ON CONFLICT (statement_id) DO NOTHING;

-- Migrate results from existing data
INSERT INTO results (
    statement_id,
    success,
    completion,
    score_raw,
    score_scaled,
    score_min,
    score_max,
    duration
)
SELECT 
    raw_statement->>'id' as statement_id,
    (raw_statement->'result'->>'success')::boolean as success,
    (raw_statement->'result'->>'completion')::boolean as completion,
    (raw_statement->'result'->'score'->>'raw')::decimal as score_raw,
    (raw_statement->'result'->'score'->>'scaled')::decimal as score_scaled,
    (raw_statement->'result'->'score'->>'min')::decimal as score_min,
    (raw_statement->'result'->'score'->>'max')::decimal as score_max,
    raw_statement->'result'->>'duration' as duration
FROM statements_flat
WHERE raw_statement->'result' IS NOT NULL
ON CONFLICT (statement_id) DO NOTHING;

-- Migrate context extensions from existing data
INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    raw_statement->>'id' as statement_id,
    key as extension_key,
    value::text as extension_value
FROM statements_flat,
LATERAL jsonb_each(raw_statement->'context'->'extensions') as ext(key, value)
WHERE raw_statement->'context'->'extensions' IS NOT NULL
ON CONFLICT DO NOTHING;

-- Also migrate platform and language as extensions
INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    raw_statement->>'id' as statement_id,
    'platform' as extension_key,
    raw_statement->'context'->>'platform' as extension_value
FROM statements_flat
WHERE raw_statement->'context'->>'platform' IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    raw_statement->>'id' as statement_id,
    'language' as extension_key,
    raw_statement->'context'->>'language' as extension_value
FROM statements_flat
WHERE raw_statement->'context'->>'language' IS NOT NULL
ON CONFLICT DO NOTHING;
