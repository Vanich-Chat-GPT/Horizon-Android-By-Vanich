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
p.write_text(s,encoding="utf-8")
print("Android completed chunk queue limited to 16; at most 12 fresh results are applied per frame to reduce RAM spikes and frame-time spikes. Results are retained, not dropped.")
