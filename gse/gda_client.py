"""
High-level GDA (Generic Data Acquisition) Server client.

Provides a convenient Python interface for the GSE GPWR simulator GDA Server API.
Handles connection management, variable access, instructor actions, and initial conditions.
"""

import logging
from typing import Optional, Dict, Any, List
from gse.rpc_client import RPCClient
from gse.xdr import XDREncoder, XDRDecoder
from gse.types import GDES, MALFS, OVERS, REMS, GLCF, FPO, ANO, ALLACTIVE, GDES_STD
from gse.exceptions import (
    GSEError,
    VariableNotFoundError,
    MalfunctionError,
    InitialConditionError,
)

logger = logging.getLogger(__name__)


# GDA RPC procedure numbers
CALLgetGDL = 1      # Get variable list
CALLgetGDES = 1     # Get variable metadata (same as getGDL)
CALLsetIC = 5       # Snap IC
CALLresetIC = 7     # Reset to IC
CALLgetBT = 9       # Get backtrack
CALLresetBT = 10    # Reset backtrack
CALLsetOR = 11      # Set override
CALLgetOVER = 12    # Get override
CALLdelOVER = 13    # Delete override
CALLgetREM = 15     # Get remote
CALLdelREM = 16     # Delete remote
CALLsetMF = 23      # Set malfunction
CALLsetRM = 24      # Set remote
CALLsetOV = 25      # Set override (newer)
CALLgetMF = 26      # Get malfunction
CALLgetRM = 27      # Get remote
CALLgetOV = 28      # Get override (newer)
CALLinfoIC = 41     # Get IC info
CALLgetFPO = 51     # Get fixed parameter override
CALLsetFPO = 52     # Set fixed parameter override
CALLdelFPO = 53     # Delete fixed parameter override
CALLgetANO = 55     # Get annunciator override
CALLsetANO = 56     # Set annunciator override
CALLdelANO = 57     # Delete annunciator override
CALLgetALLACTIVE = 84  # Get all active instructor actions
CALLget = 85        # Get variable value (primary)
CALLpost = 86       # Post variable value (primary)
CALLgetGLCF = 147   # Get global component failure
CALLsetGLCF = 148   # Set global component failure
CALLdelGLCF = 149   # Delete global component failure

# Default GDA configuration
DEFAULT_GDA_PROGRAM = 0x20000001  # Typical GDA program number
DEFAULT_GDA_VERSION = 1


class GDAClient:
    """High-level client for GDA Server.

    Provides convenient methods for reading/writing variables, inserting malfunctions,
    managing initial conditions, and other simulator operations.

    Example:
        >>> with GDAClient(host='10.1.0.123') as client:
        ...     power = client.read_variable('RCS01POWER')
        ...     client.write_variable('RTC01DEMAND', 50.0)
        ...     client.reset_to_ic(100)

    Attributes:
        host: Server hostname or IP address
        port: Server port number (default: 9800)
        timeout: Operation timeout in seconds
    """

    def __init__(
        self,
        host: str = '10.1.0.123',
        port: int = 9800,
        timeout: float = 10.0,
        program: int = DEFAULT_GDA_PROGRAM,
        version: int = DEFAULT_GDA_VERSION
    ):
        """Initialize GDA client.

        Args:
            host: GDA server hostname or IP (default: '10.1.0.123')
            port: GDA server port (default: 9800)
            timeout: Operation timeout in seconds (default: 10.0)
            program: RPC program number (default: 0x20000001)
            version: RPC version number (default: 1)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.program = program
        self.version = version
        self.rpc = RPCClient(host, port, timeout)
        self._connected = False

    def connect(self) -> None:
        """Connect to GDA server.

        Raises:
            ConnectionError: If connection fails
        """
        self.rpc.connect()
        self._connected = True
        logger.info(f"Connected to GDA server at {self.host}:{self.port}")

    def disconnect(self) -> None:
        """Disconnect from GDA server."""
        self.rpc.disconnect()
        self._connected = False
        logger.info("Disconnected from GDA server")

    def is_connected(self) -> bool:
        """Check if connected to server.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.rpc.is_connected()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False

    def read_variable(self, var_name: str) -> str:
        """Read a variable value by name.

        Uses CALLget (85) to retrieve the current value of a simulation variable.

        Args:
            var_name: Variable name (e.g., 'RCS01POWER', 'PRS01PRESS')

        Returns:
            Variable value as string

        Raises:
            VariableNotFoundError: If variable doesn't exist
            GSEError: If read operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Encode variable name
        encoder = XDREncoder()
        encoder.encode_string(var_name)
        args = encoder.get_bytes()

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLget,
                args
            )
        except Exception as e:
            logger.error(f"Failed to read variable '{var_name}': {e}")
            raise GSEError(f"Failed to read variable '{var_name}': {e}")

        # Decode response
        decoder = XDRDecoder(response)
        try:
            value = decoder.decode_string()
        except Exception as e:
            raise GSEError(f"Failed to decode variable value: {e}")

        logger.debug(f"Read variable '{var_name}' = '{value}'")
        return value

    def write_variable(self, var_name: str, value: Any) -> str:
        """Write a variable value.

        Uses CALLpost (86) to set a variable value.

        Args:
            var_name: Variable name
            value: Value to write (will be converted to string)

        Returns:
            Server response message

        Raises:
            GSEError: If write operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Format command string: "VAR_NAME=value"
        command = f"{var_name}={value}"

        # Encode command
        encoder = XDREncoder()
        encoder.encode_string(command)
        args = encoder.get_bytes()

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLpost,
                args
            )
        except Exception as e:
            logger.error(f"Failed to write variable '{var_name}': {e}")
            raise GSEError(f"Failed to write variable '{var_name}': {e}")

        # Decode response
        decoder = XDRDecoder(response)
        try:
            status = decoder.decode_string()
        except Exception as e:
            raise GSEError(f"Failed to decode write response: {e}")

        logger.debug(f"Wrote variable '{var_name}' = {value}, status: '{status}'")
        return status

    def get_variable_info(self, var_name: str, flags: int = GDES_STD) -> GDES:
        """Get detailed variable metadata.

        Uses CALLgetGDES (1) to retrieve complete information about a variable.

        Args:
            var_name: Variable name
            flags: GDES fields to retrieve (default: GDES_STD)

        Returns:
            GDES structure with variable information

        Raises:
            VariableNotFoundError: If variable doesn't exist
            GSEError: If operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Encode request
        encoder = XDREncoder()
        encoder.encode_uint(flags)
        encoder.encode_string("")  # Username (empty)
        encoder.encode_string(var_name)
        args = encoder.get_bytes()

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLgetGDES,
                args
            )
        except Exception as e:
            logger.error(f"Failed to get variable info for '{var_name}': {e}")
            raise GSEError(f"Failed to get variable info: {e}")

        # Decode response
        decoder = XDRDecoder(response)
        gdes = self._decode_gdes(decoder)

        if not gdes.name:
            raise VariableNotFoundError(var_name)

        logger.debug(f"Got variable info for '{var_name}'")
        return gdes

    def reset_to_ic(self, ic_number: int) -> None:
        """Reset simulator to an initial condition.

        Uses CALLresetIC (7) to load a saved plant state.

        Args:
            ic_number: IC number to load (e.g., 0=shutdown, 100=full power)

        Raises:
            InitialConditionError: If IC doesn't exist or reset fails
            GSEError: If operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Encode IC number
        encoder = XDREncoder()
        encoder.encode_int(ic_number)
        args = encoder.get_bytes()

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLresetIC,
                args
            )
        except Exception as e:
            logger.error(f"Failed to reset to IC {ic_number}: {e}")
            raise InitialConditionError(f"Failed to reset to IC {ic_number}: {e}")

        logger.info(f"Reset to IC {ic_number}")

    def insert_malfunction(
        self,
        var_name: str,
        final_value: float,
        ramp_time: int = 0,
        delay: int = 0,
        description: str = ""
    ) -> int:
        """Insert a malfunction on a variable.

        Uses CALLsetMF (23) to create a malfunction that ramps a variable
        to a target value over time.

        Args:
            var_name: Variable name to malfunction
            final_value: Target value for malfunction
            ramp_time: Time to ramp to final value in seconds (0=instant)
            delay: Delay before malfunction activates in seconds
            description: Optional description

        Returns:
            Malfunction index (for later deletion)

        Raises:
            MalfunctionError: If malfunction insertion fails
            GSEError: If operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Create malfunction structure
        malf = MALFS(
            vars=var_name,
            final=final_value,
            ramp=ramp_time,
            delay=delay,
            desc=description or f"Malfunction on {var_name}",
            avail=1,
            type=1,  # Ramp type
        )

        # Encode malfunction
        encoder = XDREncoder()
        self._encode_malfs(encoder, malf)
        args = encoder.get_bytes()

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLsetMF,
                args
            )
        except Exception as e:
            logger.error(f"Failed to insert malfunction on '{var_name}': {e}")
            raise MalfunctionError(f"Failed to insert malfunction: {e}")

        # Decode malfunction index
        decoder = XDRDecoder(response)
        try:
            index = decoder.decode_int()
        except Exception as e:
            raise MalfunctionError(f"Failed to decode malfunction index: {e}")

        logger.info(f"Inserted malfunction on '{var_name}', index={index}")
        return index

    def delete_malfunction(self, index: int) -> None:
        """Delete an active malfunction.

        Args:
            index: Malfunction index to delete

        Raises:
            GSEError: If deletion fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Note: CALLdelMALF might be procedure 8, implementation depends on API
        logger.warning("delete_malfunction not yet implemented")
        raise NotImplementedError("delete_malfunction requires API procedure mapping")

    def get_all_active(self) -> ALLACTIVE:
        """Get all active instructor actions.

        Uses CALLgetALLACTIVE (84) to retrieve all malfunctions, overrides,
        remotes, and other active instructor actions.

        Returns:
            ALLACTIVE structure containing all active actions

        Raises:
            GSEError: If operation fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # No arguments
        args = b''

        # Make RPC call
        try:
            response = self.rpc.call(
                self.program,
                self.version,
                CALLgetALLACTIVE,
                args
            )
        except Exception as e:
            logger.error(f"Failed to get all active actions: {e}")
            raise GSEError(f"Failed to get all active actions: {e}")

        # Decode response
        decoder = XDRDecoder(response)
        allactive = self._decode_allactive(decoder)

        logger.debug(f"Got all active: {allactive.nummalf} malfunctions, "
                    f"{allactive.numovers} overrides, {allactive.numremf} remotes")
        return allactive

    def read_variables(self, var_names: List[str]) -> Dict[str, str]:
        """Read multiple variables (batch operation).

        Args:
            var_names: List of variable names to read

        Returns:
            Dictionary mapping variable names to values

        Raises:
            GSEError: If operation fails
        """
        results = {}
        for var_name in var_names:
            try:
                results[var_name] = self.read_variable(var_name)
            except Exception as e:
                logger.warning(f"Failed to read '{var_name}': {e}")
                results[var_name] = None

        return results

    def write_variables(self, values: Dict[str, Any]) -> Dict[str, str]:
        """Write multiple variables (batch operation).

        Args:
            values: Dictionary mapping variable names to values

        Returns:
            Dictionary mapping variable names to status messages

        Raises:
            GSEError: If operation fails
        """
        results = {}
        for var_name, value in values.items():
            try:
                results[var_name] = self.write_variable(var_name, value)
            except Exception as e:
                logger.warning(f"Failed to write '{var_name}': {e}")
                results[var_name] = f"ERROR: {e}"

        return results

    # Helper methods for encoding/decoding structures

    def _encode_malfs(self, encoder: XDREncoder, malf: MALFS) -> None:
        """Encode MALFS structure to XDR."""
        encoder.encode_short(malf.avail)
        encoder.encode_short(malf.type)
        encoder.encode_short(malf.scale)
        encoder.encode_short(malf.pending)
        encoder.encode_short(malf.event)
        encoder.encode_short(malf.index)
        encoder.encode_short(malf.trgindex)
        encoder.encode_short(malf.gid)
        encoder.encode_short(malf.trggid)
        encoder.encode_int(malf.delay)
        encoder.encode_int(malf.ldelete)
        encoder.encode_int(malf.ramp)
        encoder.encode_int(malf.offset)
        encoder.encode_int(malf.trgoffset)
        encoder.encode_int(malf.goffset)
        encoder.encode_int(malf.gtrgoffset)
        encoder.encode_int(malf.time)
        encoder.encode_float(malf.final)
        encoder.encode_float(malf.init)
        encoder.encode_float(malf.delta)
        encoder.encode_float(malf.low)
        encoder.encode_float(malf.high)
        encoder.encode_double(malf.value)
        encoder.encode_string(malf.vars)
        encoder.encode_string(malf.trgvars)
        encoder.encode_string(malf.desc)
        encoder.encode_string(malf.param)
        encoder.encode_string(malf.tam)
        encoder.encode_short(malf.malftype)

    def _decode_gdes(self, decoder: XDRDecoder) -> GDES:
        """Decode GDES structure from XDR."""
        gdes = GDES()

        # This is simplified - actual implementation depends on flags
        # For now, decode common fields
        try:
            gdes.name = decoder.decode_string()
            gdes.type = decoder.decode_ushort()
            gdes.gid = decoder.decode_ushort()

            # Additional fields as needed...
            if decoder.remaining() > 0:
                gdes.value = decoder.decode_string()

        except Exception as e:
            logger.warning(f"Error decoding GDES: {e}")

        return gdes

    def _decode_allactive(self, decoder: XDRDecoder) -> ALLACTIVE:
        """Decode ALLACTIVE structure from XDR."""
        allactive = ALLACTIVE()

        try:
            # Number of malfunctions
            allactive.nummalf = decoder.decode_int()
            # Decode malfunction array...
            # (simplified for now)

            # Similar for other fields...
        except Exception as e:
            logger.warning(f"Error decoding ALLACTIVE: {e}")

        return allactive
