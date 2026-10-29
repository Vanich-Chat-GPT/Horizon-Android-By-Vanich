#!/usr/bin/env python3
"""Bound Android chunk streaming work and reduce candidate/result memory spikes.

The patch preserves vanilla chunk data, lighting, close-range meshes and world
simulation. It bounds only queued/in-flight background jobs and work applied
to the render thread in one update; dirty work is kept for later frames.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "crates/horizon-client/src/streaming.rs"
source = p.read_text(encoding="utf-8")


def replace(old: str, new: str, expected: int = 1) -> None:
    global source
    count = source.count(old)
    if count != expected:
        raise RuntimeError(
            f"streaming optimization anchor expected {expected} match(es), "
            f"found {count}: {old[:110]!r}"
        )
    source = source.replace(old, new, expected)


# Keep only the best candidate batch while scanning the requested square.
# The upstream implementation built and sorted every missing coordinate, then
# immediately truncated to workers*3. This keeps temporary memory O(batch) and
# preserves the same priority/x/z ordering and de-duplication semantics.
replace(
    "impl GenerationScan {\n    /// None means the scan was skipped; Some preserves the original candidate",
    """fn keep_nearest(
    wanted: &mut Vec<(i64, i32, i32)>,
    candidate: (i64, i32, i32),
    limit: usize,
) {
    if limit == 0
        || wanted
            .iter()
            .any(|item| (item.1, item.2) == (candidate.1, candidate.2))
    {
        return;
    }
    if wanted.len() < limit {
        wanted.push(candidate);
        return;
    }
    let mut worst = 0;
    for index in 1..wanted.len() {
        if wanted[index] > wanted[worst] {
            worst = index;
        }
    }
    if candidate < wanted[worst] {
        wanted[worst] = candidate;
    }
}

impl GenerationScan {
    /// None means the scan was skipped; Some preserves the original candidate""",
)

replace("            let mut wanted = Vec::new();",
        "            let candidate_limit = capacity.saturating_sub(input.generating.len());\n            let mut wanted = Vec::with_capacity(candidate_limit);")
replace(
    "                    wanted.push((input.ranges.priority(x, z, input.loading), x, z));",
    "                    keep_nearest(\n                        &mut wanted,\n                        (input.ranges.priority(x, z, input.loading), x, z),\n                        candidate_limit,\n                    );",
)
replace(
    "                        wanted.push((input.ranges.priority(x, z, input.loading), x, z));",
    "                        keep_nearest(\n                            &mut wanted,\n                            (input.ranges.priority(x, z, input.loading), x, z),\n                            candidate_limit,\n                        );",
)
replace(
    "            wanted.sort_unstable();\n            wanted.dedup();\n            wanted.truncate(capacity - input.generating.len());",
    "            wanted.sort_unstable();",
)

# A synchronous channel provides back-pressure: completed Chunk/Mesh payloads
# cannot accumulate without limit while the main/render thread is busy.
replace(
    "        let (send, results) = mpsc::channel();",
    "        let result_capacity = threads.max(1).saturating_mul(2);\n        let (send, results) = mpsc::sync_channel(result_capacity);",
)

# Process a small, predictable number of worker completions per update. Anything
# already deferred remains ordered and is drained on subsequent updates.
replace(
    "        let mut uploads = Vec::new();\n        if self.paused {",
    "        let mut uploads = Vec::new();\n        const RESULTS_PER_UPDATE: usize = 4;\n        if self.paused {",
)
replace(
    """        let deferred = std::mem::take(&mut self.deferred);
        let received = std::iter::from_fn(|| self.results.try_recv().ok());
        for done in deferred.into_iter().chain(received.collect::<Vec<_>>()) {""",
    """        let mut completed = Vec::with_capacity(RESULTS_PER_UPDATE);
        let deferred_count = self.deferred.len().min(RESULTS_PER_UPDATE);
        completed.extend(self.deferred.drain(..deferred_count));
        while completed.len() < RESULTS_PER_UPDATE {
            match self.results.try_recv() {
                Ok(done) => completed.push(done),
                Err(_) => break,
            }
        }
        for done in completed {""",
)

# Keep only a couple of chunk-finalization jobs per worker in flight. Sorting
# makes the limited slots go to nearby chunks instead of arbitrary HashMap order.
replace(
    """        // Finalize chunks whose neighbourhood is decorated.
        let candidates: Vec<(i32, i32)> = self.protos.keys().copied().collect();
        for (x, z) in candidates {""",
    """        // Finalize chunks whose neighbourhood is decorated. Limit work in
        // flight so a large view distance cannot fill the job heap with full
        // chunks and their proto allocations.
        let workers = self.threads.len().max(1);
        let stage_limit = workers.saturating_mul(2).max(1);
        let mut candidates: Vec<(i32, i32)> = self.protos.keys().copied().collect();
        candidates.sort_unstable_by_key(|&(x, z)| self.distance(x, z));
        for (x, z) in candidates {
            if self.finishing.len() >= stage_limit {
                break;
            }""",
)
replace(
    "        let workers = self.threads.len();\n        if self.decorates && self.order_area",
    "        if self.decorates && self.order_area",
)

# Lighting jobs also own nine Arc chunk snapshots. Schedule nearest dirty lights
# first and keep their in-flight set bounded; unprocessed keys stay dirty.
replace(
    """        let light: Vec<_> = world.dirty_light.iter().copied().collect();
        for (x, z) in light {""",
    """        let mut light: Vec<_> = world.dirty_light.iter().copied().collect();
        light.sort_unstable_by_key(|&(x, z)| self.distance(x, z));
        for (x, z) in light {""",
)
replace(
    """            if !world.chunks.contains_key(&(x, z)) {
                world.dirty_light.remove(&(x, z));
                continue;
            }
            let Some(region) = self.light_region(world, x, z) else {""",
    """            if !world.chunks.contains_key(&(x, z)) {
                world.dirty_light.remove(&(x, z));
                continue;
            }
            if self.lighting.len() >= stage_limit {
                break;
            }
            let Some(region) = self.light_region(world, x, z) else {""",
)

# Mesh output is large. Cap queued/in-flight section meshes and leave every
# section not scheduled in dirty_sections, so no chunk geometry is discarded.
replace(
    """        let columns: Vec<_> = world.dirty_sections.columns().collect();
        for ((x, z), sections) in columns {
            if !world.chunks.contains_key(&(x, z)) {""",
    """        let columns: Vec<_> = world.dirty_sections.columns().collect();
        let mesh_limit = stage_limit;
        for ((x, z), sections) in columns {
            if self.meshing.len() >= mesh_limit {
                break;
            }
            if !world.chunks.contains_key(&(x, z)) {""",
)
replace(
    """            world.dirty_sections.take_column(x, z);
            for sy in section_indexes(sections) {
                let first = self.meshed.insert((x, z));""",
    """            world.dirty_sections.take_column(x, z);
            for sy in section_indexes(sections) {
                if self.meshing.len() >= mesh_limit {
                    world.dirty_sections.insert((x, sy, z));
                    continue;
                }
                let first = self.meshed.insert((x, z));""",
)

p.write_text(source, encoding="utf-8")
print("Applied bounded candidate selection, back-pressure, and per-stage streaming budgets.")
