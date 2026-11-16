use std::collections::VecDeque;

const DEFAULT_CAPACITY: usize = 120;

/// A bounded rolling window of frame durations in nanoseconds.
#[derive(Debug, Clone)]
pub struct FrameTimeWindow {
    capacity: usize,
    samples: VecDeque<u64>,
}

impl Default for FrameTimeWindow {
    fn default() -> Self {
        Self::new(DEFAULT_CAPACITY)
    }
}

impl FrameTimeWindow {
    pub fn new(capacity: usize) -> Self {
        Self {
            capacity: capacity.max(1),
            samples: VecDeque::with_capacity(capacity.max(1)),
        }
    }

    pub fn push_ns(&mut self, frame_time_ns: u64) {
        if frame_time_ns == 0 {
            return;
        }
        if self.samples.len() == self.capacity {
            self.samples.pop_front();
        }
        self.samples.push_back(frame_time_ns);
    }

    pub fn len(&self) -> usize {
        self.samples.len()
    }

    pub fn is_empty(&self) -> bool {
        self.samples.is_empty()
    }

    pub fn average_ns(&self) -> Option<u64> {
        if self.samples.is_empty() {
            return None;
        }
        let sum: u128 = self.samples.iter().map(|&value| u128::from(value)).sum();
        Some((sum / self.samples.len() as u128) as u64)
    }

    pub fn fps_from_average(&self) -> Option<f64> {
        self.average_ns()
            .map(|average| 1_000_000_000.0 / average as f64)
    }

    pub fn percentile_ns(&self, percentile: u8) -> Option<u64> {
        if self.samples.is_empty() {
            return None;
        }
        let mut ordered: Vec<u64> = self.samples.iter().copied().collect();
        ordered.sort_unstable();
        let p = usize::from(percentile.min(100));
        let index = ((ordered.len() - 1) * p).div_ceil(100);
        ordered.get(index).copied()
    }
}

#[cfg(test)]
mod tests {
    use super::FrameTimeWindow;

    #[test]
    fn rolling_window_evicts_oldest_sample() {
        let mut window = FrameTimeWindow::new(2);
        window.push_ns(10);
        window.push_ns(20);
        window.push_ns(30);
        assert_eq!(window.len(), 2);
        assert_eq!(window.average_ns(), Some(25));
    }

    #[test]
    fn zero_duration_is_ignored() {
        let mut window = FrameTimeWindow::default();
        window.push_ns(0);
        assert!(window.is_empty());
    }

    #[test]
    fn percentile_returns_sorted_sample() {
        let mut window = FrameTimeWindow::new(4);
        for value in [40, 10, 30, 20] {
            window.push_ns(value);
        }
        assert_eq!(window.percentile_ns(50), Some(30));
    }
}
