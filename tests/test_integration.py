"""Integration tests — require a running MemDB instance.

Skipped unless ``MEMDB_INTEGRATION_TEST=1`` is set.

Usage::

    MEMDB_INTEGRATION_TEST=1 pytest tests/test_integration.py -v

Assumes MemDB is running at ``MEMDB_URL`` (default: http://localhost:8080).
Auth disabled (default MemDB config). If AUTH_ENABLED=true, set
``MEMDB_SERVICE_SECRET`` env var.
"""

from __future__ import annotations

import os
import time
import pytest

from memdb_claude_memory import MemDBMemoryTool
from anthropic.lib.tools._beta_builtin_memory_tool import (
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818StrReplaceCommand,
    BetaMemoryTool20250818ViewCommand,
)

SKIP = not os.getenv("MEMDB_INTEGRATION_TEST")
REASON = "set MEMDB_INTEGRATION_TEST=1 to run integration tests"

MEMDB_URL = os.getenv("MEMDB_URL", "http://localhost:8080")
MEMDB_SECRET = os.getenv("MEMDB_SERVICE_SECRET", "")
CUBE = f"integration-test-{int(time.time())}"


@pytest.fixture(scope="module")
def tool():
    t = MemDBMemoryTool(
        memdb_url=MEMDB_URL,
        cube_id=CUBE,
        user_id=CUBE,
        service_secret=MEMDB_SECRET,
        timeout=15,
    )
    yield t
    # Cleanup: clear all memories created during the test
    t.clear_all_memory()


@pytest.mark.skipif(SKIP, reason=REASON)
class TestIntegration:
    def test_create_and_view(self, tool):
        path = f"/memories/{CUBE}/hello.txt"
        tool.create(BetaMemoryTool20250818CreateCommand(
            command="create", path=path, file_text="hello world\nsecond line"
        ))
        result = tool.view(BetaMemoryTool20250818ViewCommand(
            command="view", path=path, view_range=None
        ))
        assert "hello world" in result
        assert "second line" in result

    def test_str_replace(self, tool):
        path = f"/memories/{CUBE}/replace.txt"
        tool.create(BetaMemoryTool20250818CreateCommand(
            command="create", path=path, file_text="foo bar baz"
        ))
        tool.str_replace(BetaMemoryTool20250818StrReplaceCommand(
            command="str_replace", path=path, old_str="bar", new_str="QUX"
        ))
        result = tool.view(BetaMemoryTool20250818ViewCommand(
            command="view", path=path, view_range=None
        ))
        assert "QUX" in result
        assert "bar" not in result

    def test_insert(self, tool):
        path = f"/memories/{CUBE}/insert.txt"
        tool.create(BetaMemoryTool20250818CreateCommand(
            command="create", path=path, file_text="line1\nline3"
        ))
        tool.insert(BetaMemoryTool20250818InsertCommand(
            command="insert", path=path, insert_line=1, insert_text="line2"
        ))
        result = tool.view(BetaMemoryTool20250818ViewCommand(
            command="view", path=path, view_range=None
        ))
        lines_in_order = ["line1", "line2", "line3"]
        for ln in lines_in_order:
            assert ln in result

    def test_delete(self, tool):
        path = f"/memories/{CUBE}/delete_me.txt"
        tool.create(BetaMemoryTool20250818CreateCommand(
            command="create", path=path, file_text="to be deleted"
        ))
        tool.delete(BetaMemoryTool20250818DeleteCommand(command="delete", path=path))
        # After delete, view should raise ToolError
        from anthropic.lib.tools._beta_builtin_memory_tool import ToolError
        with pytest.raises(ToolError):
            tool.view(BetaMemoryTool20250818ViewCommand(
                command="view", path=path, view_range=None
            ))

    def test_dir_listing(self, tool):
        prefix = f"/memories/{CUBE}/subdir"
        for i in range(3):
            tool.create(BetaMemoryTool20250818CreateCommand(
                command="create",
                path=f"{prefix}/file{i}.txt",
                file_text=f"content {i}",
            ))
        result = tool.view(BetaMemoryTool20250818ViewCommand(
            command="view", path=prefix, view_range=None
        ))
        assert "2 levels deep" in result
        for i in range(3):
            assert f"file{i}.txt" in result
