"""Anthropic-style output formatters for the MemDB memory tool adapter.

Format rules mirror ``BetaLocalFilesystemMemoryTool`` so Claude's trained
expectations are met exactly.
"""

from __future__ import annotations

from typing import List, Tuple

_LINE_NUMBER_WIDTH = 6  # matches SDK constant


def format_file_view(path: str, text: str, view_range: list[int] | None = None) -> str:
    """Format file content with line numbers.

    Matches the SDK output::

        Here's the content of /memories/foo.txt with line numbers:
             1\tline one
             2\tline two
    """
    lines = text.split("\n")
    start_num = 1

    if view_range and len(view_range) == 2:
        start = max(1, view_range[0]) - 1
        end = len(lines) if view_range[1] == -1 else view_range[1]
        lines = lines[start:end]
        start_num = start + 1

    numbered = [
        f"{str(i + start_num).rjust(_LINE_NUMBER_WIDTH)}\t{line}"
        for i, line in enumerate(lines)
    ]
    return f"Here's the content of {path} with line numbers:\n" + "\n".join(numbered)


def format_dir_view(path: str, items: list[dict]) -> str:
    """Format directory listing in du-style.

    ``items`` is a list of dicts with keys: ``key`` (str), ``char_size`` (int).

    Output format::

        Here's the files and directories up to 2 levels deep in /memories,
        excluding hidden items:

        4096\t/memories
        124\t/memories/users/alice/prefs.txt
    """
    header = (
        f"Here's the files and directories up to 2 levels deep in {path}, "
        "excluding hidden items:"
    )
    lines = [f"0\t{path}"]
    for item in items:
        key: str = item.get("key", "")
        char_size: int = item.get("char_size", 0)
        if key.startswith("/"):
            full_path = key
        else:
            full_path = key  # already absolute key stored by MemDB
        lines.append(f"{char_size}\t{full_path}")
    return header + "\n\n" + "\n".join(lines)


def format_str_replace_snippet(path: str, new_text: str, changed_line_index: int) -> str:
    """Return the edited-region snippet message."""
    new_lines = new_text.split("\n")
    context_start = max(0, changed_line_index - 2)
    context_end = min(len(new_lines), changed_line_index + 3)
    snippet = [
        f"{str(line_num).rjust(_LINE_NUMBER_WIDTH)}\t{new_lines[line_num - 1]}"
        for line_num in range(context_start + 1, context_end + 1)
    ]
    return (
        "The memory file has been edited. Here is the snippet showing the change "
        "(with line numbers):\n" + "\n".join(snippet)
    )
