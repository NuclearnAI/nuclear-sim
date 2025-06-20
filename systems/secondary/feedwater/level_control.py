"""
Three-Element Level Control System

This module provides advanced three-element control for steam generator level,
extracted and refactored from the original feedwater system to follow the
modular architecture pattern.

Key Features:
1. Three-element control (level, steam flow, feedwater flow)
2. Steam quality compensation
3. Load following capabilities
4. Swell compensation for void fraction effects
5. Advanced feedforward and feedback control
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


@dataclass
class ThreeElementConfig:
    """Configuration for three-element control system"""
    num_steam_generators: int = 3                    # Number of steam generators
    
    # Control gains
    level_control_gain: float = 0.8                  # Level feedback gain
    steam_flow_feedforward_gain: float = 1.0         # Steam flow feedforward gain
    flow_feedback_gain: float = 0.2                  # Feedwater flow feedback gain
    
    # Steam quality compensation
    quality_control_gain: float = 0.2                # Steam quality error gain
    void_fraction_gain: float = 0.2                  # Void fraction compensation gain
    
    # Level swell compensation
    enable_swell_compensation: bool = True           # Enable level swell compensation
    nominal_void_fraction: float = 0.45              # Normal operating void fraction
    
    # Control limits
    max_level_error: float = 2.0                     # m maximum level error
    max_flow_change_rate: float = 100.0              # kg/s/min maximum flow change rate
    min_flow_fraction: float = 0.18                  # Minimum flow as fraction of design (300 kg/s total minimum)
    max_flow_fraction: float = 1.2                   # Maximum flow as fraction of design
    
    # Design parameters
    design_sg_level: float = 12.5                    # m design steam generator level
    design_flow_per_sg: float = 555.0                # kg/s design flow per SG
    design_steam_quality: float = 0.99               # Design steam quality


class SteamQualityCompensator:
    """
    Steam quality compensation system
    
    This system adjusts feedwater flow based on steam quality to:
    1. Maintain proper heat transfer
    2. Prevent carryover or carryunder
    3. Optimize steam generator performance
    """
    
    def __init__(self, config: ThreeElementConfig):
        """Initialize steam quality compensator"""
        self.config = config
        
        # Quality tracking
        self.target_quality = config.design_steam_quality
        self.quality_error_history = []
        self.quality_integral_error = 0.0
        
        # Compensation parameters
        self.quality_deadband = 0.005                 # Quality deadband (±0.5%)
        self.max_quality_correction = 50.0            # kg/s maximum correction
        
    def calculate_quality_compensation(self,
                                     steam_qualities: List[float],
                                     steam_flows: List[float],
                                     dt: float) -> List[float]:
        """
        Calculate feedwater flow compensation based on steam quality
        
        Args:
            steam_qualities: Steam quality for each SG (0-1)
            steam_flows: Steam flow for each SG (kg/s)
            dt: Time step (hours)
            
        Returns:
            List of flow corrections for each SG (kg/s)
        """
        corrections = []
        
        for i, (quality, steam_flow) in enumerate(zip(steam_qualities, steam_flows)):
            # Calculate quality error
            quality_error = self.target_quality - quality
            
            # Apply deadband
            if abs(quality_error) < self.quality_deadband:
                quality_error = 0.0
            
            # Proportional correction
            proportional_correction = quality_error * self.config.quality_control_gain * steam_flow
            
            # Integral correction (simplified)
            self.quality_integral_error += quality_error * dt
            integral_correction = self.quality_integral_error * 0.1 * steam_flow
            
            # Total correction
            total_correction = proportional_correction + integral_correction
            
            # Apply limits
            total_correction = np.clip(total_correction, 
                                     -self.max_quality_correction, 
                                     self.max_quality_correction)
            
            corrections.append(total_correction)
            
            # Track quality error history
            if len(self.quality_error_history) > 10:
                self.quality_error_history.pop(0)
            self.quality_error_history.append(quality_error)
        
        return corrections
    
    def reset(self):
        """Reset quality compensator"""
        self.quality_error_history = []
        self.quality_integral_error = 0.0


class ThreeElementControl:
    """
    Advanced three-element control system for steam generator level
    
    This system implements:
    1. Level feedback control (primary element)
    2. Steam flow feedforward (second element)
    3. Feedwater flow feedback (third element)
    4. Steam quality compensation
    5. Level swell compensation
    6. Load following capabilities
    """
    
    def __init__(self, config: ThreeElementConfig):
        """Initialize three-element control system"""
        self.config = config
        
        # Control state
        self.target_levels = [config.design_sg_level] * config.num_steam_generators
        self.level_errors = [0.0] * config.num_steam_generators
        self.level_integral_errors = [0.0] * config.num_steam_generators
        self.previous_level_errors = [0.0] * config.num_steam_generators
        
        # Flow tracking
        self.previous_steam_flows = [config.design_flow_per_sg] * config.num_steam_generators
        self.previous_feedwater_flows = [config.design_flow_per_sg] * config.num_steam_generators
        self.flow_demand_history = []
        
        # Steam quality compensator
        self.quality_compensator = SteamQualityCompensator(config)
        
        # Control mode
        self.auto_mode = True
        self.manual_flow_setpoint = config.design_flow_per_sg * config.num_steam_generators
        
        # Performance tracking
        self.control_performance = 1.0
        self.last_calibration_time = 0.0
        
    def calculate_flow_demands(self,
                             sg_levels: List[float],
                             sg_steam_flows: List[float],
                             sg_steam_qualities: List[float],
                             target_levels: List[float] = None,
                             load_demand: float = 1.0,
                             dt: float = 1.0) -> Dict[str, float]:
        """
        Calculate feedwater flow demands using three-element control
        
        Args:
            sg_levels: Current SG levels (m)
            sg_steam_flows: Current steam flows (kg/s)
            sg_steam_qualities: Current steam qualities (0-1)
            target_levels: Target SG levels (m), optional
            load_demand: Load demand (0-1)
            dt: Time step (hours)
            
        Returns:
            Dictionary with flow demands and control information
        """
        if target_levels is None:
            target_levels = self.target_levels
        
        # Update target levels
        self.target_levels = target_levels
        
        if not self.auto_mode:
            # Manual mode - return manual setpoint
            return {
                'total_flow_demand': self.manual_flow_setpoint,
                'individual_demands': [self.manual_flow_setpoint / self.config.num_steam_generators] * self.config.num_steam_generators,
                'level_errors': [0.0] * self.config.num_steam_generators,
                'control_mode': 'manual'
            }
        
        # Calculate individual SG flow demands
        individual_demands = []
        level_errors = []
        
        # Get steam quality compensation
        quality_corrections = self.quality_compensator.calculate_quality_compensation(
            sg_steam_qualities, sg_steam_flows, dt
        )
        
        for i in range(self.config.num_steam_generators):
            # Ensure we have valid data
            if i < len(sg_levels) and i < len(sg_steam_flows) and i < len(sg_steam_qualities):
                level = sg_levels[i]
                steam_flow = sg_steam_flows[i]
                steam_quality = sg_steam_qualities[i]
                target_level = target_levels[i] if i < len(target_levels) else self.config.design_sg_level
                quality_correction = quality_corrections[i] if i < len(quality_corrections) else 0.0
            else:
                # Use defaults if data is missing
                level = self.config.design_sg_level
                steam_flow = self.config.design_flow_per_sg * load_demand
                steam_quality = self.config.design_steam_quality
                target_level = self.config.design_sg_level
                quality_correction = 0.0
            
            # === ELEMENT 1: LEVEL FEEDBACK CONTROL ===
            level_error = target_level - level
            level_errors.append(level_error)
            
            # Level swell compensation
            if self.config.enable_swell_compensation:
                # Estimate void fraction effect on apparent level
                void_fraction = 0.3 + 0.3 * steam_quality  # Simplified relationship
                void_error = void_fraction - self.config.nominal_void_fraction
                swell_correction = void_error * self.config.void_fraction_gain * 2.0  # m correction
                
                # Adjust target level based on void fraction
                compensated_target_level = target_level + swell_correction
                level_error = compensated_target_level - level
            
            # PID control for level
            # Proportional term
            proportional_correction = self.config.level_control_gain * level_error * 50.0  # kg/s per meter error
            
            # Integral term (simplified)
            self.level_integral_errors[i] += level_error * dt
            integral_correction = self.level_integral_errors[i] * 0.1 * 10.0  # kg/s
            
            # Derivative term
            if i < len(self.previous_level_errors):
                level_error_rate = (level_error - self.previous_level_errors[i]) / dt
                derivative_correction = level_error_rate * 0.05 * 20.0  # kg/s
            else:
                derivative_correction = 0.0
            
            level_correction = proportional_correction + integral_correction + derivative_correction
            
            # === ELEMENT 2: STEAM FLOW FEEDFORWARD ===
            # This is the key to making feedwater flow follow load changes
            feedforward_demand = steam_flow * self.config.steam_flow_feedforward_gain
            
            # === ELEMENT 3: FEEDWATER FLOW FEEDBACK ===
            # Compare actual feedwater flow to demand (simplified for now)
            if i < len(self.previous_feedwater_flows):
                flow_error = feedforward_demand - self.previous_feedwater_flows[i]
                flow_feedback_correction = flow_error * self.config.flow_feedback_gain
            else:
                flow_feedback_correction = 0.0
            
            # === COMBINE ALL ELEMENTS ===
            # Start with feedforward (steam flow demand)
            base_demand = feedforward_demand
            
            # Add level correction (small adjustment)
            total_demand = base_demand + level_correction + flow_feedback_correction + quality_correction
            
            # Apply load demand scaling
            total_demand *= load_demand
            
            # Apply limits
            min_demand = self.config.design_flow_per_sg * self.config.min_flow_fraction
            max_demand = self.config.design_flow_per_sg * self.config.max_flow_fraction
            total_demand = np.clip(total_demand, min_demand, max_demand)
            
            individual_demands.append(total_demand)
            
            # Update previous values
            if i < len(self.previous_level_errors):
                self.previous_level_errors[i] = level_error
            else:
                self.previous_level_errors.append(level_error)
            
            if i < len(self.previous_steam_flows):
                self.previous_steam_flows[i] = steam_flow
            else:
                self.previous_steam_flows.append(steam_flow)
        
        # Calculate total demand
        total_flow_demand = sum(individual_demands)
        
        # Track flow demand history
        if len(self.flow_demand_history) > 20:
            self.flow_demand_history.pop(0)
        self.flow_demand_history.append(total_flow_demand)
        
        # Update level errors
        self.level_errors = level_errors
        
        # Calculate control performance
        avg_level_error = np.mean([abs(error) for error in level_errors])
        self.control_performance = max(0.0, 1.0 - avg_level_error / 2.0)  # Performance degrades with level error
        
        return {
            'total_flow_demand': total_flow_demand,
            'individual_demands': individual_demands,
            'level_errors': level_errors,
            'control_mode': 'automatic',
            'control_performance': self.control_performance,
            'quality_corrections': quality_corrections,
            'avg_level_error': avg_level_error
        }
    
    def set_manual_mode(self, manual_setpoint: float = None):
        """Set control to manual mode"""
        self.auto_mode = False
        if manual_setpoint is not None:
            self.manual_flow_setpoint = manual_setpoint
    
    def set_auto_mode(self):
        """Set control to automatic mode"""
        self.auto_mode = True
        
        # Reset integral errors when switching to auto
        self.level_integral_errors = [0.0] * self.config.num_steam_generators
        self.quality_compensator.reset()
    
    def set_target_levels(self, target_levels: List[float]):
        """Set target levels for all steam generators"""
        if len(target_levels) == self.config.num_steam_generators:
            self.target_levels = target_levels.copy()
    
    def perform_calibration(self, **kwargs) -> Dict[str, float]:
        """Perform control system calibration"""
        calibration_type = kwargs.get('calibration_type', 'standard')
        
        results = {}
        
        if calibration_type == 'level_sensors':
            # Reset level integral errors
            self.level_integral_errors = [0.0] * self.config.num_steam_generators
            results['level_calibration'] = True
            
        elif calibration_type == 'flow_sensors':
            # Reset flow tracking
            self.previous_feedwater_flows = [self.config.design_flow_per_sg] * self.config.num_steam_generators
            results['flow_calibration'] = True
            
        elif calibration_type == 'quality_compensation':
            # Reset quality compensator
            self.quality_compensator.reset()
            results['quality_calibration'] = True
            
        else:
            # Full calibration
            self.level_integral_errors = [0.0] * self.config.num_steam_generators
            self.previous_feedwater_flows = [self.config.design_flow_per_sg] * self.config.num_steam_generators
            self.quality_compensator.reset()
            self.flow_demand_history = []
            results['full_calibration'] = True
        
        self.last_calibration_time = 0.0  # Reset calibration timer
        self.control_performance = 1.0    # Reset performance to optimal
        
        return results
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'level_control_auto_mode': float(self.auto_mode),
            'level_control_performance': self.control_performance,
            'level_control_avg_error': np.mean([abs(error) for error in self.level_errors]),
            'level_control_max_error': max([abs(error) for error in self.level_errors]) if self.level_errors else 0.0,
            'level_control_manual_setpoint': self.manual_flow_setpoint
        }
        
        # Add individual SG level errors
        for i, error in enumerate(self.level_errors):
            state_dict[f'level_control_sg_{i+1}_error'] = error
        
        # Add target levels
        for i, target in enumerate(self.target_levels):
            state_dict[f'level_control_sg_{i+1}_target'] = target
        
        return state_dict
    
    def reset(self):
        """Reset three-element control system"""
        self.level_errors = [0.0] * self.config.num_steam_generators
        self.level_integral_errors = [0.0] * self.config.num_steam_generators
        self.previous_level_errors = [0.0] * self.config.num_steam_generators
        self.previous_steam_flows = [self.config.design_flow_per_sg] * self.config.num_steam_generators
        self.previous_feedwater_flows = [self.config.design_flow_per_sg] * self.config.num_steam_generators
        self.flow_demand_history = []
        self.quality_compensator.reset()
        self.auto_mode = True
        self.manual_flow_setpoint = self.config.design_flow_per_sg * self.config.num_steam_generators
        self.control_performance = 1.0
        self.last_calibration_time = 0.0


# Example usage and testing
if __name__ == "__main__":
    print("Three-Element Level Control System - Test")
    print("=" * 50)
    
    # Create control system
    config = ThreeElementConfig(num_steam_generators=3)
    control_system = ThreeElementControl(config)
    
    print(f"Control System Configuration:")
    print(f"  Number of SGs: {config.num_steam_generators}")
    print(f"  Level Control Gain: {config.level_control_gain}")
    print(f"  Steam Flow Feedforward Gain: {config.steam_flow_feedforward_gain}")
    print(f"  Design SG Level: {config.design_sg_level} m")
    print(f"  Design Flow per SG: {config.design_flow_per_sg} kg/s")
    print()
    
    # Test control system operation
    print("Control System Test:")
    print(f"{'Time':<6} {'Load':<6} {'Avg Level':<10} {'Total Demand':<12} {'Avg Error':<10} {'Performance':<12}")
    print("-" * 70)
    
    for hour in range(24):
        # Simulate load following
        if hour < 4:
            load_demand = 0.5 + 0.1 * hour  # 50% to 80% load
        elif hour < 8:
            load_demand = 0.8 + 0.05 * (hour - 4)  # 80% to 100% load
        elif hour < 16:
            load_demand = 1.0  # 100% load
        elif hour < 20:
            load_demand = 1.0 - 0.1 * (hour - 16)  # 100% to 60% load
        else:
            load_demand = 0.6  # 60% load
        
        # Simulate SG conditions with slight variations
        sg_levels = [12.5 + 0.2 * np.sin(hour * 0.2 + i) for i in range(3)]
        sg_steam_flows = [555.0 * load_demand + 10 * np.sin(hour * 0.1 + i) for i in range(3)]
        sg_steam_qualities = [0.99 + 0.005 * np.sin(hour * 0.15 + i) for i in range(3)]
        
        # Calculate control demands
        result = control_system.calculate_flow_demands(
            sg_levels=sg_levels,
            sg_steam_flows=sg_steam_flows,
            sg_steam_qualities=sg_steam_qualities,
            load_demand=load_demand,
            dt=1.0
        )
        
        avg_level = np.mean(sg_levels)
        avg_error = abs(result['avg_level_error'])
        
        if hour % 2 == 0:  # Print every 2 hours
            print(f"{hour:<6} {load_demand:<6.1%} {avg_level:<10.2f} "
                  f"{result['total_flow_demand']:<12.0f} {avg_error:<10.3f} "
                  f"{result['control_performance']:<12.3f}")
    
    print()
    print("Three-element control system ready for integration!")
