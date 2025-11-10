# Idempotency Implementation

## Overview

The system ensures **idempotency** for both **users** and **statements**, meaning:
- Same statement sent multiple times → stored only once
- Same user from xAPI and CSV → merged into single record
- Same CSV imported multiple times → no duplicate users

## Statement Idempotency

### Implementation

**File**: `app/etl/pubsub_bigquery_processor.py`

1. **Early Duplicate Check**:
   ```python
   if statement_id and await self.statement_exists(statement_id):
       logger.info(f"Statement {statement_id} already exists, skipping duplicate")
       message.ack()  # Acknowledge since already processed
       return
   ```

2. **MERGE Statement** (safety net):
   ```sql
   MERGE `statements` T
   USING (SELECT @statement_id, @timestamp, ...) S
   ON T.statement_id = S.statement_id
   WHEN NOT MATCHED THEN INSERT ...
   ```
   - Only inserts if `statement_id` doesn't exist
   - No-op if statement already exists

### Flow

```
xAPI Statement Arrives
    ↓
Extract statement_id
    ↓
Check: statement_exists(statement_id)?
    ├─ YES → Skip, acknowledge message
    └─ NO → Process normally → MERGE (idempotent)
```

### Benefits

- ✅ Safe retries: Same statement can be sent multiple times
- ✅ No duplicates: Only one record per `statement_id`
- ✅ Performance: Early check avoids unnecessary processing

## User Idempotency

### Implementation

**File**: `app/services/user_normalization.py`

**MERGE Statement**:
```sql
MERGE `users` T
USING (SELECT @user_id, @email, @name, ...) S
ON T.user_id = S.user_id
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...
```

### Flow

```
User Data Arrives (xAPI or CSV)
    ↓
Normalize email → user_id
    ↓
Find existing user by user_id or email
    ├─ EXISTS → Merge data (sources, timestamps, csv_data)
    └─ NOT EXISTS → Create new user
    ↓
MERGE into users table (idempotent)
```

### Cross-Source Merging

**Example**: Same user from xAPI and CSV
```
1. xAPI statement arrives → creates user record
   {
     user_id: "john@example.com",
     sources: ["xapi"],
     csv_data: []
   }

2. CSV import arrives → finds existing user, merges
   {
     user_id: "john@example.com",
     sources: ["xapi", "csv"],
     csv_data: [{Team: "UVM", Group: "UVM", ...}]
   }
```

### Benefits

- ✅ Single source of truth: One user record per email
- ✅ Cross-source enrichment: CSV data enriches xAPI statements
- ✅ No duplicates: Same CSV imported twice → updates, not duplicates

## CSV Import Idempotency

### Implementation

**File**: `app/services/csv_import_service.py`

Uses `normalize_csv_row()` → `upsert_user()` → MERGE

### Flow

```
CSV Row Processed
    ↓
normalize_csv_row(row)
    ↓
extract_user_info_from_csv(row)
    ↓
upsert_user(user_info) → MERGE (idempotent)
    ↓
CSV data added to users.csv_data array
```

### Benefits

- ✅ Re-importable: Same CSV can be imported multiple times
- ✅ Incremental updates: New CSV data merges with existing
- ✅ User deduplication: Same user in multiple CSV rows → single record

## Testing Idempotency

### Test Case 1: Duplicate Statement
```python
# Send same statement twice
statement = {"id": "test-123", "actor": {...}, ...}
await publish_statement(statement)  # First time
await publish_statement(statement)  # Second time

# Expected: Only one record in statements table
```

### Test Case 2: Same User from Multiple Sources
```python
# xAPI statement
xapi_statement = {"actor": {"mbox": "mailto:john@example.com"}}
await process_statement(xapi_statement)

# CSV import
csv_row = {"Email": "john@example.com", "Team": "UVM"}
await import_csv_row(csv_row)

# Expected: Single user record with sources=["xapi", "csv"]
```

### Test Case 3: CSV Imported Twice
```python
csv_content = "Email,Team\njohn@example.com,UVM"
await import_csv(csv_content)  # First import
await import_csv(csv_content)  # Second import

# Expected: No duplicate users, csv_data array updated
```

## Performance Considerations

1. **Early Duplicate Check**: `statement_exists()` query before processing
   - Reduces unnecessary work
   - Can be optimized with caching if needed

2. **MERGE Statements**: Atomic operations
   - No race conditions
   - BigQuery handles concurrency

3. **User Lookups**: `find_existing_user()` called for every statement
   - Consider caching for high-volume scenarios
   - Current implementation is safe and correct

## Error Handling

- **Duplicate Check Fails**: Proceeds with processing (fail-safe)
- **MERGE Fails**: Error logged, message not acknowledged (retry)
- **User Lookup Fails**: Proceeds with new user creation (fail-safe)

## Summary

✅ **Statements**: Idempotent via early check + MERGE  
✅ **Users**: Idempotent via MERGE with email-based matching  
✅ **CSV Imports**: Idempotent via user normalization MERGE  
✅ **Cross-Source**: Automatic merging of xAPI and CSV users  
✅ **Safe Retries**: All operations can be safely retried  

