"""Tests for path_utils module."""

import pytest

from memdb_claude_memory.path_utils import (
    PathError,
    is_directory_path,
    validate_path,
)


class TestValidatePath:
    def test_valid_file_path(self):
        assert validate_path("/memories/foo.txt") == "/memories/foo.txt"

    def test_valid_dir_path(self):
        assert validate_path("/memories/users/") == "/memories/users/"

    def test_valid_root(self):
        assert validate_path("/memories") == "/memories"

    def test_rejects_no_prefix(self):
        with pytest.raises(PathError, match="must start with /memories"):
            validate_path("/tmp/foo.txt")

    def test_rejects_tilde(self):
        with pytest.raises(PathError, match="must not contain ~"):
            validate_path("/memories/~/foo.txt")

    def test_rejects_nul(self):
        with pytest.raises(PathError, match="NUL"):
            validate_path("/memories/foo\x00bar")

    def test_rejects_dotdot(self):
        with pytest.raises(PathError, match=r"\.\."):
            validate_path("/memories/../etc/passwd")

    def test_rejects_too_long(self):
        long_path = "/memories/" + "a" * 510
        with pytest.raises(PathError, match="exceeds maximum"):
            validate_path(long_path)

    def test_max_length_ok(self):
        path = "/memories/" + "a" * 502  # 10 + 502 = 512
        assert len(path) == 512
        assert validate_path(path) == path


class TestIsDirectoryPath:
    def test_trailing_slash(self):
        assert is_directory_path("/memories/users/") is True

    def test_no_extension(self):
        assert is_directory_path("/memories/users") is True

    def test_root(self):
        assert is_directory_path("/memories") is True

    def test_file_with_extension(self):
        assert is_directory_path("/memories/users/alice.txt") is False

    def test_deep_file(self):
        assert is_directory_path("/memories/a/b/c/notes.md") is False

    def test_deep_dir(self):
        assert is_directory_path("/memories/a/b/c") is True
