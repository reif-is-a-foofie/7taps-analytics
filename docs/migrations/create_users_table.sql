-- Create users table for normalized user profiles
CREATE TABLE IF NOT EXISTS `taps_data.users` (
  user_id STRING NOT NULL,
  email STRING,
  name STRING,
  sources ARRAY<STRING>,
  first_seen TIMESTAMP,
  last_seen TIMESTAMP,
  activity_count INT64,
  csv_data ARRAY<JSON>,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, email;

-- Create index on email for fast lookups
CREATE INDEX IF NOT EXISTS `taps_data.users_email_idx` 
ON `taps_data.users` (email);

-- Create index on user_id for fast lookups
CREATE INDEX IF NOT EXISTS `taps_data.users_user_id_idx` 
ON `taps_data.users` (user_id);

