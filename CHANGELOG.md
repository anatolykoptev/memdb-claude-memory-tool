# Changelog

All notable changes to this project are recorded here, in the Keep a Changelog format, and the
project follows semantic versioning.

## [Unreleased]

### Changed

- CI skips the heavy job on pull requests that change only documents.

## [0.1.0] - 2026-04-26

### Added

- `MemDBMemoryTool`, a drop-in `BetaAbstractMemoryTool` backed by the MemDB HTTP API, with the
  six memory-tool commands (`view`, `create`, `str_replace`, `insert`, `delete`, `rename`) and
  `clear_all_memory`.
- `MemDBClient`, path validation and output formatters; per-tenant isolation through `cube_id`.
- Examples, unit tests and a PyPI publishing workflow.

### Changed

- Licence changed from MIT to Apache-2.0 to match MemDB.
