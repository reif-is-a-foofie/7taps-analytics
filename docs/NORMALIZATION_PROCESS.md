# User Normalization Process Overview

## Current Architecture

### 1. **Email Normalization**
- **Process**: Lowercase + strip whitespace
- **Validation**: Basic regex pattern matching
- **Output**: Consistent email format for matching

### 2. **User ID Generation**
- **Primary Key**: Normalized email address
- **Fallback**: Account name, OpenID, or actor ID
- **Consistency**: Same email → same user_id

### 3. **Data Source Integration**

#### **xAPI Statements** (Real-time)
- Extracts: email (from `actor.mbox`), name, timestamp
- Normalizes: Email → user_id
- Enriches: Adds CSV metadata if user exists in `users` table
- Stores: Enriched statement in `statements` table

#### **CSV Imports** (Batch)
- Extracts: Email, name, Team, Group, Location, Phone, ID
- Normalizes: Email → user_id
- Merges: With existing xAPI users if email matches
- Stores: CSV data in `users.csv_data` array

### 4. **Automatic Enrichment Flow**

```
xAPI Statement Arrives
    ↓
Extract user info (email, name)
    ↓
Normalize email → user_id
    ↓
Check users table for existing user
    ↓
If CSV data exists:
    Extract Team, Group, Location, Phone
    Compute cohort_id (Team + Group)
    ↓
Enrich statement with CSV metadata:
    - context.extensions["https://7taps.com/csv-metadata"]
    - actor.extensions["https://7taps.com/csv-metadata"]
    ↓
Store enriched statement in BigQuery
```

## Idempotency Guarantees

### **Statements Idempotency**
✅ **Duplicate Detection**: Early check for `statement_id` existence before processing  
✅ **MERGE Statement**: Uses BigQuery MERGE to ensure idempotent inserts  
✅ **Safe Retries**: Same statement can be sent multiple times, only stored once  

**Implementation**:
- `statement_exists()` check before processing
- MERGE statement: `ON statement_id` → only inserts if not matched
- Early return if duplicate detected (acknowledges message)

### **Users Idempotency**
✅ **Email-Based Matching**: Users matched by normalized email  
✅ **MERGE Statement**: Uses BigQuery MERGE for upsert operations  
✅ **Cross-Source Merging**: Same user from xAPI and CSV merged into one record  

**Implementation**:
- `upsert_user()` uses MERGE: `ON user_id` → updates if matched, inserts if not
- CSV imports use same `upsert_user()` → automatic deduplication
- Sources array tracks all data sources for each user

### **CSV Import Idempotency**
✅ **User Deduplication**: Uses `normalize_csv_row()` → `upsert_user()` → MERGE  
✅ **Multiple Imports**: Same CSV can be imported multiple times safely  
✅ **User Merging**: CSV users automatically merge with existing xAPI users  

## Current Process Flow

### **ETL Pipeline** (`pubsub_bigquery_processor.py`)
1. Message arrives from Pub/Sub
2. **Check idempotency**: `statement_exists(statement_id)` → skip if exists
3. **Normalize** via `normalize_xapi_statement()`
4. **Enrich** with CSV metadata if available
5. Transform to BigQuery row format
6. **MERGE** into `statements` table (idempotent)

### **CSV Import** (`csv_import_service.py`)
1. Parse CSV file
2. For each row:
   - **Normalize** via `normalize_csv_row()`
   - **Upsert** user in `users` table (MERGE → idempotent)
   - Store CSV data in `users.csv_data` array
3. Store import record in `csv_imports` table

### **User Merging** (`user_normalization.py`)
- **Match Strategy**: Email-based (normalized)
- **Merge Logic**:
  - Preserve earliest `first_seen`
  - Update to latest `last_seen`
  - Combine `sources` array
  - Merge `csv_data` arrays
  - Prefer longer name if conflict

## Key Features

✅ **Automatic**: Runs on every xAPI statement  
✅ **Transparent**: Enrichment happens in ETL pipeline  
✅ **Cohort Derivation**: Automatically computes cohort_id from Team+Group  
✅ **Deduplication**: Merges users across sources by email  
✅ **Metadata Preservation**: CSV data stored in `users.csv_data` array  
✅ **Idempotent**: Same statement/user can be processed multiple times safely  

## Idempotency Examples

### Example 1: Duplicate xAPI Statement
```
Statement sent twice with same statement_id:
1. First arrival → processed, stored in BigQuery
2. Second arrival → detected as duplicate, skipped, message acknowledged
Result: Only one record in database
```

### Example 2: Same User from xAPI and CSV
```
User "john@example.com" appears in:
1. xAPI statement → creates user record
2. CSV import → finds existing user, merges CSV data
Result: Single user record with both sources in `sources` array
```

### Example 3: CSV Imported Twice
```
Same CSV file imported twice:
1. First import → creates/updates users
2. Second import → finds existing users, updates `csv_data` array
Result: No duplicate users, CSV data merged
```

## Potential Issues & Considerations

1. **Email Matching Only**: No fuzzy matching for name variations
2. **CSV Data Array**: Multiple CSV entries per user (no deduplication within array)
3. **Performance**: Database lookup on every xAPI statement (mitigated by early duplicate check)
4. **Data Quality**: Depends on email consistency across sources
5. **Cohort Computation**: Always uses first CSV entry's Team+Group

## Questions to Discuss

1. **Matching Strategy**: Should we add name-based fuzzy matching?
2. **CSV Deduplication**: Should we deduplicate CSV entries per user?
3. **Performance**: Should we cache user lookups?
4. **Cohort Priority**: What if user has multiple CSV entries with different cohorts?
5. **Data Quality**: How do we handle email mismatches or typos?

