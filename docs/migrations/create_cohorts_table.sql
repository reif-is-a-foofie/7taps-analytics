-- Create cohorts table for storing cohort definitions
CREATE TABLE IF NOT EXISTS `taps_data.cohorts` (
  cohort_id STRING NOT NULL,
  cohort_name STRING NOT NULL,
  team STRING,
  group_name STRING,
  description STRING,
  source STRING NOT NULL, -- 'data_derived' or 'manual'
  user_count INT64 DEFAULT 0,
  statement_count INT64 DEFAULT 0,
  last_activity TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  active BOOLEAN DEFAULT TRUE
)
PARTITION BY DATE(created_at)
CLUSTER BY cohort_id, team, group_name;

