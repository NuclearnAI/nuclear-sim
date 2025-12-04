"""
Unit tests for XDR encoding/decoding.

Tests the XDR serialization implementation for correctness and edge cases.
"""

import pytest
import struct
from gse.xdr import XDREncoder, XDRDecoder, encode_xdr_string, decode_xdr_string
from gse.exceptions import XDRError


class TestXDREncoder:
    """Test XDR encoding functionality."""

    def test_encode_int(self):
        """Test integer encoding."""
        encoder = XDREncoder()
        encoder.encode_int(42)
        assert encoder.get_bytes() == struct.pack('>i', 42)

    def test_encode_uint(self):
        """Test unsigned integer encoding."""
        encoder = XDREncoder()
        encoder.encode_uint(12345)
        assert encoder.get_bytes() == struct.pack('>I', 12345)

    def test_encode_long(self):
        """Test long encoding."""
        encoder = XDREncoder()
        encoder.encode_long(9876543210)
        assert encoder.get_bytes() == struct.pack('>q', 9876543210)

    def test_encode_float(self):
        """Test float encoding."""
        encoder = XDREncoder()
        encoder.encode_float(3.14159)
        assert encoder.get_bytes() == struct.pack('>f', 3.14159)

    def test_encode_double(self):
        """Test double encoding."""
        encoder = XDREncoder()
        encoder.encode_double(2.71828)
        assert encoder.get_bytes() == struct.pack('>d', 2.71828)

    def test_encode_bool(self):
        """Test boolean encoding."""
        encoder = XDREncoder()
        encoder.encode_bool(True)
        assert encoder.get_bytes() == struct.pack('>i', 1)

        encoder.reset()
        encoder.encode_bool(False)
        assert encoder.get_bytes() == struct.pack('>i', 0)

    def test_encode_string(self):
        """Test string encoding with padding."""
        encoder = XDREncoder()
        encoder.encode_string("hello")

        # Length (4 bytes) + "hello" (5 bytes) + padding (3 bytes)
        expected = struct.pack('>I', 5) + b'hello' + b'\x00\x00\x00'
        assert encoder.get_bytes() == expected

    def test_encode_string_aligned(self):
        """Test string encoding when length is already aligned."""
        encoder = XDREncoder()
        encoder.encode_string("test")  # 4 bytes, no padding needed

        expected = struct.pack('>I', 4) + b'test'
        assert encoder.get_bytes() == expected

    def test_encode_empty_string(self):
        """Test empty string encoding."""
        encoder = XDREncoder()
        encoder.encode_string("")

        expected = struct.pack('>I', 0)
        assert encoder.get_bytes() == expected

    def test_encode_none_string(self):
        """Test None string encoding (should encode as empty)."""
        encoder = XDREncoder()
        encoder.encode_string(None)

        expected = struct.pack('>I', 0)
        assert encoder.get_bytes() == expected

    def test_encode_bytes(self):
        """Test bytes encoding."""
        encoder = XDREncoder()
        encoder.encode_bytes(b'\x01\x02\x03')

        # Length (4 bytes) + data (3 bytes) + padding (1 byte)
        expected = struct.pack('>I', 3) + b'\x01\x02\x03\x00'
        assert encoder.get_bytes() == expected

    def test_encode_multiple_values(self):
        """Test encoding multiple values."""
        encoder = XDREncoder()
        encoder.encode_int(42)
        encoder.encode_string("test")
        encoder.encode_float(3.14)

        data = encoder.get_bytes()
        assert len(data) == 4 + 8 + 4  # int + string_with_padding + float

    def test_reset(self):
        """Test encoder reset."""
        encoder = XDREncoder()
        encoder.encode_int(42)
        encoder.reset()
        assert len(encoder.get_bytes()) == 0


class TestXDRDecoder:
    """Test XDR decoding functionality."""

    def test_decode_int(self):
        """Test integer decoding."""
        data = struct.pack('>i', 42)
        decoder = XDRDecoder(data)
        assert decoder.decode_int() == 42

    def test_decode_uint(self):
        """Test unsigned integer decoding."""
        data = struct.pack('>I', 12345)
        decoder = XDRDecoder(data)
        assert decoder.decode_uint() == 12345

    def test_decode_long(self):
        """Test long decoding."""
        data = struct.pack('>q', 9876543210)
        decoder = XDRDecoder(data)
        assert decoder.decode_long() == 9876543210

    def test_decode_float(self):
        """Test float decoding."""
        data = struct.pack('>f', 3.14159)
        decoder = XDRDecoder(data)
        assert abs(decoder.decode_float() - 3.14159) < 1e-5

    def test_decode_double(self):
        """Test double decoding."""
        data = struct.pack('>d', 2.71828)
        decoder = XDRDecoder(data)
        assert abs(decoder.decode_double() - 2.71828) < 1e-10

    def test_decode_bool(self):
        """Test boolean decoding."""
        data = struct.pack('>i', 1)
        decoder = XDRDecoder(data)
        assert decoder.decode_bool() is True

        data = struct.pack('>i', 0)
        decoder = XDRDecoder(data)
        assert decoder.decode_bool() is False

    def test_decode_string(self):
        """Test string decoding."""
        data = struct.pack('>I', 5) + b'hello' + b'\x00\x00\x00'
        decoder = XDRDecoder(data)
        assert decoder.decode_string() == "hello"

    def test_decode_empty_string(self):
        """Test empty string decoding."""
        data = struct.pack('>I', 0)
        decoder = XDRDecoder(data)
        assert decoder.decode_string() == ""

    def test_decode_bytes(self):
        """Test bytes decoding."""
        data = struct.pack('>I', 3) + b'\x01\x02\x03\x00'
        decoder = XDRDecoder(data)
        assert decoder.decode_bytes() == b'\x01\x02\x03'

    def test_decode_multiple_values(self):
        """Test decoding multiple values."""
        encoder = XDREncoder()
        encoder.encode_int(42)
        encoder.encode_string("test")
        encoder.encode_float(3.14)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert decoder.decode_int() == 42
        assert decoder.decode_string() == "test"
        assert abs(decoder.decode_float() - 3.14) < 1e-5

    def test_decode_insufficient_data(self):
        """Test decoding with insufficient data."""
        data = b'\x00\x00'  # Only 2 bytes, need 4 for int
        decoder = XDRDecoder(data)
        with pytest.raises(XDRError):
            decoder.decode_int()

    def test_remaining(self):
        """Test remaining bytes calculation."""
        data = struct.pack('>I', 42) + struct.pack('>I', 99)
        decoder = XDRDecoder(data)

        assert decoder.remaining() == 8
        decoder.decode_uint()
        assert decoder.remaining() == 4
        decoder.decode_uint()
        assert decoder.remaining() == 0


class TestXDRRoundTrip:
    """Test encode/decode round-trip correctness."""

    def test_int_roundtrip(self):
        """Test int encode/decode round-trip."""
        encoder = XDREncoder()
        encoder.encode_int(-12345)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert decoder.decode_int() == -12345

    def test_string_roundtrip(self):
        """Test string encode/decode round-trip."""
        test_string = "Hello, World! 123"
        encoder = XDREncoder()
        encoder.encode_string(test_string)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert decoder.decode_string() == test_string

    def test_float_roundtrip(self):
        """Test float encode/decode round-trip."""
        encoder = XDREncoder()
        encoder.encode_float(1.23456)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert abs(decoder.decode_float() - 1.23456) < 1e-5

    def test_double_roundtrip(self):
        """Test double encode/decode round-trip."""
        encoder = XDREncoder()
        encoder.encode_double(1.234567890123)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert abs(decoder.decode_double() - 1.234567890123) < 1e-10

    def test_complex_roundtrip(self):
        """Test complex structure encode/decode round-trip."""
        encoder = XDREncoder()
        encoder.encode_int(42)
        encoder.encode_string("test")
        encoder.encode_float(3.14)
        encoder.encode_bool(True)
        encoder.encode_double(2.71828)
        data = encoder.get_bytes()

        decoder = XDRDecoder(data)
        assert decoder.decode_int() == 42
        assert decoder.decode_string() == "test"
        assert abs(decoder.decode_float() - 3.14) < 1e-5
        assert decoder.decode_bool() is True
        assert abs(decoder.decode_double() - 2.71828) < 1e-10


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_encode_xdr_string(self):
        """Test encode_xdr_string convenience function."""
        data = encode_xdr_string("hello")
        expected = struct.pack('>I', 5) + b'hello' + b'\x00\x00\x00'
        assert data == expected

    def test_decode_xdr_string(self):
        """Test decode_xdr_string convenience function."""
        data = struct.pack('>I', 5) + b'hello' + b'\x00\x00\x00'
        s, offset = decode_xdr_string(data)
        assert s == "hello"
        assert offset == 12  # 4 (length) + 5 (data) + 3 (padding)

    def test_decode_xdr_string_with_offset(self):
        """Test decode_xdr_string with offset."""
        prefix = b'\x00\x00\x00\x00'
        data = prefix + struct.pack('>I', 4) + b'test'
        s, offset = decode_xdr_string(data, offset=4)
        assert s == "test"
        assert offset == 12


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
