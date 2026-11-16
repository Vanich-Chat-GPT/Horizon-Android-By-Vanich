use std::cmp::Ordering;
use std::collections::BinaryHeap;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
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
#[derive(Debug, Default)]
pub struct ChunkWorkQueue {
    heap: BinaryHeap<ChunkJob>,
    next_sequence: u64,
}

impl ChunkWorkQueue {
    pub fn enqueue(&mut self, key: ChunkKey, distance_sq: u64, generation: u64) {
        let job = ChunkJob {
            key,
            distance_sq,
            generation,
            sequence: self.next_sequence,
        };
        self.next_sequence = self.next_sequence.wrapping_add(1);
        self.heap.push(job);
    }

    pub fn pop_next(&mut self, current_generation: u64) -> Option<ChunkJob> {
        while let Some(job) = self.heap.pop() {
            if job.generation == current_generation {
                return Some(job);
            }
        }
        None
    }

    pub fn discard_stale(&mut self, current_generation: u64) {
        self.heap = self
            .heap
            .drain()
            .filter(|job| job.generation == current_generation)
            .collect();
    }

    pub fn pending(&self) -> usize {
        self.heap.len()
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
    }
}
