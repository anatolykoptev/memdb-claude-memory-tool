#!/usr/bin/env python3
"""Minimal quickstart — create, view, delete a memory file directly.

No Anthropic API key required. Talks to MemDB only.

Usage::

    MEMDB_URL=http://localhost:8080 python3 examples/quickstart.py
    MEMDB_URL=http://localhost:8080 MEMDB_SECRET=mysecret python3 examples/quickstart.py
"""

import os
import sys

from anthropic.lib.tools._beta_builtin_memory_tool import (
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818ViewCommand,
)

from memdb_claude_memory import MemDBMemoryTool

MEMDB_URL = os.getenv("MEMDB_URL", "http://localhost:8080")
MEMDB_SECRET = os.getenv("MEMDB_SECRET", "")

# Quick connectivity check
import requests

try:
    resp = requests.get(f"{MEMDB_URL}/health", timeout=5)
    resp.raise_for_status()
except Exception as exc:
    print(f"ERROR: MemDB unreachable at {MEMDB_URL}: {exc}", file=sys.stderr)
    print("Start MemDB with: docker compose -f docker/docker-compose.yml up -d", file=sys.stderr)
    sys.exit(1)

tool = MemDBMemoryTool(
    memdb_url=MEMDB_URL,
    cube_id="quickstart",
    user_id="quickstart",
    service_secret=MEMDB_SECRET,
)

print("create  →", tool.create(BetaMemoryTool20250818CreateCommand(
    command="create",
    path="/memories/hello.txt",
    file_text="Hello from MemDB!\n",
)))

print("view    →", tool.view(BetaMemoryTool20250818ViewCommand(
    command="view",
    path="/memories/hello.txt",
    view_range=None,
)))

print("delete  →", tool.delete(BetaMemoryTool20250818DeleteCommand(
    command="delete",
    path="/memories/hello.txt",
)))

print("\nAll operations succeeded.")
