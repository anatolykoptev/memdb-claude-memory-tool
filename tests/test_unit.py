"""Unit tests for MemDBMemoryTool — all HTTP stubbed via responses library."""

from __future__ import annotations

import json
import pytest
import responses as rsps_lib

from anthropic.lib.tools._beta_builtin_memory_tool import (
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818RenameCommand,
    BetaMemoryTool20250818StrReplaceCommand,
    BetaMemoryTool20250818ViewCommand,
    ToolError,
)

from memdb_claude_memory import MemDBMemoryTool

BASE = "http://memdb-test:8080"
CUBE = "test-cube"
USER = "test-user"


@pytest.fixture
def tool():
    return MemDBMemoryTool(
        memdb_url=BASE,
        cube_id=CUBE,
        user_id=USER,
        service_secret="secret",
        timeout=5,
    )


def _wrap(data):
    return {"code": 200, "message": "ok", "data": data}


def _add_response():
    return _wrap([])


def _memory_data(memory_id, text, key="/memories/foo.txt"):
    return _wrap({
        "memory_id": memory_id,
        "properties": {
            "memory": text,
            "key": key,
            "memory_type": "LongTermMemory",
        },
    })


def _list_response(items):
    return _wrap(items)


# ------------------------------------------------------------------
# create
# ------------------------------------------------------------------

@rsps_lib.activate
def test_create_sends_correct_request(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/add",
        json=_add_response(), status=200,
    )
    cmd = BetaMemoryTool20250818CreateCommand(
        command="create",
        path="/memories/notes.txt",
        file_text="hello world",
    )
    result = tool.create(cmd)
    assert "File created successfully at: /memories/notes.txt" in result

    req_body = json.loads(rsps_lib.calls[0].request.body)
    assert req_body["key"] == "/memories/notes.txt"
    assert req_body["mode"] == "raw"
    assert req_body["async_mode"] == "sync"
    assert req_body["messages"][0]["content"] == "hello world"
    assert req_body["writable_cube_ids"] == [CUBE]
    assert req_body["user_id"] == USER


@rsps_lib.activate
def test_create_invalid_path_raises_tool_error(tool):
    cmd = BetaMemoryTool20250818CreateCommand(
        command="create",
        path="/tmp/bad.txt",
        file_text="x",
    )
    with pytest.raises(ToolError, match="must start with /memories"):
        tool.create(cmd)


# ------------------------------------------------------------------
# view — file
# ------------------------------------------------------------------

@rsps_lib.activate
def test_view_file_returns_numbered_lines(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "line one\nline two"),
        status=200,
    )
    cmd = BetaMemoryTool20250818ViewCommand(
        command="view",
        path="/memories/foo.txt",
        view_range=None,
    )
    result = tool.view(cmd)
    assert "Here's the content of /memories/foo.txt with line numbers:" in result
    assert "1\tline one" in result
    assert "2\tline two" in result


@rsps_lib.activate
def test_view_file_404_raises_tool_error(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json={"code": 404, "message": "memory not found", "data": None},
        status=404,
    )
    cmd = BetaMemoryTool20250818ViewCommand(
        command="view",
        path="/memories/missing.txt",
        view_range=None,
    )
    with pytest.raises(ToolError, match="does not exist"):
        tool.view(cmd)


@rsps_lib.activate
def test_view_file_range(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "a\nb\nc\nd\ne"),
        status=200,
    )
    cmd = BetaMemoryTool20250818ViewCommand(
        command="view",
        path="/memories/foo.txt",
        view_range=[2, 4],
    )
    result = tool.view(cmd)
    assert "2\tb" in result
    assert "1\ta" not in result


# ------------------------------------------------------------------
# view — directory
# ------------------------------------------------------------------

@rsps_lib.activate
def test_view_directory(tool):
    items = [
        {"id": "u1", "key": "/memories/users/alice.txt", "char_size": 100,
         "memory_type": "LongTermMemory", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"id": "u2", "key": "/memories/users/bob.txt", "char_size": 50,
         "memory_type": "LongTermMemory", "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ]
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/list_memories_by_prefix",
        json=_list_response(items), status=200,
    )
    cmd = BetaMemoryTool20250818ViewCommand(
        command="view",
        path="/memories/users",
        view_range=None,
    )
    result = tool.view(cmd)
    assert "2 levels deep" in result
    assert "alice.txt" in result
    assert "bob.txt" in result

    req_body = json.loads(rsps_lib.calls[0].request.body)
    assert req_body["prefix"] == "/memories/users/"
    assert req_body["cube_id"] == CUBE
    assert req_body["user_id"] == USER


# ------------------------------------------------------------------
# str_replace
# ------------------------------------------------------------------

@rsps_lib.activate
def test_str_replace_success(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "hello world\nsecond line"),
        status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/update_memory",
        json=_wrap({}), status=200,
    )
    cmd = BetaMemoryTool20250818StrReplaceCommand(
        command="str_replace",
        path="/memories/foo.txt",
        old_str="hello world",
        new_str="goodbye world",
    )
    result = tool.str_replace(cmd)
    assert "has been edited" in result

    update_body = json.loads(rsps_lib.calls[1].request.body)
    assert update_body["memory_id"] == "uuid-1"
    assert "goodbye world" in update_body["memory"]


@rsps_lib.activate
def test_str_replace_not_found_raises(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "hello world"),
        status=200,
    )
    cmd = BetaMemoryTool20250818StrReplaceCommand(
        command="str_replace",
        path="/memories/foo.txt",
        old_str="nonexistent",
        new_str="x",
    )
    with pytest.raises(ToolError, match="did not appear verbatim"):
        tool.str_replace(cmd)


@rsps_lib.activate
def test_str_replace_multiple_matches_raises(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "foo\nfoo\nbar"),
        status=200,
    )
    cmd = BetaMemoryTool20250818StrReplaceCommand(
        command="str_replace",
        path="/memories/foo.txt",
        old_str="foo",
        new_str="baz",
    )
    with pytest.raises(ToolError, match="Multiple occurrences"):
        tool.str_replace(cmd)


# ------------------------------------------------------------------
# insert
# ------------------------------------------------------------------

@rsps_lib.activate
def test_insert_success(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "line1\nline2"),
        status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/update_memory",
        json=_wrap({}), status=200,
    )
    cmd = BetaMemoryTool20250818InsertCommand(
        command="insert",
        path="/memories/foo.txt",
        insert_line=1,
        insert_text="inserted",
    )
    result = tool.insert(cmd)
    assert "has been edited" in result

    update_body = json.loads(rsps_lib.calls[1].request.body)
    lines = update_body["memory"].splitlines()
    assert lines[0] == "line1"
    assert lines[1] == "inserted"
    assert lines[2] == "line2"


@rsps_lib.activate
def test_insert_line_0_prepends(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "line1\nline2"),
        status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/update_memory",
        json=_wrap({}), status=200,
    )
    cmd = BetaMemoryTool20250818InsertCommand(
        command="insert",
        path="/memories/foo.txt",
        insert_line=0,
        insert_text="prepended",
    )
    tool.insert(cmd)
    update_body = json.loads(rsps_lib.calls[1].request.body)
    lines = update_body["memory"].splitlines()
    assert lines[0] == "prepended"
    assert lines[1] == "line1"


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------

@rsps_lib.activate
def test_delete_file(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "text"),
        status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/delete_memory",
        json=_wrap({"deleted": 1}), status=200,
    )
    cmd = BetaMemoryTool20250818DeleteCommand(
        command="delete",
        path="/memories/foo.txt",
    )
    result = tool.delete(cmd)
    assert "Successfully deleted" in result

    del_body = json.loads(rsps_lib.calls[1].request.body)
    assert "uuid-1" in del_body["memory_ids"]


@rsps_lib.activate
def test_delete_root_raises(tool):
    cmd = BetaMemoryTool20250818DeleteCommand(
        command="delete",
        path="/memories",
    )
    with pytest.raises(ToolError, match="Cannot delete"):
        tool.delete(cmd)


@rsps_lib.activate
def test_delete_directory(tool):
    items = [
        {"id": "u1", "key": "/memories/dir/a.txt", "char_size": 10,
         "memory_type": "LongTermMemory", "created_at": "", "updated_at": ""},
        {"id": "u2", "key": "/memories/dir/b.txt", "char_size": 20,
         "memory_type": "LongTermMemory", "created_at": "", "updated_at": ""},
    ]
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/list_memories_by_prefix",
        json=_list_response(items), status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/delete_memory",
        json=_wrap({"deleted": 2}), status=200,
    )
    cmd = BetaMemoryTool20250818DeleteCommand(
        command="delete",
        path="/memories/dir",
    )
    result = tool.delete(cmd)
    assert "Successfully deleted" in result

    del_body = json.loads(rsps_lib.calls[1].request.body)
    assert set(del_body["memory_ids"]) == {"u1", "u2"}


# ------------------------------------------------------------------
# rename
# ------------------------------------------------------------------

@rsps_lib.activate
def test_rename_success(tool):
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/get_memory_by_key",
        json=_memory_data("uuid-1", "the content"),
        status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/add",
        json=_add_response(), status=200,
    )
    rsps_lib.add(
        rsps_lib.POST, f"{BASE}/product/delete_memory",
        json=_wrap({"deleted": 1}), status=200,
    )
    cmd = BetaMemoryTool20250818RenameCommand(
        command="rename",
        old_path="/memories/old.txt",
        new_path="/memories/new.txt",
    )
    result = tool.rename(cmd)
    assert "Successfully renamed" in result

    add_body = json.loads(rsps_lib.calls[1].request.body)
    assert add_body["key"] == "/memories/new.txt"
    assert add_body["messages"][0]["content"] == "the content"

    del_body = json.loads(rsps_lib.calls[2].request.body)
    assert "uuid-1" in del_body["memory_ids"]
