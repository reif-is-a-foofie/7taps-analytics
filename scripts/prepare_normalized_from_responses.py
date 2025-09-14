#!/usr/bin/env python3
"""
Prepare normalized CSVs from raw Responses lesson files for easy import.

It scans a source directory (e.g., ../Responses) for lesson CSVs whose
filenames begin with a lesson number, reads each "Card ..." column, and
emits a normalized CSV with columns:
  Learner,Card,Card type,Lesson Number,Global Q#,PDF Page #,Response

Usage:
  python scripts/prepare_normalized_from_responses.py \
    --source ../Responses \
    --out imports/normalized \
    --combine imports/normalized/all_lessons.csv

Notes:
- Global Q# is inferred: preferred = parsed card number; fallback = running index.
- PDF Page # is left blank unless you have a mapping (can be extended here).
"""

import argparse
import os
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd


CARD_COL_RE = re.compile(r"^Card\s+\d+\s*\(([^)]+)\):\s*(.*)$")
LESSON_NUMBER_RE = re.compile(r"^(\d+)")


def parse_lesson_number_from_filename(filename: str) -> Optional[int]:
    m = LESSON_NUMBER_RE.match(Path(filename).name)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def extract_card_meta_from_header(header: str):
    """Return (card_type, question_text, card_number) if parsable."""
    # Try to pull number directly too
    num = None
    try:
        if "Card " in header:
            after = header.split("Card ", 1)[1]
            num_str = after.split(" ", 1)[0].strip()
            if num_str.isdigit():
                num = int(num_str)
    except Exception:
        pass

    m = CARD_COL_RE.match(header)
    if not m:
        # Not a standard card header; return unknowns but keep header as question text
        return None, header.strip(), num
    card_type = m.group(1).strip()
    question_text = m.group(2).strip() or header.strip()
    return card_type, question_text, num


def process_lesson_csv(path: Path) -> pd.DataFrame:
    lesson_number = parse_lesson_number_from_filename(path.name) or 0
    df = pd.read_csv(path, dtype=str)
    df = df.fillna("")

    # Identify card columns
    card_columns: List[str] = [c for c in df.columns if c.strip().lower().startswith("card ")]
    if "Learner" not in df.columns:
        raise ValueError(f"Missing 'Learner' column in {path}")

    rows = []
    # Running index fallback for Global Q# if not parseable from header
    running_index = 0

    for _, r in df.iterrows():
        learner = str(r["Learner"]).strip()
        for col in card_columns:
            value = str(r[col]).strip()
            if not value:
                continue
            card_type, question_text, card_num = extract_card_meta_from_header(col)
            running_index += 1
            global_q = card_num if card_num is not None else running_index
            rows.append(
                {
                    "Learner": learner,
                    "Card": col,
                    "Card type": card_type or "Unknown",
                    "Lesson Number": lesson_number,
                    "Global Q#": global_q,
                    "PDF Page #": "",
                    "Response": value,
                }
            )

    return pd.DataFrame(rows, columns=[
        "Learner",
        "Card",
        "Card type",
        "Lesson Number",
        "Global Q#",
        "PDF Page #",
        "Response",
    ])


def main():
    ap = argparse.ArgumentParser(description="Prepare normalized CSVs from Responses")
    ap.add_argument("--source", required=True, help="Path to Responses directory")
    ap.add_argument("--out", required=True, help="Output directory for normalized CSVs")
    ap.add_argument("--combine", default="", help="Optional combined CSV output path")
    args = ap.parse_args()

    src = Path(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    lesson_files = sorted([p for p in src.glob("*.csv") if parse_lesson_number_from_filename(p.name)])
    combined_frames: List[pd.DataFrame] = []

    for lf in lesson_files:
        print(f"→ Normalizing {lf.name}")
        try:
            frame = process_lesson_csv(lf)
            if frame.empty:
                print(f"  (no responses found)")
                continue
            combined_frames.append(frame)
            out_path = out_dir / f"lesson_{parse_lesson_number_from_filename(lf.name)}.csv"
            frame.to_csv(out_path, index=False)
            print(f"  saved: {out_path}")
        except Exception as e:
            print(f"  error: {e}")

    if args.combine and combined_frames:
        combined = pd.concat(combined_frames, ignore_index=True)
        comb_path = Path(args.combine)
        comb_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(comb_path, index=False)
        print(f"✓ combined: {comb_path} ({len(combined)} rows)")


if __name__ == "__main__":
    main()

