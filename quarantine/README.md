# Quarantine Directory

This directory contains files that are either:
- Redundant/duplicate content
- Development artifacts that shouldn't be tracked
- Outdated analysis files
- Empty directories

## Contents

### `redundant_requirements/`
- **Reason**: Duplicate content from `orchestrator_contracts/` 
- **Action**: Keep `orchestrator_contracts/` as the canonical source
- **Files**: All JSON files from `requirements/` directory

### `empty_keys/`
- **Reason**: Empty directory with no purpose
- **Action**: Remove if no longer needed
- **Files**: Empty `keys/` directory

### `development_artifacts/`
- **Reason**: Should be in `.gitignore`, not tracked
- **Action**: Add to `.gitignore` and remove from tracking
- **Files**: `.pytest_cache/`, `venv/`

### `redundant_reports/`
- **Reason**: Multiple similar analysis files, keep only the most recent/complete
- **Action**: Review and keep only essential reports
- **Files**: Various field mapping and analysis JSON files

## Cleanup Actions Needed

1. Add to `.gitignore`:
   ```
   .pytest_cache/
   venv/
   ```

2. Remove empty directories:
   ```
   keys/
   ```

3. Consolidate duplicate content:
   - Keep `orchestrator_contracts/` as canonical
   - Remove `requirements/` directory

4. Review and clean up redundant reports
