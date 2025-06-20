"""
Condenser Physics Module

This module provides comprehensive condenser physics models for PWR plants,
including enhanced models with tube degradation, fouling, water quality,
and vacuum system integration.

Components:
- Enhanced condenser physics with advanced degradation states
- Tube degradation and failure tracking
- Multi-component fouling models (biofouling, scale, corrosion)
- Cooling water quality and chemical treatment
- Steam jet ejector vacuum system
- Vacuum system control logic
"""

# Import enhanced condenser physics
from .physics import (
    EnhancedCondenserPhysics,
    EnhancedCondenserConfig,
    TubeDegradationModel,
    TubeDegradationConfig,
    AdvancedFoulingModel,
    FoulingConfig
)

# Import vacuum system components
from .vacuum_system import (
    VacuumSystem,
    VacuumSystemConfig,
    VacuumControlLogic
)

# Import vacuum pump components
from .vacuum_pump import (
    SteamJetEjector,
    SteamEjectorConfig
)

__all__ = [
    # Enhanced condenser physics
    'EnhancedCondenserPhysics',
    'EnhancedCondenserConfig',
    
    # Tube degradation
    'TubeDegradationModel',
    'TubeDegradationConfig',
    
    # Fouling models
    'AdvancedFoulingModel',
    'FoulingConfig',
    
    # Vacuum system
    'VacuumSystem',
    'VacuumSystemConfig',
    'VacuumControlLogic',
    
    # Steam jet ejectors
    'SteamJetEjector',
    'SteamEjectorConfig'
]
