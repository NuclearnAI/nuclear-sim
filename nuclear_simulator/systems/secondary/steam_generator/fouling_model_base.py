"""
Fouling Model Base Class

This module provides a base class for all fouling models in steam generators,
including shared properties, methods, and interfaces for consistent behavior
across different fouling phenomena (TSP fouling, tube interior scaling, etc.).

Key Features:
1. Shared chemistry integration
2. Common time tracking and performance metrics
3. Unified maintenance interface
4. Consistent state management
5. Base physics calculations (temperature, pH effects)
"""

import numpy as np
from typing import Dict, Optional, Any
from dataclasses import dataclass
import warnings

# Import chemistry flow interfaces
try:
    from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies
    CHEMISTRY_INTEGRATION_AVAILABLE = True
except ImportError:
    # Fallback for standalone operation
    CHEMISTRY_INTEGRATION_AVAILABLE = False
    
    class ChemistryFlowProvider:
        def get_chemistry_flows(self): return {}
        def get_chemistry_state(self): return {}
        def update_chemistry_effects(self, chemistry_state): pass
    
    class ChemicalSpecies:
        PH = "ph"
        IRON = "iron"
        COPPER = "copper"
        SILICA = "silica"

# Import unified water chemistry system
try:
    from ..water_chemistry import WaterChemistry, WaterChemistryConfig
    WATER_CHEMISTRY_AVAILABLE = True
except ImportError:
    WATER_CHEMISTRY_AVAILABLE = False
    WaterChemistry = None
    WaterChemistryConfig = None

warnings.filterwarnings("ignore")


class FoulingModelBase(ChemistryFlowProvider):
    """
    Base class for all fouling models in steam generators
    
    This class provides common functionality for different types of fouling:
    - TSP (Tube Support Plate) fouling on secondary side
    - Tube interior scaling on primary side
    - Future fouling types (condenser tubes, etc.)
    
    Shared Features:
    - Chemistry integration with unified water chemistry system
    - Time tracking and operating history
    - Common physics calculations (temperature, pH effects)
    - Unified maintenance interface
    - Consistent state management
    """
    
    def __init__(self, config: Optional[Any] = None, water_chemistry: Optional[WaterChemistry] = None):
        """Initialize base fouling model"""
        self.config = config
        
        # Initialize or use provided unified water chemistry system
        if water_chemistry is not None:
            self.water_chemistry = water_chemistry
        elif WATER_CHEMISTRY_AVAILABLE:
            # Create own instance if not provided (for standalone use)
            self.water_chemistry = WaterChemistry(WaterChemistryConfig())
        else:
            self.water_chemistry = None
        
        # === SHARED STATE VARIABLES ===
        # Time tracking
        self.operating_years = 0.0                  # Total operating years
        self.total_cleaning_cycles = 0              # Number of cleaning cycles performed
        self.last_cleaning_time = 0.0               # Years since last cleaning
        
        # Fouling state
        self.fouling_fraction = 0.0                 # Overall fouling fraction (0-1)
        
        # Performance tracking
        self.cumulative_performance_loss = 0.0      # Cumulative performance loss
        self.replacement_recommended = False        # Replacement recommendation flag
        
        # Maintenance history
        self.maintenance_history = []               # List of maintenance events
    
    def update_operating_time(self, dt_seconds: float) -> None:
        """
        Update operating time tracking (shared by all fouling models)
        
        Args:
            dt_seconds: Time step in seconds
        """
        dt_years = dt_seconds / (365.25 * 24.0 * 3600.0)  # Convert seconds to years
        
        self.operating_years += dt_years
        self.last_cleaning_time += dt_years
    
    def calculate_temperature_factor(self, 
                                   temperature: float, 
                                   activation_energy: float = 45000.0,
                                   reference_temp: float = 300.0) -> float:
        """
        Calculate Arrhenius temperature relationship (shared by all fouling models)
        
        Args:
            temperature: Current temperature (°C)
            activation_energy: Activation energy (J/mol)
            reference_temp: Reference temperature (°C)
            
        Returns:
            Temperature factor relative to reference
        """
        temp_kelvin = temperature + 273.15
        ref_temp_kelvin = reference_temp + 273.15
        
        factor = np.exp(-activation_energy / (8.314 * temp_kelvin))
        ref_factor = np.exp(-activation_energy / (8.314 * ref_temp_kelvin))
        
        return factor / ref_factor
    
    def calculate_ph_factor(self, ph: float, optimal_ph: float = 9.2) -> float:
        """
        Calculate pH effect on fouling (shared calculation)
        
        Args:
            ph: Current pH
            optimal_ph: Optimal pH for minimal fouling
            
        Returns:
            pH factor (1.0 = optimal, >1.0 = increased fouling)
        """
        return 1.0 + 0.5 * abs(ph - optimal_ph)
    
    def calculate_chemistry_multiplier(self, 
                                     species_concentration: float, 
                                     base_factor: float) -> float:
        """
        Generic chemistry concentration effect
        
        Args:
            species_concentration: Concentration of chemical species
            base_factor: Base multiplication factor per unit concentration
            
        Returns:
            Chemistry multiplier
        """
        return 1.0 + species_concentration * base_factor
    
    def calculate_flow_velocity_factor(self, 
                                     velocity: float, 
                                     reference_velocity: float = 3.0,
                                     exponent: float = 0.5) -> float:
        """
        Calculate flow velocity effect on mass transfer and fouling
        
        Args:
            velocity: Current flow velocity (m/s)
            reference_velocity: Reference velocity (m/s)
            exponent: Velocity exponent
            
        Returns:
            Velocity factor
        """
        velocity_ratio = velocity / reference_velocity
        return np.clip(velocity_ratio ** exponent, 0.5, 2.0)
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Base maintenance method - override in subclasses
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results
        """
        # Base implementation - subclasses should override with their specific maintenance functions
        maintenance_functions = {
            # Override in subclasses with specific maintenance functions
        }
        
        if maintenance_type not in maintenance_functions:
            return {
                'success': False,
                'error': f'Unknown maintenance type: {maintenance_type}',
                'available_types': list(maintenance_functions.keys())
            }
        
        # Execute maintenance function
        result = maintenance_functions[maintenance_type](**kwargs)
        
        # Update maintenance history
        self._update_maintenance_history(result, maintenance_type)
        
        return result
    
    def _update_maintenance_history(self, result: Dict[str, Any], maintenance_type: str) -> None:
        """Update maintenance history tracking"""
        if result.get('success', False):
            self.total_cleaning_cycles += 1
            self.last_cleaning_time = 0.0
            
            # Add to maintenance history
            self.maintenance_history.append({
                'type': maintenance_type,
                'operating_years': self.operating_years,
                'success': result.get('success', False),
                'duration_hours': result.get('duration_hours', 0.0),
                'effectiveness': result.get('effectiveness_score', 0.0)
            })
            
            # Keep only last 10 maintenance events
            if len(self.maintenance_history) > 10:
                self.maintenance_history = self.maintenance_history[-10:]
    
    def get_state_dict(self) -> Dict[str, float]:
        """
        Get current state as dictionary for logging/monitoring
        Base implementation - extend in subclasses
        
        Returns:
            Dictionary with base fouling state
        """
        return {
            # Base fouling state
            'fouling_operating_years': self.operating_years,
            'fouling_total_cleaning_cycles': float(self.total_cleaning_cycles),
            'fouling_years_since_cleaning': self.last_cleaning_time,
            'fouling_fraction': self.fouling_fraction,
            'fouling_cumulative_performance_loss': self.cumulative_performance_loss,
            'fouling_replacement_recommended': float(self.replacement_recommended)
        }
    
    def reset(self) -> None:
        """Reset fouling model to initial conditions - override in subclasses"""
        # Reset base state
        self.operating_years = 0.0
        self.total_cleaning_cycles = 0
        self.last_cleaning_time = 0.0
        self.fouling_fraction = 0.0
        self.cumulative_performance_loss = 0.0
        self.replacement_recommended = False
        self.maintenance_history = []
    
    # === CHEMISTRY FLOW PROVIDER INTERFACE METHODS ===
    # Base implementations - extend in subclasses
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        Base implementation - extend in subclasses
        
        Returns:
            Dictionary with base chemistry flow data
        """
        return {
            'base_fouling': {
                'fouling_fraction': self.fouling_fraction,
                'operating_years': self.operating_years,
                'cleaning_cycles': float(self.total_cleaning_cycles)
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state for chemistry flow tracker
        Base implementation - extend in subclasses
        
        Returns:
            Dictionary with base chemistry state
        """
        return {
            'fouling_fraction': self.fouling_fraction,
            'operating_years': self.operating_years,
            'years_since_cleaning': self.last_cleaning_time
        }
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update fouling based on external chemistry effects
        Base implementation - extend in subclasses
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Base implementation - subclasses can extend with specific chemistry effects
        if hasattr(self, 'water_chemistry') and self.water_chemistry:
            # Pass chemistry effects to the water chemistry system
            self.water_chemistry.update_chemistry_effects(chemistry_state)


# Example usage and testing
if __name__ == "__main__":
    print("Fouling Model Base Class - Test")
    print("=" * 40)
    
    # Create base fouling model
    base_fouling = FoulingModelBase()
    
    print(f"Base Fouling Model:")
    print(f"  Operating years: {base_fouling.operating_years}")
    print(f"  Fouling fraction: {base_fouling.fouling_fraction}")
    print(f"  Cleaning cycles: {base_fouling.total_cleaning_cycles}")
    print()
    
    # Test shared physics calculations
    print("Shared Physics Calculations:")
    temp_factor = base_fouling.calculate_temperature_factor(285.0)
    ph_factor = base_fouling.calculate_ph_factor(9.0)
    chem_multiplier = base_fouling.calculate_chemistry_multiplier(0.1, 1.5)
    flow_factor = base_fouling.calculate_flow_velocity_factor(2.5)
    
    print(f"  Temperature factor (285°C): {temp_factor:.3f}")
    print(f"  pH factor (pH 9.0): {ph_factor:.3f}")
    print(f"  Chemistry multiplier (0.1 ppm, factor 1.5): {chem_multiplier:.3f}")
    print(f"  Flow velocity factor (2.5 m/s): {flow_factor:.3f}")
    print()
    
    # Test state dictionary
    state_dict = base_fouling.get_state_dict()
    print("State Dictionary:")
    for key, value in state_dict.items():
        print(f"  {key}: {value}")
    print()
    
    # Test maintenance (should fail with base implementation)
    result = base_fouling.perform_maintenance('test_maintenance')
    print("Maintenance Test:")
    print(f"  Success: {result['success']}")
    print(f"  Error: {result.get('error', 'None')}")
    print()
    
    print("Fouling model base class ready for inheritance!")
