"""Tests for Anthropic-style output formatters."""

import pytest
from memdb_claude_memory.formatters import (
    format_dir_view,
    format_file_view,
    format_str_replace_snippet,
)


class TestFormatFileView:
    def test_basic_line_numbers(self):
        result = format_file_view("/memories/foo.txt", "line one\nline two\nline three")
        assert "Here's the content of /memories/foo.txt with line numbers:" in result
        assert "\t1\t" not in result  # no leading tab before number
        assert "1\tline one" in result
        assert "2\tline two" in result
        assert "3\tline three" in result

    def test_view_range(self):
        text = "a\nb\nc\nd\ne"
        result = format_file_view("/memories/f.txt", text, view_range=[2, 4])
        assert "2\tb" in result
        assert "3\tc" in result
        assert "4\td" in result
        assert "1\ta" not in result
        assert "5\te" not in result

    def test_view_range_minus_one_end(self):
        text = "a\nb\nc"
        result = format_file_view("/memories/f.txt", text, view_range=[2, -1])
        assert "2\tb" in result
        assert "3\tc" in result
        assert "1\ta" not in result

    def test_empty_file(self):
        result = format_file_view("/memories/empty.txt", "")
        assert "Here's the content of /memories/empty.txt with line numbers:" in result
        assert "1\t" in result


class TestFormatDirView:
    def test_empty_dir(self):
        result = format_dir_view("/memories", [])
        assert "Here's the files and directories up to 2 levels deep in /memories" in result
        assert "excluding hidden items" in result

    def test_with_items(self):
        items = [
            {"key": "/memories/users/alice.txt", "char_size": 124},
            {"key": "/memories/users/bob.txt", "char_size": 89},
        ]
        result = format_dir_view("/memories/users", items)
        assert "/memories/users/alice.txt" in result
        assert "124" in result
        assert "/memories/users/bob.txt" in result
        assert "89" in result


class TestFormatStrReplaceSnippet:
    def test_snippet_around_change(self):
        new_text = "line1\nline2\nchanged\nline4\nline5"
        # changed_line_index = 2 (0-based), so line 3
        result = format_str_replace_snippet("/memories/f.txt", new_text, 2)
        assert "The memory file has been edited" in result
        assert "changed" in result

    def test_snippet_at_top(self):
        new_text = "changed\nline2\nline3"
        result = format_str_replace_snippet("/memories/f.txt", new_text, 0)
        assert "changed" in result
        assert "The memory file has been edited" in result
