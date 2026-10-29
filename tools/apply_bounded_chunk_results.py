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
replace("        let (send, results) = mpsc::channel();",
'''        // Keep expensive completed meshes and chunk snapshots from piling up
        // on mobile devices if generation outruns the renderer.
        #[cfg(target_os = "android")]
        let (send, results) = mpsc::sync_channel(16);
        #[cfg(not(target_os = "android"))]
        let (send, results) = mpsc::channel();''')
replace('''                            if send.send(done).is_err() {
                                return;
                            }''',
'''                            #[cfg(not(target_os = "android"))]
                            if send.send(done).is_err() {
                                return;
                            }
                            #[cfg(target_os = "android")]
                            {
                                let mut pending = done;
                                loop {
                                    if shared.stop.load(Ordering::Relaxed) {
                                        return;
                                    }
                                    match send.try_send(pending) {
                                        Ok(()) => break,
                                        Err(mpsc::TrySendError::Disconnected(_)) => return,
                                        Err(mpsc::TrySendError::Full(unsent)) => {
                                            pending = unsent;
                                            // Backpressure workers to avoid memory spikes,
                                            // never discard a chunk or a completed mesh.
                                            thread::sleep(std::time::Duration::from_millis(2));
                                        }
                                    }
                                }
                            }''')
# Keep queued lighting/mesh snapshots bounded on Android. When the queue
# is full, leave dirty work marked in World so a later update can schedule it;
# never discard chunks, lighting changes, or meshes.
replace('''        let deferred = std::mem::take(&mut self.deferred);
        let received = std::iter::from_fn(|| self.results.try_recv().ok());
        for done in deferred.into_iter().chain(received.collect::<Vec<_>>()) {''',
'''        // Apply at most 12 completed results per update on Android. Keep the
        // remainder deferred/in the channel so mesh uploads cannot monopolize
        // a frame; scheduling changes only, world visuals remain identical.
        #[cfg(target_os = "android")]
        let (deferred, received) = {
            let mut deferred = std::mem::take(&mut self.deferred);
            let take = deferred.len().min(12);
            let remaining = deferred.split_off(take);
            self.deferred = remaining;
            let budget = 12 - take;
            let received = self.results.try_iter().take(budget).collect::<Vec<_>>();
            (deferred, received)
        };
        #[cfg(not(target_os = "android"))]
        let (deferred, received) = {
            let deferred = std::mem::take(&mut self.deferred);
            let received = std::iter::from_fn(|| self.results.try_recv().ok()).collect::<Vec<_>>();
            (deferred, received)
        };
        for done in deferred.into_iter().chain(received) {''')
replace("        let workers = self.threads.len();",
'''        let workers = self.threads.len();
        #[cfg(target_os = "android")]
        let queue_limit = workers.saturating_mul(8).saturating_add(32);''')
replace('''        for (x, z) in light {
            if !world.chunks.contains_key(&(x, z)) {''',
'''        for (x, z) in light {
            #[cfg(target_os = "android")]
            if self.shared.queue.lock().unwrap().len() >= queue_limit {
                // Keep this key in dirty_light; it will be retried next update.
                continue;
            }
            if !world.chunks.contains_key(&(x, z)) {''')
replace('''            let Some(region) = Self::region(world, x, z) else {
                continue;
            };''',
'''            // Do not enqueue more section meshes than the worker pool can
            // reasonably drain. Leave dirty_sections untouched for a later
            // update, preserving the exact rendered geometry and block data.
            #[cfg(target_os = "android")]
            if self.shared.queue.lock().unwrap().len().saturating_add(section_indexes(sections).count()) > queue_limit {
                continue;
            }
            let Some(region) = Self::region(world, x, z) else {
                continue;
            };''')
# Reserve only the bounded number of candidate jobs before sorting and truncating.
# This avoids geometric Vec growth during wide render-distance scans.
replace("            let mut wanted = Vec::new();",
        "            // Reserve the bounded in-flight batch before scanning candidates.\n            let mut wanted = Vec::with_capacity(capacity - input.generating.len());")
p.write_text(s,encoding="utf-8")
print("Android bounds completed-result buffering and queued lighting/mesh snapshots; at most 12 results are applied per update. Deferred dirty work is retained, not dropped, preserving rendered content.")
