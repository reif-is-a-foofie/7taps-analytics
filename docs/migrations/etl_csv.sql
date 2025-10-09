-- ETL script to load CSV focus group data into normalized schema
-- This treats CSV rows as statements with verb = "responded"

-- Function to extract card info from card text
CREATE OR REPLACE FUNCTION extract_card_info(card_text TEXT)
RETURNS TABLE(card_number TEXT, card_type TEXT, question TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN card_text ~ 'Card \d+' 
            THEN (regexp_match(card_text, 'Card (\d+)'))[1]
            ELSE NULL
        END as card_number,
        CASE 
            WHEN card_text ~ '\([^)]+\)' 
            THEN (regexp_match(card_text, '\(([^)]+)\)'))[1]
            ELSE NULL
        END as card_type,
        CASE 
            WHEN card_text ~ ':' 
            THEN trim(substring(card_text from ':(.*)$'))
            ELSE card_text
        END as question;
END;
$$ LANGUAGE plpgsql;

-- Insert actors from CSV data (normalized)
INSERT INTO actors (actor_id, name, email, account_name, source)
SELECT DISTINCT
    normalize_actor_id(NULL, "Learner", "Learner") as actor_id,
    "Learner" as name,
    NULL as email,
    "Learner" as account_name,
    'csv' as source
FROM (
    SELECT DISTINCT "Learner" FROM focus_group_csv
) csv_learners
ON CONFLICT (actor_id) DO NOTHING;

-- Insert activities from CSV data
INSERT INTO activities (activity_id, name, type, description, lesson_number, global_q_number, pdf_page, source)
SELECT DISTINCT
    'focus_group_card_' || COALESCE(ci.card_number, "Global Q#") as activity_id,
    COALESCE(ci.question, "Card") as name,
    COALESCE(ci.card_type, "Card type") as type,
    'Focus group ' || "Card type" || ' question from lesson ' || "Lesson Number" as description,
    "Lesson Number"::integer as lesson_number,
    "Global Q#"::integer as global_q_number,
    "PDF Page #"::integer as pdf_page,
    'csv' as source
FROM focus_group_csv fgc
CROSS JOIN LATERAL extract_card_info(fgc."Card") ci
ON CONFLICT (activity_id) DO NOTHING;

-- Insert statements from CSV data (treating each response as a statement)
INSERT INTO statements (
    statement_id,
    actor_id,
    activity_id,
    verb_id,
    timestamp,
    source,
    raw_json
)
SELECT 
    'focus_group_' || uuid_generate_v4()::text as statement_id,
    normalize_actor_id(NULL, "Learner", "Learner") as actor_id,
    'focus_group_card_' || COALESCE(ci.card_number, "Global Q#") as activity_id,
    'http://adlnet.gov/expapi/verbs/responded' as verb_id,
    NOW() as timestamp, -- Using current timestamp since CSV doesn't have timestamps
    'csv' as source,
    jsonb_build_object(
        'learner', "Learner",
        'card', "Card",
        'card_type', "Card type",
        'lesson_number', "Lesson Number",
        'global_q', "Global Q#",
        'pdf_page', "PDF Page #",
        'response', "Response",
        'source', 'focus_group_csv'
    ) as raw_json
FROM focus_group_csv fgc
CROSS JOIN LATERAL extract_card_info(fgc."Card") ci
ON CONFLICT (statement_id) DO NOTHING;

-- Insert results (responses) from CSV data
INSERT INTO results (statement_id, response, success, completion)
SELECT 
    s.statement_id,
    fgc."Response" as response,
    true as success, -- All focus group responses are considered successful
    true as completion -- All focus group responses are considered completed
FROM statements s
JOIN focus_group_csv fgc ON 
    s.actor_id = normalize_actor_id(NULL, fgc."Learner", fgc."Learner")
    AND s.source = 'csv'
    AND s.raw_json->>'response' = fgc."Response"
ON CONFLICT (statement_id) DO NOTHING;

-- Insert context extensions for CSV data
INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    s.statement_id,
    'focus_group_import' as extension_key,
    'true' as extension_value
FROM statements s
WHERE s.source = 'csv'
ON CONFLICT DO NOTHING;

-- Insert additional context extensions for CSV data
INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    s.statement_id,
    'card_type' as extension_key,
    fgc."Card type" as extension_value
FROM statements s
JOIN focus_group_csv fgc ON 
    s.actor_id = normalize_actor_id(NULL, fgc."Learner", fgc."Learner")
    AND s.source = 'csv'
    AND s.raw_json->>'response' = fgc."Response"
ON CONFLICT DO NOTHING;

INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    s.statement_id,
    'lesson_number' as extension_key,
    fgc."Lesson Number" as extension_value
FROM statements s
JOIN focus_group_csv fgc ON 
    s.actor_id = normalize_actor_id(NULL, fgc."Learner", fgc."Learner")
    AND s.source = 'csv'
    AND s.raw_json->>'response' = fgc."Response"
ON CONFLICT DO NOTHING;

INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    s.statement_id,
    'global_q' as extension_key,
    fgc."Global Q#" as extension_value
FROM statements s
JOIN focus_group_csv fgc ON 
    s.actor_id = normalize_actor_id(NULL, fgc."Learner", fgc."Learner")
    AND s.source = 'csv'
    AND s.raw_json->>'response' = fgc."Response"
ON CONFLICT DO NOTHING;

INSERT INTO context_extensions (statement_id, extension_key, extension_value)
SELECT 
    s.statement_id,
    'pdf_page' as extension_key,
    fgc."PDF Page #" as extension_value
FROM statements s
JOIN focus_group_csv fgc ON 
    s.actor_id = normalize_actor_id(NULL, fgc."Learner", fgc."Learner")
    AND s.source = 'csv'
    AND s.raw_json->>'response' = fgc."Response"
ON CONFLICT DO NOTHING;
