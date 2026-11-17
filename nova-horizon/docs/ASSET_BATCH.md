# Mojang asset batch pipeline

The installer validates the official version descriptor and asset-index JSON in the Rust core. Asset entries are deduplicated by SHA-1 and sorted deterministically before the Android layer sees them.

The Android pipeline then:

1. Downloads the asset index through the same HTTPS allow-list and SHA-1 verification used for other official artifacts.
2. Writes a compact, private, atomic manifest containing object hashes, sizes, content URLs, canonical relative paths and logical names.
3. Runs one cancellable user-initiated batch instead of creating thousands of independent Android jobs. At most four object transfers run concurrently.
4. Resumes partial files only when the server supplies a strong ETag and the returned Content-Range is exact. Every completed object is SHA-1 checked before atomic placement.
5. Materializes legacy `virtual` and `map_to_resources` layouts using hard links where supported, falling back to checked copies when necessary.

The batch progress is persisted as one aggregate download record. The object store remains content-addressed under `assets/objects/<prefix>/<sha1>`; logical aliases do not cause duplicate network downloads.

This pipeline does not make the game launch-ready. A compatible Android Java runtime, native-library resolution, LWJGL/platform bridge, renderer/input/audio integration, Microsoft OAuth and a real end-to-end world-launch test remain separate required milestones.
