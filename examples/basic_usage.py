"""Basic usage example — Claude + MemDB memory tool.

Prerequisites:
    pip install anthropic memdb-claude-memory

    # MemDB running at localhost:8080 (AUTH_ENABLED=false default)
    docker run -e POSTGRES_PASSWORD=pass -p 8080:8080 ghcr.io/anatolykoptev/memdb:latest

Usage::

    ANTHROPIC_API_KEY=sk-... python examples/basic_usage.py
"""

import anthropic
from memdb_claude_memory import MemDBMemoryTool

# One tool instance = one memory namespace (cube_id)
memory = MemDBMemoryTool(
    memdb_url="http://localhost:8080",
    cube_id="alice",
    user_id="alice",
    service_secret="",  # leave empty when AUTH_ENABLED=false
)

client = anthropic.Anthropic()

messages = [
    {"role": "user", "content": "Remember that I prefer TypeScript over JavaScript."},
]

print("Turn 1: store a preference")
result = (
    client.beta.messages.run_tools(
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
    client.beta.messages.run_tools(
        model="claude-sonnet-4-5",
        betas=["context-management-2025-06-27"],
        tools=[memory],
        messages=messages,
        max_tokens=1024,
    )
    .until_done()
)
print("Response:", result.content[-1].text if result.content else "(no text)")
