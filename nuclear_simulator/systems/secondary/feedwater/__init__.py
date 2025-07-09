"""
Feedwater System Module

This module provides comprehensive feedwater system physics modeling including:
- Enhanced feedwater physics with advanced states
- Multi-pump system coordination and control
- Three-element level control system
- Water chemistry and treatment modeling
- Performance monitoring and diagnostics
- Protection systems and trip logic

Components:
- physics.py: Main enhanced feedwater physics model
- pump_system.py: Individual pump models and coordination
- level_control.py: Three-element control and steam quality management
- water_chemistry.py: Water quality monitoring and treatment
- performance_monitoring.py: Cavitation, wear, and diagnostics
- protection_system.py: Safety systems and protection logic
"""

# Import enhanced feedwater physics
from .physics import (
    EnhancedFeedwaterPhysics,
)

# Import proper feedwater config
from .config import (
    FeedwaterConfig,
    create_standard_feedwater_config
)

# Import pump system components
from .pump_system import (
    FeedwaterPumpSystem,
    FeedwaterPumpSystemConfig,
    FeedwaterPump,
    FeedwaterPumpState,
    FeedwaterPumpConfig
)

# Import control system components
from .level_control import (
    ThreeElementControl,
    SteamQualityCompensator
)

# Note: Water chemistry components moved to unified system at systems.secondary.water_chemistry
# from .water_chemistry import (
#     WaterQualityModel,
#     WaterQualityConfig,
#     ChemicalTreatmentSystem
# )

# Import performance monitoring
from .performance_monitoring import (
    CavitationModel,
    CavitationConfig,
    WearTrackingModel,
    WearTrackingConfig,
    PerformanceDiagnostics,
    PerformanceDiagnosticsConfig
)

# Import protection system
from .protection_system import (
    FeedwaterProtectionSystem,
    FeedwaterProtectionConfig,
    NPSHProtection
)

# Import pump lubrication system
from .pump_lubrication import (
    FeedwaterPumpLubricationSystem,
    FeedwaterPumpLubricationConfig,
    integrate_lubrication_with_pump
)

__all__ = [
    # Main enhanced physics
    'EnhancedFeedwaterPhysics',
    
    # Proper feedwater config
    'FeedwaterConfig',
    'create_standard_feedwater_config',
    
    # Pump system
    'FeedwaterPumpSystem',
    'FeedwaterPumpSystemConfig',
    'FeedwaterPump',
    'FeedwaterPumpState',
    'FeedwaterPumpConfig',
    
    # Control system
    'ThreeElementControl',
    'SteamQualityCompensator',
    
    # Water chemistry (moved to unified system)
    # 'WaterQualityModel',
    # 'WaterQualityConfig', 
    # 'ChemicalTreatmentSystem',
    
    # Performance monitoring
    'CavitationModel',
    'CavitationConfig',
    'WearTrackingModel',
    'WearTrackingConfig',
    'PerformanceDiagnostics',
    'PerformanceDiagnosticsConfig',
    
    # Protection system
    'FeedwaterProtectionSystem',
    'FeedwaterProtectionConfig',
    'NPSHProtection',
    
    # Pump lubrication system
    'FeedwaterPumpLubricationSystem',
    'FeedwaterPumpLubricationConfig',
    'integrate_lubrication_with_pump'
]
