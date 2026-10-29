#!/usr/bin/env python3
"""Reduce chunk scheduling allocations and configure Android-friendly far terrain.

Near chunks retain full detail. The supported far-terrain LOD uses coarser tiles,
and Android defaults use fewer resident chunks. No generated chunks, queued jobs,
lighting data, or completed results are arbitrarily discarded or capped.
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

    # Drain results directly from the queue without collecting them into a
    # second temporary Vec. Preserve all ready results and their ordering.
    source = replace(
        source,
        """        let deferred = std::mem::take(&mut self.deferred);
        let received = std::iter::from_fn(|| self.results.try_recv().ok());
        for done in deferred.into_iter().chain(received.collect::<Vec<_>>()) {""",
        """        let deferred = std::mem::take(&mut self.deferred);
        let mut deferred = deferred.into_iter();
        loop {
            let done = if let Some(done) = deferred.next() {
                done
            } else {
                match self.results.try_recv() {
                    Ok(done) => done,
                    Err(_) => break,
                }
            };""",
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
                // Skip entities hidden by opaque terrain; this changes draw work, not visibility.
                g.entity_culling = true;
                g.lod_distance = if g.lod_distance == 0 {
                    32
                } else {
                    g.lod_distance.min(32)
                };
                // Keep the render/server threads responsive on low-RAM mobile SoCs.
                let auto_workers = std::thread::available_parallelism()
                    .map_or(2, |n| n.get().saturating_sub(2).clamp(1, 3)) as u32;
                g.workers = if g.workers == 0 {
                    auto_workers
                } else {
                    g.workers.clamp(1, 3)
                };
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
                // Match the tablet's 90 Hz display ceiling without disabling VSync.
                settings.max_fps = settings.max_fps.min(90);
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

def patch_lod(source: str) -> str:
    # Distant chunk summaries include 256 material columns plus reduced mip
    # levels. Keep less of this optional cache on 4GB Android devices; desktop
    # retains the upstream 1024-entry cache and all active LOD tiles stay intact.
    return replace(
        source,
        "const CELLS: usize = 16;\nconst MAX_SAVED: usize = 1024;",
        """const CELLS: usize = 16;
#[cfg(target_os = "android")]
const MAX_SAVED: usize = 256;
#[cfg(not(target_os = "android"))]
const MAX_SAVED: usize = 1024;""",
    )


patch_file("crates/horizon-client/src/streaming.rs", patch_streaming)
patch_file("crates/horizon-client/src/graphics.rs", patch_graphics)
patch_file("crates/horizon-client/src/settings.rs", patch_settings)
patch_file("crates/horizon-client/src/lod.rs", patch_lod)
print("Applied lower-allocation chunk scheduling and Android low-RAM LOD/cache defaults.")
