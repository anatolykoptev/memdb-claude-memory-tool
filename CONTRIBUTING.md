# Contributing

Bug reports, fixes and small features are welcome. For a larger change, open an issue first so the
approach can be agreed before you write it.

## Development

Python 3.10 or newer.

```sh
git clone https://github.com/anatolykoptev/memdb-claude-memory-tool.git
cd memdb-claude-memory-tool
pip install -e ".[dev]"
ruff check src/ tests/
pytest tests/test_unit.py tests/test_formatters.py tests/test_path_utils.py -v
```

These are the commands CI runs on Python 3.10, 3.11 and 3.12 (`.github/workflows/ci.yml`); if they
pass locally they pass there. A pull request that changes only documents skips that job.

The integration tests talk to a real MemDB (see the README for starting one):

```sh
MEMDB_INTEGRATION_TEST=1 pytest tests/test_integration.py -v
```

## Commits

Conventional Commits in the style of the history: `feat:`, `fix:`, `chore:`, `ci:`, `docs:`,
`test:`. No release tool reads them; a release is a version bump plus a `v*` tag by a maintainer.

## Pull requests

One concern per pull request. State what changed and how you tested it, and add a test for new
behaviour. A change that touches path validation or tenant isolation needs a test that shows the
unsafe input being rejected. Update [docs/INDEX.md](docs/INDEX.md) when you add or rename a
document.
