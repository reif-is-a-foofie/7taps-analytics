# Legacy Tables Documentation

## Overview
These tables are marked with the `LEGACY_` prefix and should **NOT** be used for new development.

## Legacy Tables

### LEGACY_statements_new
- **Original name:** statements_new
- **Purpose:** Transitional table from flat to normalized schema
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` and `user_responses` tables

### LEGACY_results_new  
- **Original name:** results_new
- **Purpose:** Transitional results table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_responses` table

### LEGACY_context_extensions_new
- **Original name:** context_extensions_new
- **Purpose:** Transitional context extensions table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Data is now in `lessons`, `questions`, and `user_activities` tables

### LEGACY_statements_flat
- **Original name:** statements_flat
- **Purpose:** Original flat xAPI statements storage
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` table

### LEGACY_statements_normalized
- **Original name:** statements_normalized
- **Purpose:** Attempted normalized xAPI schema
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` table

### LEGACY_activities
- **Original name:** activities
- **Purpose:** xAPI activities table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `lessons` and `questions` tables

### LEGACY_actors
- **Original name:** actors
- **Purpose:** xAPI actors table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `users` table

## Current Active Schema

### Primary Tables (Use These)
- `lessons` - Main lesson entities
- `users` - Normalized user data  
- `questions` - Questions within lessons
- `user_activities` - All user interactions
- `user_responses` - Specific question responses

### How to Query
```sql
-- Instead of LEGACY tables, use:
SELECT * FROM user_activities;  -- instead of LEGACY_statements_new
SELECT * FROM user_responses;   -- instead of LEGACY_results_new
SELECT * FROM lessons;          -- instead of LEGACY_activities
SELECT * FROM users;            -- instead of LEGACY_actors
```

## Migration Notes
- Legacy tables contain historical data that may be migrated to proper schema
- Do not create new queries using LEGACY_ tables
- Legacy tables can be dropped after confirming data migration
