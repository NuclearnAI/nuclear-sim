"""
ONC RPC (Open Network Computing Remote Procedure Call) client implementation.

Implements the ONC RPC protocol (RFC 5531) over TCP with record marking (RFC 5532).
Handles message formatting, XID tracking, fragmentation, and error handling.
"""

import socket
import struct
import logging
from typing import Optional, Tuple
from gse.exceptions import RPCError, ConnectionError as GSEConnectionError, TimeoutError
from gse.xdr import XDREncoder, XDRDecoder

logger = logging.getLogger(__name__)


# RPC Message Types
RPC_CALL = 0
RPC_REPLY = 1

# RPC Version
RPC_VERSION = 2

# Reply Status
MSG_ACCEPTED = 0
MSG_DENIED = 1

# Accept Status
SUCCESS = 0
PROG_UNAVAIL = 1
PROG_MISMATCH = 2
PROC_UNAVAIL = 3
GARBAGE_ARGS = 4
SYSTEM_ERR = 5

# Reject Status
RPC_MISMATCH = 0
AUTH_ERROR = 1

# Auth Flavor
AUTH_NULL = 0
AUTH_UNIX = 1
AUTH_SHORT = 2
AUTH_DES = 3

# RPC Error Codes
RPC_SUCCESS = 0
RPC_CANTENCODEARGS = 1
RPC_CANTDECODERES = 2
RPC_CANTSEND = 3
RPC_CANTRECV = 4
RPC_TIMEDOUT = 5
RPC_VERSMISMATCH = 6
RPC_AUTHERROR = 7
RPC_PROGUNAVAIL = 8
RPC_PROGVERSMISMATCH = 9
RPC_PROCUNAVAIL = 10
RPC_CANTDECODEARGS = 11
RPC_SYSTEMERROR = 12


class RPCClient:
    """Low-level ONC RPC client over TCP.

    Handles RPC message construction, fragmentation, and response parsing.

    Attributes:
        host: Server hostname or IP address
        port: Server port number
        timeout: Socket timeout in seconds
    """

    def __init__(self, host: str, port: int, timeout: float = 10.0):
        """Initialize RPC client.

        Args:
            host: Server hostname or IP address
            port: Server port number
            timeout: Socket timeout in seconds (default: 10.0)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.xid = 0
        self._connected = False

    def connect(self) -> None:
        """Establish TCP connection to RPC server.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            self._connected = True
            logger.info(f"Connected to RPC server at {self.host}:{self.port}")
        except socket.error as e:
            raise GSEConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close connection to RPC server."""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
            finally:
                self.sock = None
                self._connected = False
                logger.info("Disconnected from RPC server")

    def is_connected(self) -> bool:
        """Check if connected to server.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.sock is not None

    def call(
        self,
        program: int,
        version: int,
        procedure: int,
        args: bytes,
        auth_flavor: int = AUTH_NULL,
        auth_data: bytes = b''
    ) -> bytes:
        """Make an RPC call.

        Args:
            program: RPC program number
            version: Program version number
            procedure: Procedure number to call
            args: XDR-encoded procedure arguments
            auth_flavor: Authentication flavor (default: AUTH_NULL)
            auth_data: Authentication data

        Returns:
            XDR-encoded response data

        Raises:
            ConnectionError: If not connected
            RPCError: If RPC call fails
            TimeoutError: If call times out
        """
        if not self.is_connected():
            raise GSEConnectionError("Not connected to RPC server")

        # Generate new XID
        self.xid += 1

        # Build RPC call message
        msg = self._build_call_message(
            self.xid, program, version, procedure,
            args, auth_flavor, auth_data
        )

        # Send message with record marking
        try:
            self._send_fragment(msg, last=True)
        except socket.timeout:
            raise TimeoutError(f"Timeout sending RPC call (procedure {procedure})")
        except socket.error as e:
            raise GSEConnectionError(f"Failed to send RPC call: {e}")

        logger.debug(f"Sent RPC call: xid={self.xid}, prog={program}, vers={version}, proc={procedure}")

        # Receive response
        try:
            response = self._receive_fragments()
        except socket.timeout:
            raise TimeoutError(f"Timeout receiving RPC response (procedure {procedure})")
        except socket.error as e:
            raise GSEConnectionError(f"Failed to receive RPC response: {e}")

        # Parse response
        result = self._parse_reply(response, self.xid)

        logger.debug(f"Received RPC reply: xid={self.xid}, size={len(result)} bytes")

        return result

    def _build_call_message(
        self,
        xid: int,
        program: int,
        version: int,
        procedure: int,
        args: bytes,
        auth_flavor: int,
        auth_data: bytes
    ) -> bytes:
        """Build RPC call message.

        Args:
            xid: Transaction ID
            program: Program number
            version: Version number
            procedure: Procedure number
            args: Procedure arguments
            auth_flavor: Authentication flavor
            auth_data: Authentication data

        Returns:
            Complete RPC call message
        """
        encoder = XDREncoder()

        # XID
        encoder.encode_uint(xid)

        # Message type (CALL)
        encoder.encode_uint(RPC_CALL)

        # RPC version
        encoder.encode_uint(RPC_VERSION)

        # Program, version, procedure
        encoder.encode_uint(program)
        encoder.encode_uint(version)
        encoder.encode_uint(procedure)

        # Credentials (auth)
        encoder.encode_uint(auth_flavor)
        if auth_data:
            encoder.encode_bytes(auth_data)
        else:
            encoder.encode_uint(0)  # Empty auth

        # Verifier (auth)
        encoder.encode_uint(AUTH_NULL)
        encoder.encode_uint(0)  # Empty verifier

        # Arguments
        encoder.buffer.extend(args)

        return encoder.get_bytes()

    def _send_fragment(self, data: bytes, last: bool = True) -> None:
        """Send RPC fragment with record marking.

        Args:
            data: Fragment data
            last: True if this is the last fragment

        Raises:
            socket.error: If send fails
        """
        # Record marking: 4-byte length with high bit indicating last fragment
        length = len(data)
        if last:
            length |= 0x80000000

        header = struct.pack('>I', length)
        self.sock.sendall(header + data)

    def _receive_fragment(self) -> Tuple[bytes, bool]:
        """Receive one RPC fragment.

        Returns:
            Tuple of (fragment data, is_last_fragment)

        Raises:
            socket.error: If receive fails
        """
        # Read record marking (4 bytes)
        header = self._recv_exactly(4)
        length = struct.unpack('>I', header)[0]

        # Check if last fragment
        last = (length & 0x80000000) != 0
        length = length & 0x7FFFFFFF

        # Read fragment data
        data = self._recv_exactly(length)

        return data, last

    def _receive_fragments(self) -> bytes:
        """Receive all RPC fragments and reassemble.

        Returns:
            Complete reassembled message

        Raises:
            socket.error: If receive fails
        """
        fragments = []

        while True:
            fragment, last = self._receive_fragment()
            fragments.append(fragment)

            if last:
                break

        return b''.join(fragments)

    def _recv_exactly(self, n: int) -> bytes:
        """Receive exactly n bytes from socket.

        Args:
            n: Number of bytes to receive

        Returns:
            Received data

        Raises:
            socket.error: If receive fails or connection closes
        """
        data = bytearray()
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise GSEConnectionError("Connection closed by server")
            data.extend(chunk)
        return bytes(data)

    def _parse_reply(self, data: bytes, expected_xid: int) -> bytes:
        """Parse RPC reply message.

        Args:
            data: Reply message data
            expected_xid: Expected transaction ID

        Returns:
            Procedure result data

        Raises:
            RPCError: If reply indicates error
        """
        decoder = XDRDecoder(data)

        # XID
        xid = decoder.decode_uint()
        if xid != expected_xid:
            raise RPCError(f"XID mismatch: expected {expected_xid}, got {xid}")

        # Message type (should be REPLY)
        msg_type = decoder.decode_uint()
        if msg_type != RPC_REPLY:
            raise RPCError(f"Expected REPLY message, got type {msg_type}")

        # Reply status
        reply_stat = decoder.decode_uint()

        if reply_stat == MSG_DENIED:
            reject_stat = decoder.decode_uint()
            if reject_stat == RPC_MISMATCH:
                low = decoder.decode_uint()
                high = decoder.decode_uint()
                raise RPCError(f"RPC version mismatch: server supports {low}-{high}", RPC_VERSMISMATCH)
            elif reject_stat == AUTH_ERROR:
                auth_stat = decoder.decode_uint()
                raise RPCError(f"Authentication error: {auth_stat}", RPC_AUTHERROR)
            else:
                raise RPCError(f"RPC call denied: {reject_stat}")

        elif reply_stat == MSG_ACCEPTED:
            # Verifier (skip)
            verifier_flavor = decoder.decode_uint()
            verifier_len = decoder.decode_uint()
            if verifier_len > 0:
                decoder.decode_fixed_bytes(verifier_len)

            # Accept status
            accept_stat = decoder.decode_uint()

            if accept_stat == SUCCESS:
                # Return remaining data (procedure result)
                return decoder.get_remaining_bytes()

            elif accept_stat == PROG_UNAVAIL:
                raise RPCError("Program unavailable", RPC_PROGUNAVAIL)

            elif accept_stat == PROG_MISMATCH:
                low = decoder.decode_uint()
                high = decoder.decode_uint()
                raise RPCError(f"Program version mismatch: server supports {low}-{high}", RPC_PROGVERSMISMATCH)

            elif accept_stat == PROC_UNAVAIL:
                raise RPCError("Procedure unavailable", RPC_PROCUNAVAIL)

            elif accept_stat == GARBAGE_ARGS:
                raise RPCError("Garbage arguments", RPC_CANTDECODEARGS)

            elif accept_stat == SYSTEM_ERR:
                raise RPCError("System error", RPC_SYSTEMERROR)

            else:
                raise RPCError(f"Unknown accept status: {accept_stat}")

        else:
            raise RPCError(f"Unknown reply status: {reply_stat}")
