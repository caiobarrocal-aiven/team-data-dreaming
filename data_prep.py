"""
data_prep.py — Aiven Data Signal
Processes service creation CSV → events.json

Each row is a real service creation event:
  as_of          — timestamp of creation
  service_type   — pg, kafka, mysql, opensearch, valkey, clickhouse, ...
  node_counter   — number of nodes provisioned (intensity driver)

Events are sorted chronologically and replayed with timing
compressed to a ~90-second loop at ~10–25 events/sec.
"""

import csv
import json
import math
from pathlib import Path
from collections import Counter
from datetime import datetime

INPUT_CSV   = Path("/sessions/clever-inspiring-franklin/mnt/uploads/bquxjob_89346bf_19d908b5090.csv")
OUTPUT_JSON = Path(__file__).parent / "events.json"

# ── Node count → volume tier ──────────────────────────────────────────────────

def node_to_tier(n):
    if n <= 1:  return "single"
    if n <= 2:  return "low"
    if n <= 4:  return "medium"
    if n <= 8:  return "high"
    return "massive"

def node_to_weight(n):
    """Log-scale 0–1 weight from node count."""
    return round(min(1.0, math.log1p(n) / math.log1p(20)), 3)

# ── Load and sort by timestamp ────────────────────────────────────────────────

print(f"[data_prep] Reading {INPUT_CSV.name} ...")

rows = []
with open(INPUT_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts    = row["as_of"]
        stype = row["service_type"].strip().lower()
        nodes = int(row["node_counter"] or 1)
        rows.append((ts, stype, nodes))

rows.sort(key=lambda r: r[0])  # chronological order

print(f"[data_prep] {len(rows):,} events spanning {rows[0][0][:10]} → {rows[-1][0][:10]}")

# ── Service type stats ────────────────────────────────────────────────────────

type_counts = Counter(r[1] for r in rows)
print("\n[data_prep] Service type breakdown:")
total_rows = len(rows)
for stype, count in type_counts.most_common():
    print(f"  {count:>6,}  {count/total_rows*100:5.1f}%  {stype}")

# ── Compute replay delays ─────────────────────────────────────────────────────
# Compress the full 14-day span to a 90-second loop.
# Floor at 40ms (25 ev/sec max), cap at 5000ms to suppress long idle gaps.

LOOP_SECONDS = 90.0
MIN_DELAY_MS = 40
MAX_DELAY_MS = 5000

def parse_ts(s):
    s = s.replace(" UTC", "").strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f").timestamp()
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()

ts_seconds = [parse_ts(r[0]) for r in rows]
span  = ts_seconds[-1] - ts_seconds[0]
scale = LOOP_SECONDS / span

# ── Build events ──────────────────────────────────────────────────────────────

events = []
for i, (ts, stype, nodes) in enumerate(rows):
    if i < len(rows) - 1:
        real_delta = ts_seconds[i + 1] - ts_seconds[i]
        delay_ms   = int(max(MIN_DELAY_MS, min(MAX_DELAY_MS, real_delta * scale * 1000)))
    else:
        delay_ms = MIN_DELAY_MS

    events.append({
        "service_type": stype,
        "nodes":        nodes,
        "volume_tier":  node_to_tier(nodes),
        "weight":       node_to_weight(nodes),
        "is_error":     False,
        "delay_ms":     delay_ms,
    })

# ── Write ─────────────────────────────────────────────────────────────────────

with open(OUTPUT_JSON, "w") as f:
    json.dump(events, f, separators=(",", ":"))

size_kb = OUTPUT_JSON.stat().st_size / 1024
print(f"\n[data_prep] Wrote {len(events):,} events → {OUTPUT_JSON.name} ({size_kb:.0f} KB)")
print(f"[data_prep] Replay loop: ~{LOOP_SECONDS}s, delay range: {MIN_DELAY_MS}–{MAX_DELAY_MS}ms")
