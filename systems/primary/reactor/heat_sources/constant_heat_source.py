"""
Constant Heat Source

Simple heat source that provides constant, predictable thermal power.
Perfect for testing secondary side systems without reactor physics complexity.
"""

from typing import Any, Dict

import numpy as np

from .heat_source_interface import HeatSource


class ConstantHeatSource(HeatSource):
    """
    Simple heat source that maintains constant power output
    
    This heat source:
    - Instantly responds to setpoint changes
    - No complex physics or dynamics
    - Always outputs exactly what is requested
    - Perfect for testing and development
    """
    
    def __init__(self, rated_power_mw: float = 3000.0):
        """
        Initialize constant heat source
        
        Args:
            rated_power_mw: Rated thermal power in MW
        """
        super().__init__(rated_power_mw)
        self.current_power_mw = self.rated_power_mw  # Start at 100%
        self.power_setpoint_percent = 100.0
        
        # Simple state tracking
        self.time = 0.0
        self.total_energy_mwh = 0.0
        
    def get_thermal_power_mw(self) -> float:
        """
        Get current thermal power output
        
        Returns:
            Current thermal power in MW
        """
        return self.current_power_mw
    
    def get_power_percent(self) -> float:
        """
        Get current power as percentage of rated
        
        Returns:
            Power level as percentage (0-100+)
        """
        return (self.current_power_mw / self.rated_power_mw) * 100.0
    
    def set_power_setpoint(self, power_percent: float) -> None:
        """
        Set desired power level (instant response)
        
        Args:
            power_percent: Target power level as percentage of rated (0-100+)
        """
        self.power_setpoint_percent = np.clip(power_percent, 0.0, 150.0)  # Allow up to 150%
        self.current_power_mw = (self.power_setpoint_percent / 100.0) * self.rated_power_mw
    
    def update(self, dt: float, **kwargs) -> Dict[str, Any]:
        """
        Update heat source state for one time step
        
        Args:
            dt: Time step in seconds
            **kwargs: Additional parameters (ignored for constant source)
            
        Returns:
            Dictionary with heat source status and parameters
        """
        # Update time tracking
        self.time += dt
        
        # Update energy integration
        energy_increment_mwh = self.current_power_mw * (dt / 3600.0)  # Convert seconds to hours
        self.total_energy_mwh += energy_increment_mwh
        
        # For constant source, power is always exactly at setpoint
        self.current_power_mw = (self.power_setpoint_percent / 100.0) * self.rated_power_mw
        
        return {
            'thermal_power_mw': self.current_power_mw,
            'power_percent': self.get_power_percent(),
            'setpoint_percent': self.power_setpoint_percent,
            'energy_mwh': self.total_energy_mwh,
            'available': True,
            'heat_source_type': 'constant'
        }
    
    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary for logging/monitoring
        
        Returns:
            Dictionary with all relevant state variables
        """
        return {
            'heat_source_type': 'constant',
            'thermal_power_mw': self.current_power_mw,
            'power_percent': self.get_power_percent(),
            'power_setpoint_percent': self.power_setpoint_percent,
            'rated_power_mw': self.rated_power_mw,
            'time': self.time,
            'total_energy_mwh': self.total_energy_mwh,
            'available': True
        }
    
    def reset(self) -> None:
        """Reset heat source to initial conditions"""
        self.current_power_mw = self.rated_power_mw
        self.power_setpoint_percent = 100.0
        self.time = 0.0
        self.total_energy_mwh = 0.0
    
    def add_power_variation(self, variation_percent: float) -> None:
        """
        Add a small power variation (for testing perturbations)
        
        Args:
            variation_percent: Power variation in percent (can be positive or negative)
        """
        new_setpoint = self.power_setpoint_percent + variation_percent
        self.set_power_setpoint(new_setpoint)
    
    def get_efficiency(self) -> float:
        """
        Get heat source efficiency (always 100% for constant source)
        
        Returns:
            Efficiency as fraction (always 1.0)
        """
        return 1.0
    
    def __str__(self) -> str:
        """String representation"""
        return f"ConstantHeatSource({self.get_power_percent():.1f}% of {self.rated_power_mw:.0f} MW)"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"ConstantHeatSource(power={self.current_power_mw:.1f}MW, "
                f"setpoint={self.power_setpoint_percent:.1f}%, "
                f"rated={self.rated_power_mw:.0f}MW)")
