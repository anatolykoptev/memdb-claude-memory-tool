# CLAUDE.md

Notes for coding agents working in memdb-claude-memory-tool: a small Python package that backs
Anthropic's `memory_20250818` memory tool with the MemDB HTTP API. Every document is indexed in
[docs/INDEX.md](docs/INDEX.md).

## Layout

`src/memdb_claude_memory/`: `tool.py` (`MemDBMemoryTool`, a `BetaAbstractMemoryTool` subclass),
`http_client.py` (`MemDBClient`), `path_utils.py` (path validation), `formatters.py` (output
text). Tests are in `tests/`, runnable scripts in `examples/`, the upload helper in
`scripts/publish.sh`.

## Gate

CI (`.github/workflows/ci.yml`, job on Python 3.10, 3.11 and 3.12) runs exactly:

```sh
pip install -e ".[dev]"
ruff check src/ tests/
pytest tests/test_unit.py tests/test_formatters.py tests/test_path_utils.py -v
```

`tests/test_integration.py` is not part of the gate; it needs a running MemDB and
`MEMDB_INTEGRATION_TEST=1`. A docs-only PR (Markdown, `docs/`, licence, issue and PR templates)
skips the job through the `docs-scope` block in `ci.yml`; that block is canonical across the fleet
and compared byte for byte, so do not edit it here.

## Invariants that are easy to break

- **Paths are a security boundary.** Every path from the model goes through `validate_path`
  before it reaches MemDB, and must stay under `/memories`. Do not build a MemDB key from
  unvalidated input.
- **Tenant isolation is the `cube_id`.** Lookups, listings and deletes carry the tool's `cube_id`
  and `user_id`; a call that omits them can read or delete another tenant's files.
  `MemDBClient.update_memory` addresses a memory by id only, so the id must come from a lookup
  scoped to this cube, never from model input.
- **The tool answers in text, not exceptions.** Failures reach Claude as `ToolError`; keep MemDB
  errors wrapped (`MemDBError` into `ToolError`) so a backend failure does not crash the tool loop.
- **`rename` is not atomic** (get, create at the new path, delete the old one). Do not document it
  as atomic.
- **The version lives in two places**, `pyproject.toml` and `__version__` in
  `src/memdb_claude_memory/__init__.py`. A `v*` tag publishes to PyPI through
  `.github/workflows/publish.yml`, so bump both before tagging and never tag a broken build.
- **The secret is the `X-Service-Secret` header**, taken from the constructor argument. Never log
  it or put a real value in a test or example.
- **This repository is public.** No hostnames, operator paths, account names, tokens or personal
  data in any tracked file.
