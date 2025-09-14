#!/usr/bin/env python3
"""
Contracts Watcher - Live terminal feed for contract assignments and progress.

Features:
- Streams updates when contracts change (status, current_agent, heartbeats)
- Highlights unclaimed/pending contracts
- Periodic summary of active work

Usage:
  python3 scripts/watch_contracts.py            # Live feed of changes
  python3 scripts/watch_contracts.py --refresh  # Full dashboard refresh every N seconds
  python3 scripts/watch_contracts.py --interval 2
"""

import os
import sys
import json
import time
import glob
import argparse
from datetime import datetime
from typing import Dict, Any, Tuple

CONTRACT_GLOB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'project_management', 'contracts', '*.json'
)

def load_contracts() -> Dict[str, Dict[str, Any]]:
    data = {}
    for path in glob.glob(CONTRACT_GLOB):
        try:
            with open(path, 'r') as f:
                c = json.load(f)
            # Derive id from filename
            cid = os.path.splitext(os.path.basename(path))[0]
            c['__path'] = path
            c['__id'] = cid
            data[cid] = c
        except Exception as e:
            # Skip malformed files but surface a note in the feed
            data[os.path.basename(path)] = {
                '__path': path,
                '__id': os.path.basename(path),
                'module': os.path.basename(path),
                'status': f'malformed_json: {e}'
            }
    return data

def summarize_contract(c: Dict[str, Any]) -> Tuple[str, str]:
    mod = c.get('module', c.get('__id'))
    agent = c.get('agent', 'unassigned')
    status = c.get('status', 'unknown')
    current_agent = c.get('current_agent', None)
    last_hb = c.get('last_heartbeat', None)
    hb_count = len(c.get('heartbeats', [])) if isinstance(c.get('heartbeats'), list) else 0
    progress = c.get('task_tracking', {}).get('progress_percentage') or c.get('progress_percentage')
    deps = c.get('task_tracking', {}).get('dependencies', [])

    headline = f"{mod} | agent={agent} status={status}"
    details = (
        f"current={current_agent or '-'} hb={hb_count} last_hb={last_hb or '-'} "
        f"progress={progress if progress is not None else '-'} deps={','.join(deps) if deps else '-'}"
    )
    return headline, details

def print_dashboard(contracts: Dict[str, Dict[str, Any]]):
    os.system('clear')
    now = datetime.utcnow().isoformat()
    print(f"Contracts Dashboard @ {now}\n")

    # Unclaimed pending work
    unclaimed = [c for c in contracts.values()
                 if c.get('status') in ('pending', 'planning') and not c.get('current_agent')]
    active = [c for c in contracts.values() if c.get('current_agent')]

    print("Unclaimed (pending/planning):")
    if not unclaimed:
        print("  - none")
    for c in sorted(unclaimed, key=lambda x: x.get('module', x.get('__id'))):
        h, d = summarize_contract(c)
        print(f"  - {h}")
        print(f"    {d}")

    print("\nActive (in progress):")
    if not active:
        print("  - none")
    for c in sorted(active, key=lambda x: x.get('last_heartbeat', '')):
        h, d = summarize_contract(c)
        print(f"  - {h}")
        print(f"    {d}")

def diff_and_print_feed(prev: Dict[str, Dict[str, Any]], curr: Dict[str, Dict[str, Any]]):
    # Detect new, removed, and changed
    prev_keys = set(prev.keys())
    curr_keys = set(curr.keys())
    now = datetime.utcnow().isoformat()

    for added in sorted(curr_keys - prev_keys):
        c = curr[added]
        h, d = summarize_contract(c)
        print(f"[{now}] NEW: {h}")
        print(f"         {d}")

    for removed in sorted(prev_keys - curr_keys):
        print(f"[{now}] REMOVED: {removed}")

    for k in sorted(prev_keys & curr_keys):
        p = prev[k]
        c = curr[k]
        # Compare interesting fields
        fields = ['status', 'current_agent', 'last_heartbeat']
        changes = []
        for f in fields:
            if p.get(f) != c.get(f):
                changes.append((f, p.get(f), c.get(f)))

        # Heartbeat increment
        p_hb = len(p.get('heartbeats', []) or [])
        c_hb = len(c.get('heartbeats', []) or [])
        if c_hb > p_hb:
            changes.append(('heartbeat', p_hb, c_hb))

        if changes:
            h, d = summarize_contract(c)
            print(f"[{now}] UPDATE: {h}")
            for f, old, new in changes:
                print(f"         {f}: {old} -> {new}")
            print(f"         {d}")

def main():
    ap = argparse.ArgumentParser(description='Watch and stream contract updates')
    ap.add_argument('--interval', type=float, default=3.0, help='Poll interval seconds')
    ap.add_argument('--refresh', action='store_true', help='Show full dashboard every interval')
    args = ap.parse_args()

    last_snapshot = {}
    last_mtimes: Dict[str, float] = {}

    try:
        if args.refresh:
            while True:
                curr = load_contracts()
                print_dashboard(curr)
                last_snapshot = curr
                time.sleep(args.interval)
        else:
            # Feed mode: on changes, print delta lines
            print("Starting contracts feed. Watching for changes...\n")
            # Initial snapshot
            last_snapshot = load_contracts()
            for c in last_snapshot.values():
                try:
                    last_mtimes[c['__path']] = os.path.getmtime(c['__path'])
                except Exception:
                    pass
            # Print initial summary of unclaimed
            print_dashboard(last_snapshot)
            print("\n--- Live updates ---\n")

            while True:
                time.sleep(args.interval)
                curr = load_contracts()
                # Build mtimes map
                curr_mtimes: Dict[str, float] = {}
                for c in curr.values():
                    try:
                        curr_mtimes[c['__path']] = os.path.getmtime(c['__path'])
                    except Exception:
                        pass

                # If anything changed, print diff feed
                if curr.keys() != last_snapshot.keys() or any(
                    curr_mtimes.get(p, 0) != last_mtimes.get(p, 0)
                    for p in set(list(curr_mtimes.keys()) + list(last_mtimes.keys()))
                ):
                    diff_and_print_feed(last_snapshot, curr)
                    last_snapshot = curr
                    last_mtimes = curr_mtimes
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == '__main__':
    main()

