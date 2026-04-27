#!/usr/bin/env python3
"""Basic usage example — Claude + MemDB memory tool.

Usage::

    ANTHROPIC_API_KEY=sk-ant-... python3 examples/basic_usage.py
    ANTHROPIC_API_KEY=sk-ant-... MEMDB_URL=http://localhost:8080 MEMDB_SECRET=s python3 examples/basic_usage.py
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
    print("Start MemDB with: docker compose -f docker/docker-compose.yml up -d", file=sys.stderr)
    sys.exit(1)

# One tool instance = one memory namespace (cube_id)
memory = MemDBMemoryTool(
    memdb_url=MEMDB_URL,
    cube_id="alice",
    user_id="alice",
    service_secret=MEMDB_SECRET,
)

client = anthropic.Anthropic()

messages = [
    {"role": "user", "content": "Remember that I prefer TypeScript over JavaScript."},
]

print("Turn 1: store a preference")
result = (
    client.beta.messages.tool_runner(
        model="claude-sonnet-4-5",
        betas=["context-management-2025-06-27"],
        tools=[memory],
        messages=messages,
        max_tokens=1024,
    )
    .until_done()
)
print("Response:", result.content[-1].text if result.content else "(no text)")

# Second turn — Claude should recall from memory
messages = [
    {"role": "user", "content": "What language do I prefer?"},
]

print("\nTurn 2: recall")
result = (
    client.beta.messages.tool_runner(
        model="claude-sonnet-4-5",
        betas=["context-management-2025-06-27"],
        tools=[memory],
        messages=messages,
        max_tokens=1024,
    )
    .until_done()
)
print("Response:", result.content[-1].text if result.content else "(no text)")
