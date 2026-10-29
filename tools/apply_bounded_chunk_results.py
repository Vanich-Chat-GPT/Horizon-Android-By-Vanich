#!/usr/bin/env python3
"""Reduce chunk-streaming memory spikes and configure Android-friendly far terrain.

The renderer still builds exact full-detail near chunks. Only the independent
far-terrain LOD may use coarser tiles; actual chunks, lighting and game logic
are preserved. Queues are bounded by in-flight stage budgets, not by dropping
world data or clipping generated results.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()


def patch_file(relative: str, transform) -> None:
    path = root / relative
    source = path.read_text(encoding="utf-8")
    updated = transform(source)
    path.write_text(updated, encoding="utf-8")


def replace(source: str, old: str, new: str, expected: int = 1) -> str:
    count = source.count(old)
    if count != expected:
        raise RuntimeError(
            f"streaming optimization anchor expected {expected} match(es), "
            f"found {count}: {old[:110]!r}"
        )
    return source.replace(old, new, expected)


def patch_streaming(source: str) -> str:
    # Keep only the closest batch while scanning the requested square. Upstream
    # collected, sorted and truncated every missing coordinate each time it
    # scanned, making a temporary O(view-distance squared) vector.
    source = replace(
        source,
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
    source = replace(
        source,
        "            let mut wanted = Vec::new();",
        "            let candidate_limit = capacity.saturating_sub(input.generating.len());\n"
        "            let mut wanted = Vec::with_capacity(candidate_limit);",
    )
    push_pattern = re.compile(
        r"(?m)^(?P<indent>[ ]*)wanted\.push\(\(input\.ranges\.priority\(x, z, input\.loading\), x, z\)\);$"
    )
    source, count = push_pattern.subn(
        lambda m: (
            f"{m.group('indent')}keep_nearest(\n"
            f"{m.group('indent')}    &mut wanted,\n"
            f"{m.group('indent')}    (input.ranges.priority(x, z, input.loading), x, z),\n"
            f"{m.group('indent')}    candidate_limit,\n"
            f"{m.group('indent')});"
        ),
        source,
    )
    if count != 2:
        raise RuntimeError(
            f"expected 2 candidate pushes in streaming.rs, found {count}"
        )
    source = replace(
        source,
        "            wanted.sort_unstable();\n"
        "            wanted.dedup();\n"
        "            wanted.truncate(capacity - input.generating.len());",
        "            wanted.sort_unstable();",
    )

    # Keep result messages in the existing channel but apply a small batch per
    # update. In-flight stages below are bounded, so payload accumulation stays
    # proportional to worker count without making worker shutdown deadlock.
    source = replace(
        source,
        "        let mut uploads = Vec::new();\n        if self.paused {",
        "        let mut uploads = Vec::new();\n"
        "        const RESULTS_PER_UPDATE: usize = 4;\n"
        "        if self.paused {",
    )
    source = replace(
        source,
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

    # Bound full proto->chunk conversions, sorted so the nearest chunks progress
    # first instead of depending on hash-map iteration order.
    source = replace(
        source,
        """        // Finalize chunks whose neighbourhood is decorated.
        let candidates: Vec<(i32, i32)> = self.protos.keys().copied().collect();
        for (x, z) in candidates {""",
        """        // Finalize chunks whose neighbourhood is decorated. Bound outstanding
        // conversions so completed full chunks cannot pile up in the job heap.
        let workers = self.threads.len().max(1);
        let stage_limit = workers.saturating_mul(2).max(1);
        let mut candidates: Vec<(i32, i32)> = self.protos.keys().copied().collect();
        candidates.sort_unstable_by_key(|&(x, z)| self.distance(x, z));
        for (x, z) in candidates {
            if self.finishing.len() >= stage_limit {
                break;
            }""",
    )
    source = replace(
        source,
        "        let workers = self.threads.len();\n        if self.decorates && self.order_area",
        "        if self.decorates && self.order_area",
    )

    # Lighting snapshots retain a 3x3 chunk region. Schedule nearby lights
    # first and leave all unscheduled coordinates dirty for the next update.
    source = replace(
        source,
        """        let light: Vec<_> = world.dirty_light.iter().copied().collect();
        for (x, z) in light {""",
        """        let mut light: Vec<_> = world.dirty_light.iter().copied().collect();
        light.sort_unstable_by_key(|&(x, z)| self.distance(x, z));
        for (x, z) in light {""",
    )
    source = replace(
        source,
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

    # Mesh snapshots and output payloads can be large. If the budget is reached,
    # preserve the remaining sections in dirty_sections instead of discarding them.
    source = replace(
        source,
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
    source = replace(
        source,
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
    return source


def patch_graphics(source: str) -> str:
    # Migrate existing Android profiles once. Use the engine's supported LOD
    # mode, keeping the resident/near chunks at full detail, and leave users'
    # settings untouched after the migration marker exists.
    source = replace(
        source,
        """        let mut g: Self = fs::read_to_string(dir.join(FILE))
            .map(|t| Self::parse(&t))
            .unwrap_or_default();
        if fs::remove_file(dir.join(HDR_MARKER)).is_ok() && g.hdr {""",
        """        let mut g: Self = fs::read_to_string(dir.join(FILE))
            .map(|t| Self::parse(&t))
            .unwrap_or_default();
        #[cfg(target_os = "android")]
        {
            let marker = dir.join(".horizon-android-performance-v1");
            if !marker.exists() {
                g.far_detail = FarDetail::Reduced;
                if g.lod_distance == 0 {
                    g.lod_distance = 32;
                }
                if g.workers == 0 {
                    // Leave a CPU core for the renderer/server where possible.
                    // Three workers are enough to overlap chunk work without
                    // overcommitting memory bandwidth on a low-RAM mobile SoC.
                    g.workers = std::thread::available_parallelism()\n                        .map_or(2, |n| n.get().saturating_sub(2).clamp(1, 3)) as u32;
                }
                if fs::create_dir_all(dir).is_ok()
                    && fs::write(dir.join(FILE), g.serialize()).is_ok()
                {
                    let _ = fs::write(marker, b"1\\n");
                }
            }
        }
        if fs::remove_file(dir.join(HDR_MARKER)).is_ok() && g.hdr {""",
    )
    return source



def patch_settings(source: str) -> str:
    # One-time migration on Android only. Fewer fully resident chunks lower
    # chunk/mesh memory and simulation load; far LOD supplies a cheaper horizon.
    # Existing values that are already lower are preserved.
    source = replace(
        source,
        """        let settings = match fs::read(path) {
            Ok(bytes) => Self {
                horizon,
                controller,
                touch,
                keypad,
                extras,
                mods,
                ..Self::parse(&String::from_utf8_lossy(&bytes))
            },
            Err(_) => Self {
                horizon,
                controller,
                touch,
                keypad,
                extras,
                mods,
                ..Self::default()
            },
        };
        settings.describe_for_crashes();
        settings""",
        """        let mut settings = match fs::read(path) {
            Ok(bytes) => Self {
                horizon,
                controller,
                touch,
                keypad,
                extras,
                mods,
                ..Self::parse(&String::from_utf8_lossy(&bytes))
            },
            Err(_) => Self {
                horizon,
                controller,
                touch,
                keypad,
                extras,
                mods,
                ..Self::default()
            },
        };
        #[cfg(target_os = "android")]
        if let Some(dir) = path.parent() {
            let marker = dir.join(".horizon-android-game-options-v1");
            if !marker.exists() {
                settings.render_distance = settings.render_distance.min(8);
                settings.simulation_distance = settings.simulation_distance.min(6);
                settings.save(path);
                if fs::read(path).is_ok() {
                    let _ = fs::write(marker, b"1\\n");
                }
            }
        }
        settings.describe_for_crashes();
        settings""",
    )
    return source

patch_file("crates/horizon-client/src/streaming.rs", patch_streaming)
patch_file("crates/horizon-client/src/graphics.rs", patch_graphics)
patch_file("crates/horizon-client/src/settings.rs", patch_settings)
print("Applied bounded chunk streaming, Android reduced far LOD defaults, and a three-worker Android default.")
