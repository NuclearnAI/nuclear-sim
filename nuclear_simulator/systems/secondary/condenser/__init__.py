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

# Import centralized configuration system
from .config import (
    CondenserConfig,
    CondenserHeatTransferConfig,
    CondenserVacuumSystemConfig,
    CondenserTubeDegradationConfig,
    CondenserFoulingConfig,
    CondenserCoolingWaterConfig,
    SteamEjectorConfig,
    CondenserInitialConditions,
    CondenserMaintenanceConfig,
    create_standard_condenser_config,
    create_uprated_condenser_config,
    create_high_efficiency_condenser_config
)

# Import enhanced condenser physics (now uses centralized config)
from .physics import (
    EnhancedCondenserPhysics,
    TubeDegradationModel,
    AdvancedFoulingModel
)

# Import vacuum system components (now uses centralized config)
from .vacuum_system import (
    VacuumSystem,
    VacuumControlLogic
)

# Import vacuum pump components (now uses centralized config)
from .vacuum_pump import (
    SteamJetEjector
)

__all__ = [
    # Centralized configuration system
    'CondenserConfig',
    'CondenserHeatTransferConfig',
    'CondenserVacuumSystemConfig',
    'CondenserTubeDegradationConfig',
    'CondenserFoulingConfig',
    'CondenserCoolingWaterConfig',
    'SteamEjectorConfig',
    'CondenserInitialConditions',
    'CondenserMaintenanceConfig',
    'create_standard_condenser_config',
    'create_uprated_condenser_config',
    'create_high_efficiency_condenser_config',
    
    # Enhanced condenser physics
    'EnhancedCondenserPhysics',
    
    # Tube degradation
    'TubeDegradationModel',
    
    # Fouling models
    'AdvancedFoulingModel',
    
    # Vacuum system
    'VacuumSystem',
    'VacuumControlLogic',
    
    # Steam jet ejectors
    'SteamJetEjector'
]
