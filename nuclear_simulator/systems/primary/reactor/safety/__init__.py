"""
Reactor Safety Systems Module

This module contains safety system implementations for nuclear reactor simulation,
including SCRAM logic and safety parameter monitoring.
"""

from .scram_logic import ScramSystem

__all__ = ['ScramSystem']
