# Download state model

The Rust core now contains a tested per-file transfer state model.

Supported transitions:
- Queued -> Downloading
- Downloading -> Verifying -> Complete
- Downloading/Verifying -> Failed
- Failed -> Queued for an explicitly retryable failure and while retry budget remains
- Any non-terminal state -> Cancelled

Byte accounting is monotonic and rejects content-length changes or progress beyond a known total. Retryable network failures preserve the resume offset. Integrity failures reset the offset so corrupted bytes are never trusted.

Important: this is only a deterministic state machine. It does not open sockets, create partial files, issue HTTP Range requests, or calculate SHA-1/SHA-256. The Android worker must verify server range support and validators, stage files, compare official hashes, fsync, and atomically promote only verified files before marking a task complete.
