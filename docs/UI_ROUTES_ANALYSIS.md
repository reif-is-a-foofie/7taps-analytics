# UI Routes Analysis & Cleanup Plan

## Current UI Routes

### ✅ In Menu (Keep These)
1. **Analytics Dashboard** (`/`) - Main dashboard
2. **Daily Course Analytics** (`/ui/daily-analytics`) - Daily analytics
3. **Data Explorer** (`/ui/data-explorer`) - Main data explorer
4. **CSV Upload** (`/ui/csv-upload`) - CSV upload functionality
5. **Data Import** (`/ui/data-import`) - Polls & Audio import
6. **Cohort Management** (`/ui/cohort-management`) - Manage cohorts
7. **User Matching** (`/ui/user-matching`) - Match orphaned statements
8. **Flagged Content** (`/ui/safety`) - Safety/flagged content dashboard
9. **Health Check** (`/health`) - System health

### ❌ NOT in Menu (Consider Removing)
1. **BigQuery Dashboard** (`/ui/bigquery-dashboard`) - Duplicate/legacy?
2. **Statement Browser** (`/ui/statement-browser`) - Not in menu
3. **Mapping** (`/ui/mapping`) - Not in menu
4. **Data Export** (`/ui/data-export`) - Not in menu
5. **User Management** (`/ui/user-management`) - Not in menu (different from user-matching)
6. **Raw Statements** (`/ui/raw-statements`) - Not in menu
7. **Recent PubSub** (`/ui/recent-pubsub`) - Not in menu
8. **ETL Dashboard** (`/ui/etl-dashboard`) - Referenced but not in main menu
9. **Daily Progress** (`/ui/daily-progress`) - Not in main menu
10. **Admin Panel** (`/ui/admin`) - Referenced but may not exist

### 🔍 Routes to Investigate
- `/ui/dashboard` vs `/` - Are these duplicates?
- `/ui/flagged-content` vs `/ui/safety` - Both exist, which one to use?

## Recommendations

### Keep (Core Functionality)
- `/` - Main dashboard
- `/ui/daily-analytics` - Daily analytics
- `/ui/data-explorer` - Data explorer
- `/ui/csv-upload` - CSV upload
- `/ui/data-import` - Data import
- `/ui/cohort-management` - Cohort management
- `/ui/user-matching` - User matching
- `/ui/safety` - Flagged content

### Remove (Not Used/Redundant)
- `/ui/bigquery-dashboard` - Use data-explorer instead
- `/ui/statement-browser` - Not in menu, functionality may be in data-explorer
- `/ui/mapping` - Not in menu
- `/ui/data-export` - Not in menu
- `/ui/user-management` - Different from user-matching, not in menu
- `/ui/raw-statements` - Not in menu
- `/ui/recent-pubsub` - Not in menu
- `/ui/etl-dashboard` - Not in main menu
- `/ui/daily-progress` - Not in main menu
- `/ui/admin` - Check if exists, remove if not

### Consolidate
- `/ui/dashboard` → Merge with `/` if duplicate
- `/ui/flagged-content` → Redirect to `/ui/safety` (already done)

