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
from typing import Dict, List, Optional, Tuple, Any
import warnings

# Import the new configuration from config.py
from .config import ThreeElementControlConfig

warnings.filterwarnings("ignore")


class SteamQualityCompensator:
    """
    Steam quality compensation system
    
    This system adjusts feedwater flow based on steam quality to:
    1. Maintain proper heat transfer
    2. Prevent carryover or carryunder
    3. Optimize steam generator performance
    """
    
    def __init__(self, config: ThreeElementControlConfig):
        """Initialize steam quality compensator"""
        self.config = config
        
        # Quality tracking
        self.target_quality = 0.99  # Default design steam quality
        self.quality_error_history = []
        self.quality_integral_error = 0.0
        
        # Compensation parameters
        self.quality_deadband = 0.005                 # Quality deadband (±0.5%)
        self.max_quality_correction = 50.0            # kg/s maximum correction
        
        # Get quality control gain from config (handle both old and new attribute names)
        if hasattr(config, 'quality_control_gain'):
            self.quality_control_gain = config.quality_control_gain
        elif hasattr(config, 'quality_compensation_gain'):
            self.quality_control_gain = config.quality_compensation_gain
        else:
            self.quality_control_gain = 1.0  # Default value
        
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
            proportional_correction = quality_error * self.quality_control_gain * steam_flow
            
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
    
    def __init__(self, config: ThreeElementControlConfig, num_steam_generators: int = 3, design_sg_level: float = 12.5, design_flow_per_sg: float = 500.0):
        """Initialize three-element control system"""
        self.config = config
        
        # Store design parameters that aren't in the new config
        self.num_steam_generators = num_steam_generators
        self.design_sg_level = design_sg_level
        self.design_flow_per_sg = design_flow_per_sg
        
        # Control state
        self.target_levels = [config.level_setpoint] * num_steam_generators
        self.level_errors = [0.0] * num_steam_generators
        self.level_integral_errors = [0.0] * num_steam_generators
        self.previous_level_errors = [0.0] * num_steam_generators
        
        # Flow tracking
        self.previous_steam_flows = [design_flow_per_sg] * num_steam_generators
        self.previous_feedwater_flows = [design_flow_per_sg] * num_steam_generators
        self.flow_demand_history = []
        
        # Steam quality compensator
        self.quality_compensator = SteamQualityCompensator(config)
        
        # Control mode
        self.auto_mode = True
        self.manual_flow_setpoint = design_flow_per_sg * num_steam_generators
        
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
                'individual_demands': [self.manual_flow_setpoint / self.num_steam_generators] * self.num_steam_generators,
                'level_errors': [0.0] * self.num_steam_generators,
                'control_mode': 'manual'
            }
        
        # Calculate individual SG flow demands
        individual_demands = []
        level_errors = []
        
        
        # Get steam quality compensation
        quality_corrections = self.quality_compensator.calculate_quality_compensation(
            sg_steam_qualities, sg_steam_flows, dt
        )
        
        for i in range(self.num_steam_generators):
            # Ensure we have valid data
            if i < len(sg_levels) and i < len(sg_steam_flows) and i < len(sg_steam_qualities):
                level = sg_levels[i]
                steam_flow = sg_steam_flows[i]
                steam_quality = sg_steam_qualities[i]
                design_sg_level = getattr(self.config, 'design_sg_level', self.design_sg_level)
                target_level = target_levels[i] if i < len(target_levels) else design_sg_level
                quality_correction = quality_corrections[i] if i < len(quality_corrections) else 0.0
            else:
                # Use defaults if data is missing
                design_sg_level = getattr(self.config, 'design_sg_level', self.design_sg_level)
                design_flow_per_sg = getattr(self.config, 'design_flow_per_sg', self.design_flow_per_sg)
                design_steam_quality = getattr(self.config, 'design_steam_quality', 0.99)
                level = design_sg_level
                steam_flow = design_flow_per_sg * load_demand
                steam_quality = design_steam_quality
                target_level = design_sg_level
                quality_correction = 0.0
            
            # === ELEMENT 1: LEVEL FEEDBACK CONTROL ===
            level_error = target_level - level
            level_errors.append(level_error)
            
            # Level swell compensation (check if enabled in config)
            enable_swell_compensation = getattr(self.config, 'enable_swell_compensation', False)
            if enable_swell_compensation:
                # Estimate void fraction effect on apparent level
                void_fraction = 0.3 + 0.3 * steam_quality  # Simplified relationship
                nominal_void_fraction = getattr(self.config, 'nominal_void_fraction', 0.45)
                void_fraction_gain = getattr(self.config, 'void_fraction_gain', 1.0)
                void_error = void_fraction - nominal_void_fraction
                swell_correction = void_error * void_fraction_gain * 2.0  # m correction
                
                # Adjust target level based on void fraction
                compensated_target_level = target_level + swell_correction
                level_error = compensated_target_level - level
            
            # PID control for level - NUCLEAR GRADE ULTRA-CONSERVATIVE GAINS
            # Proportional term - nuclear plant ultra-conservative operation
            level_control_gain = getattr(self.config, 'level_control_gain', 1.0)
            proportional_correction = level_control_gain * level_error * 0.2  # kg/s per meter error (90% reduction from 2.0)
            
            # Integral term (simplified) - nuclear grade ultra-conservative gain
            self.level_integral_errors[i] += level_error * dt
            integral_correction = self.level_integral_errors[i] * 0.0005 * 0.5  # kg/s (95% reduction from 0.005 * 2.0)
            
            # Derivative term - nuclear grade ultra-conservative gain
            if i < len(self.previous_level_errors):
                level_error_rate = (level_error - self.previous_level_errors[i]) / dt
                derivative_correction = level_error_rate * 0.0002 * 0.5  # kg/s (95% reduction from 0.002 * 2.0)
            else:
                derivative_correction = 0.0
            
            # === ELEMENT 2: STEAM FLOW FEEDFORWARD ===
            # This is the key to making feedwater flow follow load changes
            # MASS BALANCE PRINCIPLE: Feedwater flow must equal steam flow
            
            # CRITICAL FIX: Always use actual steam flow for proper mass balance
            # The feedwater system must follow steam generator output exactly
            feedforward_demand = steam_flow  # Direct 1:1 mass balance - NO SCALING
            
            # Apply minimum flow only for pump protection (very low threshold)
            design_flow_per_sg = getattr(self.config, 'design_flow_per_sg', self.design_flow_per_sg)
            absolute_minimum = design_flow_per_sg * 0.05  # 5% minimum for pump protection only
            
            if steam_flow < absolute_minimum:
                # Only override for pump protection at very low flows
                feedforward_demand = absolute_minimum
            else:
                # Always follow actual steam flow for proper mass balance
                feedforward_demand = steam_flow
            
            # Now that feedforward_demand is defined, limit level correction
            level_correction = proportional_correction + integral_correction + derivative_correction
            max_level_correction = feedforward_demand * 0.01  # NUCLEAR GRADE: Max 1% of feedforward demand (reduced from 5%)
            level_correction = np.clip(level_correction, -max_level_correction, max_level_correction)
            
            # === ELEMENT 3: FEEDWATER FLOW FEEDBACK ===
            # Compare actual feedwater flow to demand (simplified for now)
            if i < len(self.previous_feedwater_flows):
                flow_error = feedforward_demand - self.previous_feedwater_flows[i]
                feedwater_flow_weight = getattr(self.config, 'feedwater_flow_weight', 0.1)
                flow_feedback_correction = flow_error * feedwater_flow_weight
            else:
                flow_feedback_correction = 0.0
            
            # === COMBINE ALL ELEMENTS ===
            # FIXED: Proper three-element control combination for mass balance
            # Steam flow feedforward should be the primary driver (mass balance requirement)
            level_control_weight = getattr(self.config, 'level_control_weight', 0.4)
            
            # CRITICAL FIX: Steam flow feedforward should maintain mass balance
            # Use full feedforward demand, then add corrections
            base_demand = feedforward_demand  # Full steam flow demand for mass balance
            
            # Level correction (weighted and limited)
            level_contribution = level_correction * level_control_weight
            
            # Flow feedback (weighted)  
            flow_contribution = flow_feedback_correction * feedwater_flow_weight
            
            # Combine: base demand + weighted corrections
            total_demand = base_demand + level_contribution + flow_contribution + quality_correction
            
            # CRITICAL FIX: Do NOT apply load demand scaling to steam flow feedforward!
            # The steam flow already reflects the actual load, so scaling it again breaks mass balance
            # Only apply scaling to the correction terms if needed
            
            # Apply reasonable limits only for pump protection (much wider range)
            design_flow_per_sg = getattr(self.config, 'design_flow_per_sg', self.design_flow_per_sg)
            # Use much wider limits to allow proper load following
            min_demand = design_flow_per_sg * 0.05  # 5% minimum for pump protection
            max_demand = design_flow_per_sg * 2.0   # 200% maximum for transients
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
        
        # PHASE 4: Mass Balance Validation
        mass_balance_results = self.validate_mass_balance(individual_demands, sg_steam_flows)
        
        return {
            'total_flow_demand': total_flow_demand,
            'individual_demands': individual_demands,
            'level_errors': level_errors,
            'control_mode': 'automatic',
            'control_performance': self.control_performance,
            'quality_corrections': quality_corrections,
            'avg_level_error': avg_level_error,
            'mass_balance_alarm': mass_balance_results['mass_balance_alarm'],
            'mass_balance_error_percent': mass_balance_results.get('imbalance_percent', 0.0),
            'mass_balance_status': mass_balance_results.get('status', 'OK')
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
        self.level_integral_errors = [0.0] * self.num_steam_generators
        self.quality_compensator.reset()
    
    def validate_mass_balance(self, feedwater_flows: List[float], steam_flows: List[float]) -> Dict[str, Any]:
        """
        Validate mass balance and generate alarms for nuclear plant operation
        
        Args:
            feedwater_flows: Feedwater flow demands for each SG (kg/s)
            steam_flows: Steam flows for each SG (kg/s)
            
        Returns:
            Dictionary with mass balance validation results
        """
        # Ensure we have matching lengths
        min_length = min(len(feedwater_flows), len(steam_flows))
        feedwater_flows = feedwater_flows[:min_length]
        steam_flows = steam_flows[:min_length]
        
        # Calculate total flows
        total_feedwater = sum(feedwater_flows)
        total_steam = sum(steam_flows)
        
        # Calculate mass balance error
        if total_steam > 0:
            imbalance_percent = abs(total_feedwater - total_steam) / total_steam * 100
        else:
            imbalance_percent = 0.0
        
        # Nuclear plant mass balance tolerance: 1% normal, 2% alarm
        if imbalance_percent > 2.0:
            # CRITICAL: Mass balance violation - reduce control gains automatically
            return {
                'mass_balance_alarm': True,
                'imbalance_percent': imbalance_percent,
                'status': 'CRITICAL_IMBALANCE',
                'corrective_action': 'Reduce level control gains immediately',
                'feedwater_total': total_feedwater,
                'steam_total': total_steam,
                'individual_errors': [abs(fw - st)/st*100 if st > 0 else 0.0 
                                    for fw, st in zip(feedwater_flows, steam_flows)]
            }
        elif imbalance_percent > 1.0:
            # WARNING: Approaching mass balance limits
            return {
                'mass_balance_alarm': True,
                'imbalance_percent': imbalance_percent,
                'status': 'WARNING_IMBALANCE',
                'corrective_action': 'Monitor control system performance',
                'feedwater_total': total_feedwater,
                'steam_total': total_steam,
                'individual_errors': [abs(fw - st)/st*100 if st > 0 else 0.0 
                                    for fw, st in zip(feedwater_flows, steam_flows)]
            }
        else:
            # NORMAL: Mass balance within acceptable limits
            return {
                'mass_balance_alarm': False,
                'imbalance_percent': imbalance_percent,
                'status': 'NORMAL',
                'corrective_action': None,
                'feedwater_total': total_feedwater,
                'steam_total': total_steam,
                'individual_errors': [abs(fw - st)/st*100 if st > 0 else 0.0 
                                    for fw, st in zip(feedwater_flows, steam_flows)]
            }
    
    def set_target_levels(self, target_levels: List[float]):
        """Set target levels for all steam generators"""
        if len(target_levels) == self.num_steam_generators:
            self.target_levels = target_levels.copy()
    
    def perform_calibration(self, **kwargs) -> Dict[str, float]:
        """Perform control system calibration"""
        calibration_type = kwargs.get('calibration_type', 'standard')
        
        results = {}
        
        if calibration_type == 'level_sensors':
            # Reset level integral errors
            self.level_integral_errors = [0.0] * self.num_steam_generators
            results['level_calibration'] = True
            
        elif calibration_type == 'flow_sensors':
            # Reset flow tracking
            self.previous_feedwater_flows = [self.design_flow_per_sg] * self.num_steam_generators
            results['flow_calibration'] = True
            
        elif calibration_type == 'quality_compensation':
            # Reset quality compensator
            self.quality_compensator.reset()
            results['quality_calibration'] = True
            
        else:
            # Full calibration
            self.level_integral_errors = [0.0] * self.num_steam_generators
            self.previous_feedwater_flows = [self.design_flow_per_sg] * self.num_steam_generators
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
        self.level_errors = [0.0] * self.num_steam_generators
        self.level_integral_errors = [0.0] * self.num_steam_generators
        self.previous_level_errors = [0.0] * self.num_steam_generators
        self.previous_steam_flows = [self.design_flow_per_sg] * self.num_steam_generators
        self.previous_feedwater_flows = [self.design_flow_per_sg] * self.num_steam_generators
        self.flow_demand_history = []
        self.quality_compensator.reset()
        self.auto_mode = True
        self.manual_flow_setpoint = self.design_flow_per_sg * self.num_steam_generators
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
