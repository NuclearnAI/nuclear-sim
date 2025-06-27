"""
Initial Conditions Catalog

This module provides a centralized catalog of initial conditions for triggering
specific maintenance actions in nuclear plant simulations.
"""

from .initial_conditions_catalog import InitialConditionsCatalog, get_initial_conditions_catalog

__all__ = ['InitialConditionsCatalog', 'get_initial_conditions_catalog']
