use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ChunkKey {
    pub x: i32,
    pub z: i32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ChunkJob {
    pub key: ChunkKey,
    pub distance_sq: u64,
    pub generation: u64,
    sequence: u64,
}

impl Ord for ChunkJob {
    fn cmp(&self, other: &Self) -> Ordering {
        // BinaryHeap is a max-heap: reverse distance to pop nearest work first.
        other
            .distance_sq
            .cmp(&self.distance_sq)
            .then_with(|| other.sequence.cmp(&self.sequence))
    }
}

impl PartialOrd for ChunkJob {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Generic background-work scheduler. It does not load Minecraft chunks or build meshes.
///
/// The active index deduplicates work by coordinate. Re-enqueuing a coordinate replaces
/// its active generation/priority; obsolete heap entries are discarded lazily.
#[derive(Debug, Default)]
pub struct ChunkWorkQueue {
    heap: BinaryHeap<ChunkJob>,
    active: HashMap<ChunkKey, (u64, u64)>,
    next_sequence: u64,
}

impl ChunkWorkQueue {
    pub fn enqueue(&mut self, key: ChunkKey, distance_sq: u64, generation: u64) {
        let sequence = self.next_sequence;
        self.next_sequence = self.next_sequence.wrapping_add(1);

        self.active.insert(key, (generation, sequence));
        self.heap.push(ChunkJob {
            key,
            distance_sq,
            generation,
            sequence,
        });

        self.compact_if_needed();
    }

    pub fn pop_next(&mut self, current_generation: u64) -> Option<ChunkJob> {
        while let Some(job) = self.heap.pop() {
            let is_current = self.active.get(&job.key) == Some(&(job.generation, job.sequence));
            if !is_current {
                continue;
            }
            self.active.remove(&job.key);

            if job.generation == current_generation {
                return Some(job);
            }
        }
        None
    }

    pub fn discard_stale(&mut self, current_generation: u64) {
        self.active
            .retain(|_, (generation, _)| *generation == current_generation);
        self.heap.retain(|job| {
            job.generation == current_generation
                && self.active.get(&job.key) == Some(&(job.generation, job.sequence))
        });
    }

    /// Number of current, deduplicated jobs (not raw heap entries).
    pub fn pending(&self) -> usize {
        self.active.len()
    }

    fn compact_if_needed(&mut self) {
        let active = self.active.len();
        let threshold = active.saturating_mul(2).saturating_add(64);
        if self.heap.len() <= threshold {
            return;
        }

        let active = &self.active;
        self.heap.retain(|job| active.get(&job.key) == Some(&(job.generation, job.sequence)));
    }
}

#[cfg(test)]
mod tests {
    use super::{ChunkKey, ChunkWorkQueue};

    #[test]
    fn nearest_job_is_popped_first() {
        let mut queue = ChunkWorkQueue::default();
        queue.enqueue(ChunkKey { x: 4, z: 4 }, 16, 1);
        queue.enqueue(ChunkKey { x: 1, z: 1 }, 2, 1);
        assert_eq!(queue.pop_next(1).unwrap().key, ChunkKey { x: 1, z: 1 });
    }

    #[test]
    fn stale_generation_is_never_returned() {
        let mut queue = ChunkWorkQueue::default();
        queue.enqueue(ChunkKey { x: 0, z: 0 }, 0, 3);
        queue.enqueue(ChunkKey { x: 1, z: 0 }, 1, 4);
        assert_eq!(queue.pop_next(4).unwrap().generation, 4);
        assert_eq!(queue.pop_next(4), None);
    }

    #[test]
    fn discard_stale_reclaims_queue_entries() {
        let mut queue = ChunkWorkQueue::default();
        queue.enqueue(ChunkKey { x: 0, z: 0 }, 0, 1);
        queue.enqueue(ChunkKey { x: 1, z: 0 }, 1, 2);
        queue.discard_stale(2);
        assert_eq!(queue.pending(), 1);
        assert_eq!(queue.pop_next(2).unwrap().key, ChunkKey { x: 1, z: 0 });
    }

    #[test]
    fn repeated_coordinates_replace_old_jobs() {
        let mut queue = ChunkWorkQueue::default();
        let key = ChunkKey { x: 3, z: -2 };
        queue.enqueue(key, 1, 7);
        queue.enqueue(key, 25, 7);
        assert_eq!(queue.pending(), 1);
        let current = queue.pop_next(7).unwrap();
        assert_eq!(current.key, key);
        assert_eq!(current.distance_sq, 25);
        assert_eq!(queue.pop_next(7), None);
    }

    #[test]
    fn new_generation_replaces_old_coordinate() {
        let mut queue = ChunkWorkQueue::default();
        let key = ChunkKey { x: 0, z: 0 };
        queue.enqueue(key, 0, 1);
        queue.enqueue(key, 9, 2);
        assert_eq!(queue.pop_next(2).unwrap().generation, 2);
        assert_eq!(queue.pending(), 0);
    }
}
