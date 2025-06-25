"""
Turbine System Module

This module provides comprehensive turbine physics modeling including:
- Enhanced turbine physics with advanced states
- Multi-stage turbine system coordination
- Rotor dynamics and mechanical modeling
- Thermal stress and degradation tracking
- Protection systems and trip logic

Components:
- enhanced_physics.py: Main enhanced turbine physics model
- stage_system.py: Multi-stage coordination and control
- rotor_dynamics.py: Rotor speed, vibration, bearing models
- thermal_model.py: Thermal stress and expansion tracking
- protection_system.py: Trip conditions and safety systems
"""

# Import new unified config system
from .config import (
    TurbineConfig,
    TurbineStageSystemConfig,
    RotorDynamicsConfig,
    TurbineThermalStressConfig,
    TurbineProtectionConfig,
    TurbineGovernorConfig,
    TurbineBearingConfig
)

from .enhanced_physics import (
    EnhancedTurbinePhysics,
    MetalTemperatureTracker,
    TurbineProtectionSystem
)

from .stage_system import (
    TurbineStageSystem,
    TurbineStage,
    TurbineStageControlLogic
)

from .rotor_dynamics import (
    RotorDynamicsModel,
    VibrationMonitor,
    BearingModel
)

from ..lubrication_base import (
    BaseLubricationSystem,
    BaseLubricationConfig,
    LubricationComponent
)

from .governor_system import (
    TurbineGovernorSystem,
    GovernorLubricationSystem,
    GovernorValveModel
)

from .turbine_bearing_lubrication import (
    TurbineBearingLubricationSystem,
    TurbineBearingLubricationConfig,
    integrate_lubrication_with_turbine
)

# Note: Legacy turbine classes are imported directly in systems.secondary.__init__.py
# to avoid circular import issues

# Note: thermal_model.py and protection_system.py not yet implemented
# These will be added in future versions

__all__ = [
    # New unified configuration classes
    'TurbineConfig',
    'TurbineStageSystemConfig',
    'RotorDynamicsConfig',
    'TurbineThermalStressConfig',
    'TurbineProtectionConfig',
    'TurbineGovernorConfig',
    'TubrineBearingConfig',
    
    # Main enhanced physics
    'EnhancedTurbinePhysics',
    'MetalTemperatureTracker',
    'TurbineProtectionSystem',
    
    # Stage system
    'TurbineStageSystem',
    'TurbineStage',
    'TurbineStageControlLogic',
    
    # Rotor dynamics
    'RotorDynamicsModel',
    'VibrationMonitor',
    'BearingModel',
    
    # Lubrication base classes
    'BaseLubricationSystem',
    'BaseLubricationConfig',
    'LubricationComponent',
    
    # Governor system with lubrication
    'TurbineGovernorSystem',
    'GovernorLubricationSystem',
    'GovernorValveModel',
    
    # Turbine bearing lubrication
    'TurbineBearingLubricationSystem',
    'TurbineBearingLubricationConfig',
    'integrate_lubrication_with_turbine'
]
