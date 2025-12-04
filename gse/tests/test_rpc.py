"""
Unit tests for RPC client.

Tests RPC message construction and parsing (without actual connection).
"""

import pytest
import struct
from unittest.mock import Mock, MagicMock, patch
from gse.rpc_client import RPCClient, RPC_CALL, RPC_REPLY, MSG_ACCEPTED, SUCCESS
from gse.exceptions import RPCError, ConnectionError as GSEConnectionError


class TestRPCClient:
    """Test RPC client functionality."""

    def test_init(self):
        """Test RPC client initialization."""
        client = RPCClient('10.1.0.123', 9800, timeout=5.0)
        assert client.host == '10.1.0.123'
        assert client.port == 9800
        assert client.timeout == 5.0
        assert client.xid == 0
        assert not client.is_connected()

    def test_build_call_message(self):
        """Test RPC call message construction."""
        client = RPCClient('10.1.0.123', 9800)

        # Build a simple call message
        msg = client._build_call_message(
            xid=1,
            program=0x20000001,
            version=1,
            procedure=85,
            args=b'\x00\x00\x00\x05hello',  # XDR string
            auth_flavor=0,
            auth_data=b''
        )

        # Parse message header
        offset = 0

        # XID
        xid = struct.unpack_from('>I', msg, offset)[0]
        assert xid == 1
        offset += 4

        # Message type (CALL)
        msg_type = struct.unpack_from('>I', msg, offset)[0]
        assert msg_type == RPC_CALL
        offset += 4

        # RPC version
        rpc_vers = struct.unpack_from('>I', msg, offset)[0]
        assert rpc_vers == 2
        offset += 4

        # Program
        prog = struct.unpack_from('>I', msg, offset)[0]
        assert prog == 0x20000001
        offset += 4

        # Version
        vers = struct.unpack_from('>I', msg, offset)[0]
        assert vers == 1
        offset += 4

        # Procedure
        proc = struct.unpack_from('>I', msg, offset)[0]
        assert proc == 85

    def test_parse_reply_success(self):
        """Test parsing successful RPC reply."""
        client = RPCClient('10.1.0.123', 9800)

        # Construct a successful reply message
        reply = bytearray()
        reply.extend(struct.pack('>I', 1))  # XID
        reply.extend(struct.pack('>I', RPC_REPLY))  # Message type
        reply.extend(struct.pack('>I', MSG_ACCEPTED))  # Reply status
        reply.extend(struct.pack('>I', 0))  # Verifier flavor
        reply.extend(struct.pack('>I', 0))  # Verifier length
        reply.extend(struct.pack('>I', SUCCESS))  # Accept status
        reply.extend(b'result_data')  # Result

        result = client._parse_reply(bytes(reply), expected_xid=1)
        assert result == b'result_data'

    def test_parse_reply_xid_mismatch(self):
        """Test parsing reply with mismatched XID."""
        client = RPCClient('10.1.0.123', 9800)

        reply = bytearray()
        reply.extend(struct.pack('>I', 999))  # Wrong XID
        reply.extend(struct.pack('>I', RPC_REPLY))

        with pytest.raises(RPCError, match="XID mismatch"):
            client._parse_reply(bytes(reply), expected_xid=1)

    def test_xid_increment(self):
        """Test XID increments on each call."""
        client = RPCClient('10.1.0.123', 9800)
        client._connected = True  # Pretend connected
        client.sock = Mock()

        assert client.xid == 0

        # Create a proper reply
        reply_data = _create_success_reply(1)

        # Mock socket operations to return proper fragments
        client.sock.sendall = Mock()
        client.sock.recv = Mock(side_effect=[
            struct.pack('>I', 0x80000000 | len(reply_data)),  # Fragment header with last bit
            reply_data  # Reply data
        ])

        # Make call
        result = client.call(0x20000001, 1, 85, b'')

        # XID should have incremented
        assert client.xid == 1


class TestRPCMessageFragmentation:
    """Test RPC record marking and fragmentation."""

    def test_send_fragment_last(self):
        """Test sending last fragment."""
        client = RPCClient('10.1.0.123', 9800)
        client.sock = Mock()

        data = b'test_data'
        client._send_fragment(data, last=True)

        # Check that sendall was called with proper record marking
        calls = client.sock.sendall.call_args_list
        assert len(calls) == 1

        sent_data = calls[0][0][0]
        header = struct.unpack('>I', sent_data[:4])[0]

        # High bit should be set for last fragment
        assert header & 0x80000000 != 0
        # Length should match data length
        assert (header & 0x7FFFFFFF) == len(data)
        # Data should follow header
        assert sent_data[4:] == data

    def test_send_fragment_not_last(self):
        """Test sending non-last fragment."""
        client = RPCClient('10.1.0.123', 9800)
        client.sock = Mock()

        data = b'test_data'
        client._send_fragment(data, last=False)

        calls = client.sock.sendall.call_args_list
        sent_data = calls[0][0][0]
        header = struct.unpack('>I', sent_data[:4])[0]

        # High bit should NOT be set for non-last fragment
        assert header & 0x80000000 == 0


def _create_success_reply(xid: int) -> bytes:
    """Helper to create a successful RPC reply message."""
    reply = bytearray()
    reply.extend(struct.pack('>I', xid))
    reply.extend(struct.pack('>I', RPC_REPLY))
    reply.extend(struct.pack('>I', MSG_ACCEPTED))
    reply.extend(struct.pack('>I', 0))  # Verifier flavor
    reply.extend(struct.pack('>I', 0))  # Verifier length
    reply.extend(struct.pack('>I', SUCCESS))
    return bytes(reply)


@pytest.mark.skipif(True, reason="Requires running simulator")
class TestRPCClientIntegration:
    """Integration tests requiring actual simulator connection.

    These tests are skipped by default. To run them, change the skipif
    condition and ensure the simulator is running at 10.1.0.123:9800.
    """

    def test_connect(self):
        """Test actual connection to GDA server."""
        client = RPCClient('10.1.0.123', 9800)
        client.connect()
        assert client.is_connected()
        client.disconnect()
        assert not client.is_connected()

    def test_simple_call(self):
        """Test simple RPC call to simulator."""
        client = RPCClient('10.1.0.123', 9800)
        client.connect()

        try:
            # Encode variable name
            from gse.xdr import encode_xdr_string
            args = encode_xdr_string('RCS01POWER')

            # Make call
            response = client.call(
                program=0x20000001,
                version=1,
                procedure=85,  # CALLget
                args=args
            )

            # Should get a response
            assert len(response) > 0

        finally:
            client.disconnect()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
