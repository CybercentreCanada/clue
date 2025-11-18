from pathlib import Path

from clue.security.utils import is_path_traversal

ROOT_PATH = Path("/tmp")


def test_path_traversal_safe_paths():
    """Test that safe paths within the root are correctly identified as not being path traversal"""
    # Direct child
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH / "example")

    # Nested children
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH / "example" / "subdir")
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH / "a" / "b" / "c" / "d")

    # Root path itself
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH)

    # Using string paths
    assert not is_path_traversal("/tmp", "/tmp/example")
    assert not is_path_traversal("/tmp", "/tmp/example/subdir")


def test_path_traversal_basic_parent_directory():
    """Test basic parent directory traversal attempts"""
    # Single parent directory
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / "..")
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / "../example")

    # Multiple parent directories
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / ".." / "..")
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / ".." / ".." / "etc")

    # Using string paths
    assert is_path_traversal("/tmp", "/tmp/../etc")
    assert is_path_traversal("/tmp", "/tmp/../../etc")


def test_path_traversal_mixed_navigation():
    """Test path traversal with mixed forward and backward navigation"""
    # Go down then up and out
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / "subdir" / ".." / "..")
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / "a" / "b" / ".." / ".." / "..")

    # Complex mixed paths that escape
    assert is_path_traversal(ROOT_PATH, ROOT_PATH / "subdir" / ".." / ".." / "etc")


def test_path_traversal_absolute_paths():
    """Test absolute paths that are outside the root"""
    # Absolute paths outside root
    assert is_path_traversal(ROOT_PATH, Path("/etc"))
    assert is_path_traversal(ROOT_PATH, Path("/etc/passwd"))
    assert is_path_traversal(ROOT_PATH, Path("/home"))
    assert is_path_traversal(ROOT_PATH, Path("/var/log"))

    # Using string paths
    assert is_path_traversal("/tmp", "/etc/passwd")
    assert is_path_traversal("/tmp", "/home/user")


def test_path_traversal_symlink_style():
    """Test paths that would resolve to locations outside root (simulated)"""
    # After resolution, these should be detected
    # Path that resolves to parent
    assert is_path_traversal("/tmp/subdir", "/tmp")

    # Paths with redundant separators (normalized during resolve)
    assert not is_path_traversal("/tmp", "/tmp//example")
    assert not is_path_traversal("/tmp", "/tmp/./example")


def test_path_traversal_edge_cases():
    """Test edge cases and special scenarios"""
    # Empty-ish paths components
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH / ".")

    # Root vs non-root
    assert is_path_traversal("/tmp/specific", "/tmp/other")
    assert is_path_traversal("/tmp/specific", "/tmp")

    # Different roots entirely
    assert is_path_traversal("/tmp", "/var")


def test_path_traversal_string_and_path_mix():
    """Test mixing string and Path object inputs"""
    # String root, Path unsafe
    assert not is_path_traversal("/tmp", Path("/tmp/example"))
    assert is_path_traversal("/tmp", Path("/etc"))

    # Path root, string unsafe
    assert not is_path_traversal(Path("/tmp"), "/tmp/example")
    assert is_path_traversal(Path("/tmp"), "/etc")

    # Both strings
    assert not is_path_traversal("/tmp", "/tmp/example")
    assert is_path_traversal("/tmp", "/etc")


def test_path_traversal_url_encoded_attempts():
    """Test URL-encoded or obfuscated path traversal attempts"""
    # Note: Path.resolve() normalizes these, so they should be caught
    # Paths with . and .. are normalized
    assert is_path_traversal("/tmp", "/tmp/subdir/../..")

    # Multiple slashes are normalized
    assert not is_path_traversal("/tmp", "/tmp///example")


def test_path_traversal_windows_style_paths():
    """Test Windows-style path separators (if applicable on the system)"""
    # On Unix systems, backslashes are treated as regular characters in filenames
    # But we should still test the behavior
    assert not is_path_traversal(ROOT_PATH, ROOT_PATH / "example\\subdir")


def test_path_traversal_deeply_nested():
    """Test deeply nested paths both safe and unsafe"""
    # Safe deep nesting
    deep_safe = ROOT_PATH / "a" / "b" / "c" / "d" / "e" / "f" / "g"
    assert not is_path_traversal(ROOT_PATH, deep_safe)

    # Deep nesting that escapes
    deep_unsafe = ROOT_PATH / "a" / "b" / "c" / ".." / ".." / ".." / ".."
    assert is_path_traversal(ROOT_PATH, deep_unsafe)
