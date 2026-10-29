#!/usr/bin/env python3
"""Reduce temporary allocations in the Android chunk scheduler.

Keep upstream worker/channel behavior unchanged: no artificial queue, chunk,
RAM, or per-frame result caps. Reserve the expected candidate batch once to
avoid repeated Vec growth during streaming updates.
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
# Saturating subtraction avoids usize underflow if the in-flight set is larger
# than the target capacity; it does not impose a queue or result limit.
replace("            let mut wanted = Vec::new();",
        "            let mut wanted = Vec::with_capacity(capacity.saturating_sub(input.generating.len()));")
p.write_text(s,encoding="utf-8")
print("Preserved original streaming, chunk, and lighting scheduling; reduced temporary candidate-vector reallocations without changing visual settings.")
