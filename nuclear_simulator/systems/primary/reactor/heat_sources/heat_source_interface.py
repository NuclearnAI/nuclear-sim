"""
Heat Source Interface

Abstract base class defining the interface for all heat sources in the nuclear plant simulator.
This allows for easy switching between different heat source types (constant, reactor physics, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class HeatSource(ABC):
    """Abstract base class for all heat sources"""
    
    def __init__(self, rated_power_mw: float = 3000.0):
        """
        Initialize heat source
        
        Args:
            rated_power_mw: Rated thermal power in MW
        """
        self.rated_power_mw = rated_power_mw
        self.current_power_mw = 0.0
        self.power_setpoint_percent = 100.0
        
    @abstractmethod
    def get_thermal_power_mw(self) -> float:
        """
        Get current thermal power output
        
        Returns:
            Current thermal power in MW
        """
        pass
    
    @abstractmethod
    def get_power_percent(self) -> float:
        """
        Get current power as percentage of rated
        
        Returns:
            Power level as percentage (0-100+)
        """
        pass
    
    @abstractmethod
    def set_power_setpoint(self, power_percent: float) -> None:
        """
        Set desired power level
        
        Args:
            power_percent: Target power level as percentage of rated (0-100+)
        """
        pass
    
    @abstractmethod
    def update(self, dt: float, **kwargs) -> Dict[str, Any]:
        """
        Update heat source state for one time step
        
        Args:
            dt: Time step in seconds
            **kwargs: Additional parameters (coolant temp, flow rate, etc.)
            
        Returns:
            Dictionary with heat source status and parameters
        """
        pass
    
    @abstractmethod
    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary for logging/monitoring
        
        Returns:
            Dictionary with all relevant state variables
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset heat source to initial conditions"""
        pass
    
    def get_power_fraction(self) -> float:
        """
        Get current power as fraction of rated (0.0 - 1.0+)
        
        Returns:
            Power level as fraction
        """
        return self.get_power_percent() / 100.0
    
    def is_available(self) -> bool:
        """
        Check if heat source is available (not tripped/failed)
        
        Returns:
            True if heat source is available
        """
        return True  # Default implementation - override if needed
