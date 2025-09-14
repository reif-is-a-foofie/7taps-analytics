#!/usr/bin/env python3
"""
Import manual focus-group CSV data into the database (idempotent).

Usage:
  python scripts/import_manual.py --file path/to/normalized_focus_group.csv [--dry-run] [--report report.json]

CSV format (columns):
  Learner,Card,Card type,Lesson Number,Global Q#,PDF Page #,Response

This CLI converts each row into an xAPI statement with a deterministic ID
and runs it through the DataNormalizer pipeline, skipping duplicates that
already exist (same actor_id, activity_id, and response).
"""

import argparse
import asyncio
import os

from app.importers.manual_importer import import_focus_group_csv_text


def main():
    parser = argparse.ArgumentParser(description="Import manual focus-group CSV data (idempotent)")
    parser.add_argument("--file", required=True, help="Path to CSV file in normalized format")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB; show what would be imported")
    parser.add_argument("--report", default="", help="Optional JSON report path for matches/would-import")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        raise SystemExit(f"CSV file not found: {args.file}")

    with open(args.file, "r", encoding="utf-8") as f:
        csv_text = f.read()

    summary = asyncio.run(import_focus_group_csv_text(csv_text, dry_run=args.dry_run))
    print("Import complete:")
    print(f"  imported: {summary.get('imported', 0)}")
    print(f"  skipped:  {summary.get('skipped', 0)}")
    if summary.get("errors"):
        print("  errors:")
        for e in summary["errors"]:
            print(f"   - {e}")
    if args.dry_run:
        print("  (dry-run) no changes were written")
    if args.report:
        import json
        with open(args.report, "w", encoding="utf-8") as rf:
            json.dump({
                "imported": summary.get("imported", 0),
                "skipped": summary.get("skipped", 0),
                "errors": summary.get("errors", []),
                "matches": summary.get("matches", []),
                "would_import": summary.get("would_import", []),
                "dry_run": summary.get("dry_run", False),
            }, rf, ensure_ascii=False, indent=2)
        print(f"  report: {args.report}")


if __name__ == "__main__":
    main()
