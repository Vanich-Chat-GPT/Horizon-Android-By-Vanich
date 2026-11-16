/// Coarse-grained failure classes. They deliberately contain no URL, account data or path.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DownloadFailure {
    Network,
    Integrity,
    Storage,
    Protocol,
    Unknown,
}

/// State of one file transfer in the download pipeline.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DownloadState {
    Queued,
    Downloading {
        downloaded_bytes: u64,
        total_bytes: Option<u64>,
    },
    Verifying {
        downloaded_bytes: u64,
        total_bytes: Option<u64>,
    },
    Complete {
        bytes: u64,
    },
    Failed {
        kind: DownloadFailure,
        retryable: bool,
    },
    Cancelled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DownloadTransitionError {
    InvalidTransition,
    ProgressRegressed,
    TotalChanged,
    ProgressExceedsTotal,
    IncompleteTransfer,
    RetryLimitReached,
    NotRetryable,
}

/// Validates lifecycle transitions and byte counters for a single download.
///
/// This type does not perform network I/O or touch files. The Android download worker
/// must still implement safe partial-file handling, HTTP range validation and hashing.
#[derive(Debug, Clone)]
pub struct DownloadTaskState {
    state: DownloadState,
    downloaded_bytes: u64,
    total_bytes: Option<u64>,
    retries_used: u8,
    max_retries: u8,
}

impl DownloadTaskState {
    pub fn new(max_retries: u8) -> Self {
        Self {
            state: DownloadState::Queued,
            downloaded_bytes: 0,
            total_bytes: None,
            retries_used: 0,
            max_retries,
        }
    }

    pub fn state(&self) -> DownloadState {
        self.state
    }

    pub fn retries_used(&self) -> u8 {
        self.retries_used
    }

    pub fn resume_offset(&self) -> u64 {
        self.downloaded_bytes
    }

    pub fn start(&mut self) -> Result<(), DownloadTransitionError> {
        if self.state != DownloadState::Queued {
            return Err(DownloadTransitionError::InvalidTransition);
        }
        self.state = DownloadState::Downloading {
            downloaded_bytes: self.downloaded_bytes,
            total_bytes: self.total_bytes,
        };
        Ok(())
    }

    pub fn update_progress(
        &mut self,
        downloaded_bytes: u64,
        total_bytes: Option<u64>,
    ) -> Result<(), DownloadTransitionError> {
        let DownloadState::Downloading {
            downloaded_bytes: previous,
            total_bytes: previous_total,
        } = self.state
        else {
            return Err(DownloadTransitionError::InvalidTransition);
        };

        if downloaded_bytes < previous {
            return Err(DownloadTransitionError::ProgressRegressed);
        }

        if let (Some(previous), Some(next)) = (previous_total, total_bytes) {
            if previous != next {
                return Err(DownloadTransitionError::TotalChanged);
            }
        }

        let effective_total = total_bytes.or(previous_total);
        if effective_total.is_some_and(|total| downloaded_bytes > total) {
            return Err(DownloadTransitionError::ProgressExceedsTotal);
        }

        self.downloaded_bytes = downloaded_bytes;
        self.total_bytes = effective_total;
        self.state = DownloadState::Downloading {
            downloaded_bytes,
            total_bytes: effective_total,
        };
        Ok(())
    }

    pub fn begin_verification(&mut self) -> Result<(), DownloadTransitionError> {
        let DownloadState::Downloading {
            downloaded_bytes,
            total_bytes,
        } = self.state
        else {
            return Err(DownloadTransitionError::InvalidTransition);
        };

        if total_bytes.is_some_and(|total| total != downloaded_bytes) {
            return Err(DownloadTransitionError::IncompleteTransfer);
        }

        self.state = DownloadState::Verifying {
            downloaded_bytes,
            total_bytes,
        };
        Ok(())
    }

    pub fn mark_verified(&mut self) -> Result<(), DownloadTransitionError> {
        let DownloadState::Verifying {
            downloaded_bytes, ..
        } = self.state
        else {
            return Err(DownloadTransitionError::InvalidTransition);
        };

        self.state = DownloadState::Complete {
            bytes: downloaded_bytes,
        };
        Ok(())
    }

    pub fn fail(
        &mut self,
        kind: DownloadFailure,
        retryable: bool,
    ) -> Result<(), DownloadTransitionError> {
        if !matches!(
            self.state,
            DownloadState::Downloading { .. } | DownloadState::Verifying { .. }
        ) {
            return Err(DownloadTransitionError::InvalidTransition);
        }
        self.state = DownloadState::Failed { kind, retryable };
        Ok(())
    }

    /// Returns to Queued. Network/storage retries preserve the verified partial offset;
    /// integrity retries restart the transfer from byte zero.
    pub fn retry(&mut self) -> Result<(), DownloadTransitionError> {
        let DownloadState::Failed { kind, retryable } = self.state else {
            return Err(DownloadTransitionError::InvalidTransition);
        };

        if !retryable {
            return Err(DownloadTransitionError::NotRetryable);
        }
        if self.retries_used >= self.max_retries {
            return Err(DownloadTransitionError::RetryLimitReached);
        }

        self.retries_used += 1;
        if kind == DownloadFailure::Integrity {
            self.downloaded_bytes = 0;
            self.total_bytes = None;
        }
        self.state = DownloadState::Queued;
        Ok(())
    }

    pub fn cancel(&mut self) -> Result<(), DownloadTransitionError> {
        if matches!(
            self.state,
            DownloadState::Complete { .. } | DownloadState::Cancelled
        ) {
            return Err(DownloadTransitionError::InvalidTransition);
        }
        self.state = DownloadState::Cancelled;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DownloadFailure, DownloadState, DownloadTaskState, DownloadTransitionError,
    };

    #[test]
    fn transfer_must_finish_before_verification() {
        let mut task = DownloadTaskState::new(2);
        task.start().unwrap();
        task.update_progress(40, Some(100)).unwrap();
        assert_eq!(
            task.begin_verification(),
            Err(DownloadTransitionError::IncompleteTransfer)
        );
        task.update_progress(100, Some(100)).unwrap();
        task.begin_verification().unwrap();
        task.mark_verified().unwrap();
        assert_eq!(task.state(), DownloadState::Complete { bytes: 100 });
    }

    #[test]
    fn progress_is_monotonic_and_cannot_exceed_content_length() {
        let mut task = DownloadTaskState::new(1);
        task.start().unwrap();
        task.update_progress(80, Some(100)).unwrap();
        assert_eq!(
            task.update_progress(70, Some(100)),
            Err(DownloadTransitionError::ProgressRegressed)
        );
        assert_eq!(
            task.update_progress(101, Some(100)),
            Err(DownloadTransitionError::ProgressExceedsTotal)
        );
        assert_eq!(
            task.update_progress(90, Some(120)),
            Err(DownloadTransitionError::TotalChanged)
        );
    }

    #[test]
    fn retryable_network_failure_keeps_resume_offset() {
        let mut task = DownloadTaskState::new(1);
        task.start().unwrap();
        task.update_progress(512, Some(1024)).unwrap();
        task.fail(DownloadFailure::Network, true).unwrap();
        task.retry().unwrap();
        assert_eq!(task.resume_offset(), 512);
        task.start().unwrap();
        assert_eq!(
            task.state(),
            DownloadState::Downloading {
                downloaded_bytes: 512,
                total_bytes: Some(1024)
            }
        );
    }

    #[test]
    fn integrity_retry_resets_untrusted_partial_data() {
        let mut task = DownloadTaskState::new(1);
        task.start().unwrap();
        task.update_progress(512, Some(1024)).unwrap();
        task.begin_verification().unwrap_err();
        task.fail(DownloadFailure::Integrity, true).unwrap();
        task.retry().unwrap();
        assert_eq!(task.resume_offset(), 0);
        assert_eq!(task.state(), DownloadState::Queued);
    }

    #[test]
    fn retry_limit_and_non_retryable_failures_are_enforced() {
        let mut task = DownloadTaskState::new(0);
        task.start().unwrap();
        task.fail(DownloadFailure::Protocol, true).unwrap();
        assert_eq!(
            task.retry(),
            Err(DownloadTransitionError::RetryLimitReached)
        );

        let mut other = DownloadTaskState::new(2);
        other.start().unwrap();
        other.fail(DownloadFailure::Protocol, false).unwrap();
        assert_eq!(
            other.retry(),
            Err(DownloadTransitionError::NotRetryable)
        );
    }

    #[test]
    fn cancellation_is_terminal() {
        let mut task = DownloadTaskState::new(1);
        task.cancel().unwrap();
        assert_eq!(task.state(), DownloadState::Cancelled);
        assert_eq!(
            task.start(),
            Err(DownloadTransitionError::InvalidTransition)
        );
    }
}
