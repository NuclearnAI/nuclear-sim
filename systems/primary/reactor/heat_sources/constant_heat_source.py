"""
Constant Heat Source

Simple heat source that provides constant, predictable thermal power.
Perfect for testing secondary side systems without reactor physics complexity.

Enhanced with optional Gaussian white noise for realistic power variations.
"""

from typing import Any, Dict, Optional

import numpy as np

from .heat_source_interface import HeatSource


class ConstantHeatSource(HeatSource):
    """
    Simple heat source that maintains constant power output with optional noise
    
    This heat source:
    - Instantly responds to setpoint changes
    - No complex physics or dynamics
    - Always outputs exactly what is requested (unless noise is enabled)
    - Perfect for testing and development
    - Optional Gaussian white noise with low-pass filtering for realism
    """
    
    def __init__(self, 
                 rated_power_mw: float = 3000.0,
                 noise_enabled: bool = False,
                 noise_std_percent: float = 0.5,
                 noise_seed: Optional[int] = None,
                 noise_filter_time_constant: float = 30.0):
        """
        Initialize constant heat source
        
        Args:
            rated_power_mw: Rated thermal power in MW
            noise_enabled: Enable Gaussian white noise on power output
            noise_std_percent: Standard deviation of noise as percentage of current power
            noise_seed: Random seed for reproducible noise (None for random)
            noise_filter_time_constant: Time constant for low-pass noise filter in seconds
        """
        super().__init__(rated_power_mw)
        self.current_power_mw = self.rated_power_mw  # Start at 100%
        self.power_setpoint_percent = 100.0
        
        # Simple state tracking
        self.time = 0.0
        self.total_energy_mwh = 0.0
        
        # Noise configuration
        self.noise_enabled = noise_enabled
        self.noise_std_percent = noise_std_percent
        self.noise_filter_time_constant = noise_filter_time_constant
        
        # Initialize random number generator
        if noise_seed is not None:
            self.rng = np.random.RandomState(noise_seed)
        else:
            self.rng = np.random.RandomState()
            
        # Filtered noise state
        self.filtered_noise_mw = 0.0
        self.raw_noise_mw = 0.0
        
    def get_thermal_power_mw(self) -> float:
        """
        Get current thermal power output (including noise if enabled)
        
        Returns:
            Current thermal power in MW (clamped to physical limits)
        """
        if not self.noise_enabled:
            return self.current_power_mw
        
        # Apply filtered noise to base power
        noisy_power = self.current_power_mw + self.filtered_noise_mw
        
        # Ensure power stays within physical reactor limits
        # Real reactors cannot exceed rated power due to fuel design limits
        return max(0.0, min(noisy_power, self.rated_power_mw))
    
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
        
        # For constant source, power is always exactly at setpoint
        self.current_power_mw = (self.power_setpoint_percent / 100.0) * self.rated_power_mw
        
        # Generate and filter noise if enabled
        if self.noise_enabled:
            self._update_noise(dt)
        
        # Get final power output (including noise)
        final_power_mw = self.get_thermal_power_mw()
        
        # Update energy integration using final power
        energy_increment_mwh = final_power_mw * (dt / 3600.0)  # Convert seconds to hours
        self.total_energy_mwh += energy_increment_mwh
        
        return {
            'thermal_power_mw': final_power_mw,
            'power_percent': (final_power_mw / self.rated_power_mw) * 100.0,
            'setpoint_percent': self.power_setpoint_percent,
            'energy_mwh': self.total_energy_mwh,
            'available': True,
            'heat_source_type': 'constant',
            'noise_enabled': self.noise_enabled,
            'filtered_noise_mw': self.filtered_noise_mw if self.noise_enabled else 0.0,
            'raw_noise_mw': self.raw_noise_mw if self.noise_enabled else 0.0
        }
    
    def get_state_dict(self) -> Dict[str, Any]:
        """
        Get current state as dictionary for logging/monitoring
        
        Returns:
            Dictionary with all relevant state variables
        """
        final_power_mw = self.get_thermal_power_mw()
        return {
            'heat_source_type': 'constant',
            'thermal_power_mw': final_power_mw,
            'base_power_mw': self.current_power_mw,
            'power_percent': (final_power_mw / self.rated_power_mw) * 100.0,
            'power_setpoint_percent': self.power_setpoint_percent,
            'rated_power_mw': self.rated_power_mw,
            'time': self.time,
            'total_energy_mwh': self.total_energy_mwh,
            'available': True,
            'noise_enabled': self.noise_enabled,
            'noise_std_percent': self.noise_std_percent,
            'noise_filter_time_constant': self.noise_filter_time_constant,
            'filtered_noise_mw': self.filtered_noise_mw if self.noise_enabled else 0.0,
            'raw_noise_mw': self.raw_noise_mw if self.noise_enabled else 0.0
        }
    
    def _update_noise(self, dt: float) -> None:
        """
        Update noise generation and filtering
        
        Args:
            dt: Time step in seconds
        """
        # Generate new Gaussian white noise
        noise_std_mw = (self.noise_std_percent / 100.0) * self.current_power_mw
        self.raw_noise_mw = self.rng.normal(0.0, noise_std_mw)
        
        # Apply low-pass filter using exponential moving average
        # α = dt / (time_constant + dt)
        alpha = dt / (self.noise_filter_time_constant + dt)
        self.filtered_noise_mw = alpha * self.raw_noise_mw + (1.0 - alpha) * self.filtered_noise_mw
    
    def reset(self) -> None:
        """Reset heat source to initial conditions"""
        self.current_power_mw = self.rated_power_mw
        self.power_setpoint_percent = 100.0
        self.time = 0.0
        self.total_energy_mwh = 0.0
        
        # Reset noise state
        self.filtered_noise_mw = 0.0
        self.raw_noise_mw = 0.0
    
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
        final_power_mw = self.get_thermal_power_mw()
        if self.noise_enabled:
            return f"ConstantHeatSource({(final_power_mw/self.rated_power_mw)*100:.1f}% of {self.rated_power_mw:.0f} MW, noise={self.noise_std_percent:.1f}%)"
        else:
            return f"ConstantHeatSource({self.get_power_percent():.1f}% of {self.rated_power_mw:.0f} MW)"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        final_power_mw = self.get_thermal_power_mw()
        if self.noise_enabled:
            return (f"ConstantHeatSource(power={final_power_mw:.1f}MW, "
                    f"base={self.current_power_mw:.1f}MW, "
                    f"setpoint={self.power_setpoint_percent:.1f}%, "
                    f"rated={self.rated_power_mw:.0f}MW, "
                    f"noise={self.noise_std_percent:.1f}%, "
                    f"filter_tc={self.noise_filter_time_constant:.1f}s)")
        else:
            return (f"ConstantHeatSource(power={self.current_power_mw:.1f}MW, "
                    f"setpoint={self.power_setpoint_percent:.1f}%, "
                    f"rated={self.rated_power_mw:.0f}MW)")
