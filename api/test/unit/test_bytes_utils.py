from clue.common.bytes_utils import to_base64


class TestToBase64:
    """Test suite for to_base64 function."""

    def test_to_base64_simple_bytes(self):
        """Test encoding simple bytes to base64."""
        result = to_base64(b"hello")
        assert result == "aGVsbG8="

    def test_to_base64_empty_bytes(self):
        """Test encoding empty bytes."""
        result = to_base64(b"")
        assert result == ""

    def test_to_base64_with_special_characters(self):
        """Test encoding bytes with special characters."""
        result = to_base64(b"hello@world!")
        assert result == "aGVsbG9Ad29ybGQh"

    def test_to_base64_with_newlines(self):
        """Test encoding bytes containing newlines."""
        result = to_base64(b"hello\nworld")
        assert result == "aGVsbG8Kd29ybGQ="

    def test_to_base64_with_binary_data(self):
        """Test encoding binary data."""
        binary_data = bytes([0, 1, 2, 255, 254, 253])
        result = to_base64(binary_data)
        assert result == "AAEC/v79"

    def test_to_base64_utf8_encoding(self):
        """Test with explicit UTF-8 encoding."""
        result = to_base64(b"test", encoding="utf-8")
        assert result == "dGVzdA=="

    def test_to_base64_ascii_encoding(self):
        """Test with ASCII encoding."""
        result = to_base64(b"test", encoding="ascii")
        assert result == "dGVzdA=="

    def test_to_base64_large_data(self):
        """Test encoding large data."""
        large_data = b"x" * 10000
        result = to_base64(large_data)
        assert len(result) > 0
        assert isinstance(result, str)

    def test_to_base64_unicode_bytes(self):
        """Test encoding unicode text converted to bytes."""
        unicode_text = "héllo wørld".encode("utf-8")
        result = to_base64(unicode_text)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_to_base64_return_type(self):
        """Test that return type is always a string."""
        result = to_base64(b"test")
        assert isinstance(result, str)
