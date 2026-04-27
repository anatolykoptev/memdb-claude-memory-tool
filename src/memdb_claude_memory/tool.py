"""MemDB backend for the Anthropic Claude memory tool (memory_20250818).

Drop-in replacement for ``BetaLocalFilesystemMemoryTool``.
"""

from __future__ import annotations

from anthropic.lib.tools._beta_builtin_memory_tool import (
    BetaAbstractMemoryTool,
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818RenameCommand,
    BetaMemoryTool20250818StrReplaceCommand,
    BetaMemoryTool20250818ViewCommand,
    ToolError,
)
from anthropic.lib.tools import BetaFunctionToolResultType

from .http_client import MemDBClient, MemDBError
from .path_utils import PathError, is_directory_path, validate_path
from .formatters import format_dir_view, format_file_view, format_str_replace_snippet


class MemDBMemoryTool(BetaAbstractMemoryTool):
    """MemDB-backed implementation of the Anthropic memory tool.

    Stores every memory file as a single MemDB node addressed by its path
    (the ``key`` field introduced in MemDB Phase 1). This gives you
    Postgres+vector persistence, multi-tenant isolation, and semantic
    search as a bonus — all behind the same six-method interface Claude
    already knows.

    Args:
        memdb_url: Base URL of the MemDB HTTP API (e.g. ``http://localhost:8080``).
        cube_id: MemDB cube identifier — the logical namespace for this agent.
            Use one cube per user for multi-tenant deployments.
        user_id: MemDB user_id. Typically the same as ``cube_id``.
        service_secret: Value for the ``X-Service-Secret`` header. Required when
            ``AUTH_ENABLED=true`` in MemDB. Leave empty for default (no-auth) mode.
        timeout: HTTP timeout in seconds for each MemDB call.
    """

    def __init__(
        self,
        memdb_url: str = "http://localhost:8080",
        cube_id: str = "default",
        user_id: str | None = None,
        service_secret: str = "",
        timeout: int = 10,
    ) -> None:
        super().__init__()
        self.cube_id = cube_id
        self.user_id = user_id if user_id is not None else cube_id
        self._client = MemDBClient(
            base_url=memdb_url,
            service_secret=service_secret,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _vpath(self, path: str) -> str:
        """Validate path; raise ToolError on violation."""
        try:
            return validate_path(path)
        except PathError as exc:
            raise ToolError(str(exc)) from exc

    def _fetch_memory(self, path: str) -> tuple[str, str]:
        """Return (memory_id, text) for the given path or raise ToolError on 404."""
        data = self._client.get_memory_by_key(self.cube_id, self.user_id, path)
        if data is None:
            raise ToolError(f"The path {path} does not exist. Please provide a valid path.")
        memory_id: str = data.get("memory_id", "")
        props = data.get("properties", {})
        text: str = props.get("memory", "") if isinstance(props, dict) else ""
        return memory_id, text

    # ------------------------------------------------------------------
    # BetaAbstractMemoryTool interface
    # ------------------------------------------------------------------

    def view(self, command: BetaMemoryTool20250818ViewCommand) -> BetaFunctionToolResultType:
        """View file content with line numbers, or list a directory."""
        path = self._vpath(command.path)

        if is_directory_path(path):
            # Directory listing: list_memories_by_prefix
            prefix = path if path.endswith("/") else path + "/"
            # Special case: /memories root itself
            if path == "/memories":
                prefix = "/memories"
            try:
                items = self._client.list_memories_by_prefix(
                    self.cube_id, self.user_id, prefix
                )
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
            return format_dir_view(path, items)
        else:
            # File view
            try:
                _, text = self._fetch_memory(path)
            except ToolError:
                # Re-raise as-is
                raise
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
            return format_file_view(path, text, command.view_range)

    def create(self, command: BetaMemoryTool20250818CreateCommand) -> BetaFunctionToolResultType:
        """Create a new memory file (overwrite if exists)."""
        path = self._vpath(command.path)
        try:
            self._client.add_with_key(
                user_id=self.user_id,
                cube_id=self.cube_id,
                key=path,
                text=command.file_text,
            )
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc
        return f"File created successfully at: {path}"

    def str_replace(self, command: BetaMemoryTool20250818StrReplaceCommand) -> BetaFunctionToolResultType:
        """Atomic string replacement inside a memory file."""
        path = self._vpath(command.path)
        try:
            memory_id, text = self._fetch_memory(path)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        count = text.count(command.old_str)
        if count == 0:
            raise ToolError(
                f"No replacement was performed, old_str `{command.old_str}` "
                f"did not appear verbatim in {path}."
            )
        if count > 1:
            matching_lines: list[int] = []
            start = 0
            while True:
                pos = text.find(command.old_str, start)
                if pos == -1:
                    break
                matching_lines.append(text[:pos].count("\n") + 1)
                start = pos + 1
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str "
                f"`{command.old_str}` in lines: {', '.join(map(str, matching_lines))}. "
                "Please ensure it is unique"
            )

        pos = text.find(command.old_str)
        changed_line_index = text[:pos].count("\n")
        new_text = text.replace(command.old_str, command.new_str, 1)

        try:
            self._client.update_memory(memory_id, new_text)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        return format_str_replace_snippet(path, new_text, changed_line_index)

    def insert(self, command: BetaMemoryTool20250818InsertCommand) -> BetaFunctionToolResultType:
        """Insert text after a given line number (0 = top)."""
        path = self._vpath(command.path)
        try:
            memory_id, text = self._fetch_memory(path)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        lines = text.splitlines()
        if command.insert_line < 0 or command.insert_line > len(lines):
            raise ToolError(
                f"Invalid `insert_line` parameter: {command.insert_line}. "
                f"It should be within the range [0, {len(lines)}]."
            )

        lines.insert(command.insert_line, command.insert_text.rstrip("\n"))
        new_text = "\n".join(lines)
        if not new_text.endswith("\n"):
            new_text += "\n"

        try:
            self._client.update_memory(memory_id, new_text)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        return f"The file {path} has been edited."

    def delete(self, command: BetaMemoryTool20250818DeleteCommand) -> BetaFunctionToolResultType:
        """Delete a memory file or recursively delete a directory."""
        path = self._vpath(command.path)

        if path == "/memories":
            raise ToolError("Cannot delete the /memories directory itself")

        if is_directory_path(path):
            # Directory delete: batch delete all matching memories
            prefix = path if path.endswith("/") else path + "/"
            try:
                items = self._client.list_memories_by_prefix(
                    self.cube_id, self.user_id, prefix, limit=1000
                )
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
            if not items:
                raise ToolError(f"The path {path} does not exist")
            memory_ids = [item["id"] for item in items]
            try:
                self._client.delete_memories(memory_ids, self.cube_id)
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
        else:
            try:
                memory_id, _ = self._fetch_memory(path)
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
            try:
                self._client.delete_memories([memory_id], self.cube_id)
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc

        return f"Successfully deleted {path}"

    def rename(self, command: BetaMemoryTool20250818RenameCommand) -> BetaFunctionToolResultType:
        """Move a memory file to a new path.

        Note: NOT atomic. Implemented as create-at-new + delete-at-old.
        A future MemDB endpoint (PATCH properties.key) will make this atomic.
        """
        old_path = self._vpath(command.old_path)
        new_path = self._vpath(command.new_path)

        # Read existing content
        try:
            old_id, text = self._fetch_memory(old_path)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        # Write at new path
        try:
            self._client.add_with_key(
                user_id=self.user_id,
                cube_id=self.cube_id,
                key=new_path,
                text=text,
            )
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        # Delete old
        try:
            self._client.delete_memories([old_id], self.cube_id)
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc

        return f"Successfully renamed {old_path} to {new_path}"

    def clear_all_memory(self) -> BetaFunctionToolResultType:
        """Delete all memories in this tool's cube."""
        try:
            items = self._client.list_memories_by_prefix(
                self.cube_id, self.user_id, "/memories", limit=1000
            )
        except MemDBError as exc:
            raise ToolError(str(exc)) from exc
        if items:
            memory_ids = [item["id"] for item in items]
            try:
                self._client.delete_memories(memory_ids, self.cube_id)
            except MemDBError as exc:
                raise ToolError(str(exc)) from exc
        return "All memory cleared"
