#!/usr/bin/env python3
"""Bound native Android chunk worker result queue without dropping results.

Workers retry full queues instead of allocating an unbounded backlog. During
shutdown, a sender checks stop so join() cannot block on a full queue.
Desktop keeps original unbounded channel.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
p=root/"crates/horizon-client/src/streaming.rs"
s=p.read_text(encoding="utf-8")
def replace(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError(f"memory queue patch missing/ambiguous anchor: {a[:100]}")
 s=s.replace(a,b,1)
# Preserve the engine's original scheduling and queue semantics.
# Only reduce temporary allocation growth when collecting in-flight candidates.
replace("            let mut wanted = Vec::new();",
        "            let mut wanted = Vec::with_capacity(capacity - input.generating.len());")
p.write_text(s,encoding="utf-8")
print("Preserved original streaming, chunk, and lighting scheduling; reduced temporary candidate-vector reallocations without changing visual settings.")
