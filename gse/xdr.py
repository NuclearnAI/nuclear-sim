"""
XDR (External Data Representation) encoding and decoding.

Implements the XDR standard (RFC 4506) for data serialization in RPC calls.
All data is encoded in big-endian format with 4-byte alignment.
"""

import struct
from typing import Tuple, List, Any
from gse.exceptions import XDRError


class XDREncoder:
    """XDR encoder for serializing data to network format."""

    def __init__(self):
        self.buffer = bytearray()

    def encode_int(self, value: int) -> None:
        """Encode a signed 32-bit integer.

        Args:
            value: Integer value to encode
        """
        self.buffer.extend(struct.pack('>i', value))

    def encode_uint(self, value: int) -> None:
        """Encode an unsigned 32-bit integer.

        Args:
            value: Unsigned integer value to encode
        """
        self.buffer.extend(struct.pack('>I', value))

    def encode_long(self, value: int) -> None:
        """Encode a signed 64-bit long.

        Args:
            value: Long value to encode
        """
        self.buffer.extend(struct.pack('>q', value))

    def encode_ulong(self, value: int) -> None:
        """Encode an unsigned 64-bit long.

        Args:
            value: Unsigned long value to encode
        """
        self.buffer.extend(struct.pack('>Q', value))

    def encode_short(self, value: int) -> None:
        """Encode a signed 16-bit short as 32-bit int (XDR has no short).

        Args:
            value: Short value to encode
        """
        self.encode_int(value)

    def encode_ushort(self, value: int) -> None:
        """Encode an unsigned 16-bit short as 32-bit uint.

        Args:
            value: Unsigned short value to encode
        """
        self.encode_uint(value)

    def encode_float(self, value: float) -> None:
        """Encode a 32-bit float.

        Args:
            value: Float value to encode
        """
        self.buffer.extend(struct.pack('>f', value))

    def encode_double(self, value: float) -> None:
        """Encode a 64-bit double.

        Args:
            value: Double value to encode
        """
        self.buffer.extend(struct.pack('>d', value))

    def encode_bool(self, value: bool) -> None:
        """Encode a boolean as integer (0 or 1).

        Args:
            value: Boolean value to encode
        """
        self.encode_int(1 if value else 0)

    def encode_string(self, value: str) -> None:
        """Encode a string with length prefix and padding.

        Args:
            value: String to encode
        """
        if value is None:
            value = ""

        b = value.encode('utf-8')
        length = len(b)
        padding = (4 - (length % 4)) % 4

        self.encode_uint(length)
        self.buffer.extend(b)
        self.buffer.extend(b'\x00' * padding)

    def encode_bytes(self, value: bytes) -> None:
        """Encode opaque bytes with length prefix and padding.

        Args:
            value: Bytes to encode
        """
        if value is None:
            value = b''

        length = len(value)
        padding = (4 - (length % 4)) % 4

        self.encode_uint(length)
        self.buffer.extend(value)
        self.buffer.extend(b'\x00' * padding)

    def encode_fixed_bytes(self, value: bytes, length: int) -> None:
        """Encode fixed-length opaque bytes with padding.

        Args:
            value: Bytes to encode
            length: Expected length
        """
        if len(value) != length:
            raise XDRError(f"Expected {length} bytes, got {len(value)}")

        padding = (4 - (length % 4)) % 4
        self.buffer.extend(value)
        self.buffer.extend(b'\x00' * padding)

    def encode_array(self, values: List[Any], encoder_func) -> None:
        """Encode a variable-length array.

        Args:
            values: List of values to encode
            encoder_func: Function to encode each element
        """
        self.encode_uint(len(values))
        for value in values:
            encoder_func(value)

    def get_bytes(self) -> bytes:
        """Get the encoded bytes.

        Returns:
            Encoded data as bytes
        """
        return bytes(self.buffer)

    def reset(self) -> None:
        """Reset the encoder buffer."""
        self.buffer = bytearray()


class XDRDecoder:
    """XDR decoder for deserializing data from network format."""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def decode_int(self) -> int:
        """Decode a signed 32-bit integer.

        Returns:
            Decoded integer value
        """
        if self.offset + 4 > len(self.data):
            raise XDRError("Not enough data to decode int")

        value = struct.unpack_from('>i', self.data, self.offset)[0]
        self.offset += 4
        return value

    def decode_uint(self) -> int:
        """Decode an unsigned 32-bit integer.

        Returns:
            Decoded unsigned integer value
        """
        if self.offset + 4 > len(self.data):
            raise XDRError("Not enough data to decode uint")

        value = struct.unpack_from('>I', self.data, self.offset)[0]
        self.offset += 4
        return value

    def decode_long(self) -> int:
        """Decode a signed 64-bit long.

        Returns:
            Decoded long value
        """
        if self.offset + 8 > len(self.data):
            raise XDRError("Not enough data to decode long")

        value = struct.unpack_from('>q', self.data, self.offset)[0]
        self.offset += 8
        return value

    def decode_ulong(self) -> int:
        """Decode an unsigned 64-bit long.

        Returns:
            Decoded unsigned long value
        """
        if self.offset + 8 > len(self.data):
            raise XDRError("Not enough data to decode ulong")

        value = struct.unpack_from('>Q', self.data, self.offset)[0]
        self.offset += 8
        return value

    def decode_short(self) -> int:
        """Decode a 16-bit short (stored as 32-bit int in XDR).

        Returns:
            Decoded short value
        """
        return self.decode_int()

    def decode_ushort(self) -> int:
        """Decode an unsigned 16-bit short.

        Returns:
            Decoded unsigned short value
        """
        return self.decode_uint()

    def decode_float(self) -> float:
        """Decode a 32-bit float.

        Returns:
            Decoded float value
        """
        if self.offset + 4 > len(self.data):
            raise XDRError("Not enough data to decode float")

        value = struct.unpack_from('>f', self.data, self.offset)[0]
        self.offset += 4
        return value

    def decode_double(self) -> float:
        """Decode a 64-bit double.

        Returns:
            Decoded double value
        """
        if self.offset + 8 > len(self.data):
            raise XDRError("Not enough data to decode double")

        value = struct.unpack_from('>d', self.data, self.offset)[0]
        self.offset += 8
        return value

    def decode_bool(self) -> bool:
        """Decode a boolean (stored as integer).

        Returns:
            Decoded boolean value
        """
        return self.decode_int() != 0

    def decode_string(self) -> str:
        """Decode a string with length prefix.

        Returns:
            Decoded string
        """
        length = self.decode_uint()

        if self.offset + length > len(self.data):
            raise XDRError(f"Not enough data to decode string of length {length}")

        s = self.data[self.offset:self.offset + length].decode('utf-8')
        self.offset += length

        # Skip padding
        padding = (4 - (length % 4)) % 4
        self.offset += padding

        return s

    def decode_bytes(self) -> bytes:
        """Decode opaque bytes with length prefix.

        Returns:
            Decoded bytes
        """
        length = self.decode_uint()

        if self.offset + length > len(self.data):
            raise XDRError(f"Not enough data to decode bytes of length {length}")

        b = self.data[self.offset:self.offset + length]
        self.offset += length

        # Skip padding
        padding = (4 - (length % 4)) % 4
        self.offset += padding

        return b

    def decode_fixed_bytes(self, length: int) -> bytes:
        """Decode fixed-length opaque bytes.

        Args:
            length: Expected length

        Returns:
            Decoded bytes
        """
        if self.offset + length > len(self.data):
            raise XDRError(f"Not enough data to decode fixed bytes of length {length}")

        b = self.data[self.offset:self.offset + length]
        self.offset += length

        # Skip padding
        padding = (4 - (length % 4)) % 4
        self.offset += padding

        return b

    def decode_array(self, decoder_func) -> List[Any]:
        """Decode a variable-length array.

        Args:
            decoder_func: Function to decode each element

        Returns:
            List of decoded values
        """
        length = self.decode_uint()
        return [decoder_func() for _ in range(length)]

    def remaining(self) -> int:
        """Get number of remaining bytes.

        Returns:
            Number of unread bytes
        """
        return len(self.data) - self.offset

    def get_remaining_bytes(self) -> bytes:
        """Get all remaining bytes.

        Returns:
            Remaining unread bytes
        """
        return self.data[self.offset:]


# Convenience functions
def encode_xdr_string(s: str) -> bytes:
    """Encode a string to XDR format.

    Args:
        s: String to encode

    Returns:
        XDR-encoded bytes
    """
    encoder = XDREncoder()
    encoder.encode_string(s)
    return encoder.get_bytes()


def decode_xdr_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Decode a string from XDR format.

    Args:
        data: XDR-encoded data
        offset: Starting offset

    Returns:
        Tuple of (decoded string, new offset)
    """
    decoder = XDRDecoder(data[offset:])
    s = decoder.decode_string()
    return s, offset + decoder.offset
