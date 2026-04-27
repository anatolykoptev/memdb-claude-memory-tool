#!/usr/bin/env python3
"""Full Anthropic API loop with MemDB memory tool.

Claude stores and recalls memories across turns using MemDB as the backend.

Usage::

    ANTHROPIC_API_KEY=sk-ant-... python3 examples/end_to_end_claude.py
    ANTHROPIC_API_KEY=sk-ant-... MEMDB_URL=http://localhost:8080 MEMDB_SECRET=s python3 examples/end_to_end_claude.py
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

memory = MemDBMemoryTool(
    memdb_url=MEMDB_URL,
    cube_id="demo-user",
    user_id="demo-user",
    service_secret=MEMDB_SECRET,
)

client = anthropic.Anthropic()


def chat(message: str) -> str:
    result = (
        client.beta.messages.tool_runner(
            model="claude-sonnet-4-5",
            betas=["context-management-2025-06-27"],
            tools=[memory],
            messages=[{"role": "user", "content": message}],
            max_tokens=1024,
        )
        .until_done()
    )
    return result.content[-1].text if result.content else ""


print("Turn 1: store a preference")
print("Claude:", chat("Remember that I prefer TypeScript over JavaScript."))

print("\nTurn 2: recall")
print("Claude:", chat("What programming language do I prefer?"))
