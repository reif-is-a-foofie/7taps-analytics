-- Create csv_imports table for tracking CSV uploads
CREATE TABLE IF NOT EXISTS `taps_data.csv_imports` (
  filename STRING NOT NULL,
  normalized_user_id STRING,
  original_data JSON,
  imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(imported_at)
CLUSTER BY normalized_user_id, filename;

