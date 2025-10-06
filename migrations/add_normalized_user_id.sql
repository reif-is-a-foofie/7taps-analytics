-- Add normalized_user_id column to statements table
ALTER TABLE `taps_data.statements` 
ADD COLUMN IF NOT EXISTS normalized_user_id STRING;

-- Create index on normalized_user_id for fast lookups
CREATE INDEX IF NOT EXISTS `taps_data.statements_normalized_user_id_idx` 
ON `taps_data.statements` (normalized_user_id);

