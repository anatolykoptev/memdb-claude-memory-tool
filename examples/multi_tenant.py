#!/usr/bin/env python3
"""Multi-tenant example — one MemDB instance, many users.

Each user gets their own ``cube_id``, so memories are fully isolated.
Claude sees only the memories belonging to the cube it's talking to.

Usage::

    ANTHROPIC_API_KEY=sk-ant-... python3 examples/multi_tenant.py
    ANTHROPIC_API_KEY=sk-ant-... MEMDB_URL=http://localhost:8080 MEMDB_SECRET=s python3 examples/multi_tenant.py
"""

import os
import sys

import anthropic
import requests

from memdb_claude_memory import MemDBMemoryTool

MEMDB_URL = os.getenv("MEMDB_URL", "http://localhost:8080")
MEMDB_SECRET = os.getenv("MEMDB_SECRET", "")

# Connectivity check
try:
    requests.get(f"{MEMDB_URL}/health", timeout=5).raise_for_status()
except Exception as exc:
    print(f"ERROR: MemDB unreachable at {MEMDB_URL}: {exc}", file=sys.stderr)
    sys.exit(1)


def make_tool(user_id: str) -> MemDBMemoryTool:
    """Create a memory tool scoped to a single user."""
    return MemDBMemoryTool(
        memdb_url=MEMDB_URL,
        cube_id=user_id,  # one cube per user — full isolation
        user_id=user_id,
        service_secret=MEMDB_SECRET,
    )


def chat(user_id: str, message: str) -> str:
    """Single-turn chat for a given user."""
    client = anthropic.Anthropic()
    tool = make_tool(user_id)
    result = (
        client.beta.messages.tool_runner(
            model="claude-sonnet-4-5",
            betas=["context-management-2025-06-27"],
            tools=[tool],
            messages=[{"role": "user", "content": message}],
            max_tokens=512,
        )
        .until_done()
    )
    return result.content[-1].text if result.content else ""


# Alice stores her preference
print("Alice:", chat("alice", "Remember I love Python."))

# Bob stores his preference
print("Bob:", chat("bob", "Remember I prefer Rust."))

# Each user recalls independently — memories don't bleed across cubes
print("Alice recalls:", chat("alice", "What language do I love?"))
print("Bob recalls:", chat("bob", "What language do I prefer?"))
