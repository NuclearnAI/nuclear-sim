"""
Custom exceptions for GSE GPWR library.
"""


class GSEError(Exception):
    """Base exception for all GSE library errors."""
    pass


class RPCError(GSEError):
    """RPC protocol error."""

    def __init__(self, message: str, error_code: int = None):
        super().__init__(message)
        self.error_code = error_code


class ConnectionError(GSEError):
    """Connection error to GDA server."""
    pass


class TimeoutError(GSEError):
    """Operation timeout."""
    pass


class VariableNotFoundError(GSEError):
    """Variable not found in simulator."""

    def __init__(self, variable_name: str):
        super().__init__(f"Variable not found: {variable_name}")
        self.variable_name = variable_name


class XDRError(GSEError):
    """XDR encoding/decoding error."""
    pass


class MalfunctionError(GSEError):
    """Malfunction insertion error."""
    pass


class InitialConditionError(GSEError):
    """Initial condition error."""
    pass
