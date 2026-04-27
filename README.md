# memdb-claude-memory-tool

Production-grade backend for Anthropic Claude's [memory tool](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool) (`memory_20250818`).

Drop-in replacement for `BetaLocalFilesystemMemoryTool` — same six-method interface, MemDB storage.

## Why MemDB instead of local filesystem?

| Feature | `BetaLocalFilesystemMemoryTool` | `MemDBMemoryTool` |
|---------|--------------------------------|-------------------|
| Storage | Local filesystem | PostgreSQL + pgvector + Apache AGE |
| Multi-tenant | One directory per process | `cube_id` isolation — millions of users, one instance |
| Persistence across restarts | Yes (files survive) | Yes (Postgres-durable) |
| Semantic search bonus | No | Yes — MemDB indexes every write for vector search |
| GDPR / right-to-forget | `rm -rf` manually | `DELETE /product/delete_all_memories` |
| Self-hosted | Implicitly | Docker Compose in 2 minutes |
| Horizontal scale | No (single machine) | Yes (stateless app, shared DB) |

## Install

```bash
pip install memdb-claude-memory
```

> To install from source: `pip install git+https://github.com/anatolykoptev/memdb-claude-memory-tool.git`

## Quickstart

```python
import anthropic
from memdb_claude_memory import MemDBMemoryTool

memory = MemDBMemoryTool(
    memdb_url="http://localhost:8080",
    cube_id="alice",
    service_secret="",  # empty = AUTH_ENABLED=false (default)
)

client = anthropic.Anthropic()
result = (
    client.beta.messages.tool_runner(
        model="claude-sonnet-4-5",
        betas=["context-management-2025-06-27"],
        tools=[memory],
        messages=[{"role": "user", "content": "Remember I like TypeScript."}],
        max_tokens=1024,
    )
    .until_done()
)
print(result.content[-1].text)
```

## Multi-tenant pattern

One MemDB instance serves all users. Each user gets their own `cube_id`:

```python
def make_memory_tool(user_id: str) -> MemDBMemoryTool:
    return MemDBMemoryTool(
        memdb_url="http://localhost:8080",
        cube_id=user_id,   # full isolation per user
        user_id=user_id,
        service_secret=MEMDB_SECRET,
    )
```

Memories written for `cube_id="alice"` are invisible to `cube_id="bob"`.

## MemDB setup

```bash
git clone https://github.com/anatolykoptev/memdb && cd memdb
cp .env.example .env   # set POSTGRES_PASSWORD at minimum
docker compose -f docker/docker-compose.yml up -d
curl http://localhost:8080/health   # {"status":"ok"}
```

## Constructor reference

```python
MemDBMemoryTool(
    memdb_url="http://localhost:8080",  # MemDB base URL
    cube_id="default",                  # memory namespace (per user)
    user_id=None,                       # defaults to cube_id
    service_secret="",                  # X-Service-Secret header value
    timeout=10,                         # HTTP timeout per call (seconds)
)
```

## How it works

Each Claude memory file path (e.g. `/memories/users/alice/prefs.txt`) is stored as a MemDB
node with `key=<path>`. All six memory tool operations map to MemDB HTTP endpoints:

| Command | MemDB endpoint |
|---------|---------------|
| `create` | `POST /product/add` (`mode=raw`, `key=<path>`) |
| `view` (file) | `POST /product/get_memory_by_key` |
| `view` (dir) | `POST /product/list_memories_by_prefix` |
| `str_replace` | get by key → `POST /product/update_memory` |
| `insert` | get by key → `POST /product/update_memory` |
| `delete` (file) | get by key → `POST /product/delete_memory` |
| `delete` (dir) | list by prefix → batch `POST /product/delete_memory` |
| `rename` | get → create at new path → delete old (not atomic) |

## Publishing (maintainers only)

### One-time PyPI setup

1. Create PyPI account: https://pypi.org/account/register/
2. Reserve the package name on TestPyPI first: `bash scripts/publish.sh --testpypi`
3. Verify on TestPyPI: https://test.pypi.org/project/memdb-claude-memory/
4. Configure Trusted Publisher (no tokens needed) on PyPI:
   https://pypi.org/manage/project/memdb-claude-memory/settings/publishing/
   - Owner: `anatolykoptev`
   - Repository: `memdb-claude-memory-tool`
   - Workflow: `publish.yml`
   - Environment: *(leave blank)*
5. After this, every `git tag vX.Y.Z && git push origin vX.Y.Z` auto-publishes via GitHub Actions.

### Manual release

```bash
# Install publish deps
pip install --upgrade build twine

# Bump version in pyproject.toml, then:
git add pyproject.toml
git commit -m "chore: bump version to vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main vX.Y.Z

# OR manual upload without tagging:
bash scripts/publish.sh              # to real PyPI
bash scripts/publish.sh --testpypi  # dry-run on TestPyPI first
bash scripts/publish.sh --dry-run   # build + validate only, no upload
```

## See also

- [MemDB](https://github.com/anatolykoptev/memdb) — the storage backend
- [Anthropic memory tool docs](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool)
- [Anthropic SDK Python](https://github.com/anthropics/anthropic-sdk-python)
