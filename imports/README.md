Imports Folder

Use this directory to stage normalized CSVs for idempotent import.

Quick start
- Prepare from your Responses folder:
  - `python scripts/prepare_normalized_from_responses.py --source ../Responses --out imports/normalized --combine imports/normalized/all_lessons.csv`
- Import a single normalized CSV:
  - `python scripts/import_manual.py --file imports/normalized/all_lessons.csv`
- Or via API (running uvicorn):
  - `curl -F "csv_file=@imports/normalized/all_lessons.csv" http://localhost:8000/api/import/focus-group-csv`

Input assumptions (raw Responses CSV)
- Filenames begin with a lesson number, e.g., `1 You_re Here Start Strong.csv`.
- Columns include `Learner` and multiple `Card ...` columns like `Card 12 (Poll): ...`.

The converter outputs normalized rows with columns:
- Learner, Card, Card type, Lesson Number, Global Q#, PDF Page #, Response

Idempotency
- The importer uses a deterministic key and an existence check so re‑running imports, or overlapping with xAPI, will not duplicate records.

Dry‑run and reports
- CLI supports `--dry-run` to preview what would be imported without writing.
- Add `--report report.json` to save details: matches (duplicates found) and would_import (new records).
