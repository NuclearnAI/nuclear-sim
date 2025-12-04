"""
GSE GPWR Simulator Python Library

A complete Python library for interfacing with the GSE GPWR nuclear power plant
training simulator via ONC RPC protocol.

This library provides:
- Low-level ONC RPC client implementation
- XDR serialization/deserialization
- High-level GDA Server client wrapper
- RL Gym-compatible environment wrapper
- Complete data structure definitions

Example:
    >>> from gse import GDAClient
    >>> with GDAClient(host='10.1.0.123', port=9800) as client:
    ...     value = client.read_variable('RCS01POWER')
    ...     print(f"Reactor power: {value} MW")
"""

__version__ = "1.0.0"
__author__ = "Nuclear Sim Team"

from gse.gda_client import GDAClient
from gse.simulator_manager import SimulatorManager
from gse.types import (
    GDES,
    MALFS,
    OVERS,
    REMS,
    GLCF,
    FPO,
    ANO,
    ALLACTIVE,
    DataType,
    PointType,
)
from gse.env import GPWREnvironment
from gse.exceptions import (
    GSEError,
    RPCError,
    ConnectionError,
    TimeoutError,
    VariableNotFoundError,
)

__all__ = [
    'GDAClient',
    'GPWREnvironment',
    'SimulatorManager',
    'GDES',
    'MALFS',
    'OVERS',
    'REMS',
    'GLCF',
    'FPO',
    'ANO',
    'ALLACTIVE',
    'DataType',
    'PointType',
    'GSEError',
    'RPCError',
    'ConnectionError',
    'TimeoutError',
    'VariableNotFoundError',
]
