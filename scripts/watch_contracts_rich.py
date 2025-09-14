#!/usr/bin/env python3
"""
Rich Contracts Dashboard - color HUD for contract assignments and progress.

Legend:
  🟢 READY      -> deps satisfied, can start now
  🔵 ACTIVE     -> running right now (current_agent set or status in_progress)
  🟡 WAITING    -> pending/planning but blocked by deps
  ⚪ PLANNING   -> defined, not yet queued
  🔴 BLOCKED    -> error/failed

Usage:
  python3 scripts/watch_contracts_rich.py --interval 2      # refresh dashboard
  python3 scripts/watch_contracts_rich.py --once            # single render
"""

import os
import sys
import glob
import json
import time
import argparse
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

CONTRACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'project_management', 'contracts')

def load_contracts() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in glob.glob(os.path.join(CONTRACT_DIR, '*.json')):
        try:
            with open(path) as f:
                c = json.load(f)
            cid = os.path.splitext(os.path.basename(path))[0]
            c['__id'] = cid
            c['__path'] = path
            out[cid] = c
        except Exception:
            continue
    return out

def module_code(mod: str) -> str:
    # Return the prefix like gc11 or ref06 from module value
    if not mod:
        return ''
    return mod.split('_')[0]

def find_contract_by_code(contracts: Dict[str, Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    for c in contracts.values():
        m = c.get('module') or c.get('__id')
        if m and m.startswith(code):
            return c
    return None

def dep_satisfied(contracts: Dict[str, Dict[str, Any]], dep_code: str) -> bool:
    c = find_contract_by_code(contracts, dep_code)
    if c is None:
        # Unknown dep (archived/external) -> assume satisfied
        return True
    status = (c.get('status') or '').lower()
    return status in ('completed', 'complete', 'deployed', 'awaiting_verification')

def deps_satisfied(contracts: Dict[str, Dict[str, Any]], c: Dict[str, Any]) -> bool:
    deps = c.get('task_tracking', {}).get('dependencies', []) or []
    return all(dep_satisfied(contracts, d) for d in deps)

def is_active(c: Dict[str, Any]) -> bool:
    status = (c.get('status') or '').lower()
    return bool(c.get('current_agent')) or status == 'in_progress'

def is_blocked(c: Dict[str, Any]) -> bool:
    status = (c.get('status') or '').lower()
    return status in ('error', 'failed', 'blocked')

def status_bucket(contracts: Dict[str, Dict[str, Any]], c: Dict[str, Any]) -> str:
    status = (c.get('status') or '').lower()
    if is_blocked(c):
        return 'blocked'
    if is_active(c):
        return 'active'
    if status in ('pending', 'planning'):
        return 'ready' if deps_satisfied(contracts, c) else 'waiting'
    return status or 'unknown'

def status_color(bucket: str) -> str:
    return {
        'ready': 'green',
        'active': 'blue',
        'waiting': 'yellow',
        'planning': 'white',
        'blocked': 'red',
        'pending': 'cyan',
    }.get(bucket, 'white')

def compute_unlocks(contracts: Dict[str, Dict[str, Any]], c: Dict[str, Any]) -> List[str]:
    code = module_code(c.get('module') or c.get('__id'))
    unlocks: List[str] = []
    if not code:
        return unlocks
    for other in contracts.values():
        deps = other.get('task_tracking', {}).get('dependencies', []) or []
        if code in deps:
            unlocks.append(other.get('module') or other.get('__id'))
    return sorted(unlocks)

def pick_next_task(contracts: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ready = [c for c in contracts.values() if status_bucket(contracts, c) == 'ready']
    if not ready:
        return None
    scored = []
    for c in ready:
        unlocks = compute_unlocks(contracts, c)
        score = len(unlocks)
        scored.append((score, unlocks, c))
    scored.sort(key=lambda x: (-x[0], (x[2].get('module') or x[2].get('__id'))))
    return {
        'contract': scored[0][2],
        'unlocks': scored[0][1],
        'score': scored[0][0],
    }

def render(contracts: Dict[str, Dict[str, Any]]):
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.align import Align
        from rich.rule import Rule
    except Exception:
        print("rich not installed. Install with: pip install rich")
        # Plain fallback
        print("Contracts (plain):")
        for c in contracts.values():
            b = status_bucket(contracts, c)
            deps = c.get('task_tracking', {}).get('dependencies', []) or []
            print(f"- {c.get('module') or c.get('__id')} | agent={c.get('agent')} bucket={b} deps={','.join(deps) if deps else '-'}")
        return

    console = Console()
    console.clear()
    now = datetime.utcnow().isoformat()
    console.print(f"Contracts Dashboard [dim]@ {now}[/]\n")

    # NEXT MOVE
    pick = pick_next_task(contracts)
    if pick:
        c = pick['contract']
        agent = c.get('agent', 'unassigned')
        cid = c.get('module') or c.get('__id')
        unlocks = pick['unlocks']
        panel = Panel.fit(
            f"[bold green]{agent}[/bold green] → [green]{cid}[/green]\n"
            f"Unlocks: {', '.join(unlocks) if unlocks else '-'}",
            title="NEXT MOVE", border_style="green"
        )
        console.print(panel)
    else:
        console.print(Panel.fit("No READY contracts — resolve dependencies or mark prerequisites.", title="NEXT MOVE", border_style="yellow"))

    console.print(Rule())

    # Buckets to show in order
    order = [('ready', '🟢 READY'), ('active', '🔵 ACTIVE'), ('waiting', '🟡 WAITING'), ('planning', '⚪ PLANNING'), ('blocked', '🔴 BLOCKED')]

    for bucket, label in order:
        items = [c for c in contracts.values() if status_bucket(contracts, c) == bucket]
        table = Table(title=label, title_style=f"bold {status_color(bucket)}")
        table.add_column("Contract")
        table.add_column("Agent")
        table.add_column("Deps")
        table.add_column("Current")
        table.add_column("HB")
        for c in sorted(items, key=lambda x: (x.get('module') or x.get('__id'))):
            deps = c.get('task_tracking', {}).get('dependencies', []) or []
            hb = len(c.get('heartbeats', []) or [])
            table.add_row(
                f"[{status_color(bucket)}]{c.get('module') or c.get('__id')}[/]",
                c.get('agent', 'unassigned'),
                ", ".join(deps) if deps else "-",
                c.get('current_agent') or '-',
                str(hb)
            )
        console.print(table)

def main():
    ap = argparse.ArgumentParser(description='Rich Contracts Dashboard')
    ap.add_argument('--interval', type=float, default=3.0, help='Refresh interval (seconds)')
    ap.add_argument('--once', action='store_true', help='Render once and exit')
    args = ap.parse_args()

    if args.once:
        contracts = load_contracts()
        render(contracts)
        return

    try:
        while True:
            contracts = load_contracts()
            render(contracts)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == '__main__':
    main()

