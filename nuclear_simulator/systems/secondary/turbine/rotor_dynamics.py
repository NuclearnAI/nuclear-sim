"""
Rotor Dynamics Model for PWR Steam Turbine

This module implements comprehensive rotor dynamics modeling including:
- Rotor speed and acceleration tracking
- Vibration monitoring and analysis
- Bearing load calculations
- Mechanical stress analysis

Parameter Sources:
- Turbomachinery Dynamics (Vance)
- Rotor Dynamics and Critical Speed Analysis
- Bearing design specifications
- Vibration monitoring standards

Physical Basis:
- Newton's laws for rotational motion
- Vibration dynamics and critical speeds
- Bearing load distribution
- Mechanical stress calculations
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from .config import RotorDynamicsConfig

warnings.filterwarnings("ignore")


# BearingConfig is now integrated into the unified RotorDynamicsConfig
# Individual bearing configurations are created from RotorDynamicsConfig parameters


class BearingModel:
    """
    Individual bearing model - analogous to individual components in condenser
    
    This model implements:
    1. Bearing load calculations
    2. Temperature monitoring
    3. Oil film analysis
    4. Wear and degradation tracking
    """
    
    def __init__(self, bearing_id: str, bearing_config_dict: Dict):
        """Initialize bearing model from config dictionary"""
        # Create a simple config object from the dictionary
        class BearingConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        self.config = BearingConfig(**bearing_config_dict)
        
        # Bearing state
        self.current_load = 0.0                  # kN current bearing load
        self.metal_temperature = 90.0            # °C bearing metal temperature
        
        # Vibration state
        self.vibration_displacement = 0.0        # mils vibration displacement
        self.vibration_velocity = 0.0            # in/s vibration velocity
        self.vibration_acceleration = 0.0        # g vibration acceleration
        
        # Performance tracking
        self.operating_hours = 0.0               # Hours of operation
        self.load_cycles = 0                     # Number of load cycles
        self.wear_factor = 1.0                   # Bearing wear factor (1.0 = new)
        self.efficiency_factor = 1.0             # Bearing efficiency factor
        
        # Degradation tracking
        self.clearance_increase = 0.0            # mm clearance increase due to wear
        
        # UNIFIED LUBRICATION INTEGRATION - All oil parameters come from external system
        self.oil_temperature = 85.0              # °C oil temperature (from lubrication system)
        self.oil_flow_rate = 10.0                # L/min oil flow rate (from lubrication system)
        self.oil_pressure = 0.2                  # MPa oil supply pressure (from lubrication system)
        self.oil_contamination_level = 0.0       # ppm contamination level (from lubrication system)
        self.external_oil_temp = False           # Flag for external oil temperature
        self.external_oil_temperature = 85.0    # External oil temperature (°C)
        
    def calculate_bearing_loads(self,
                              rotor_weight: float,
                              steam_thrust: float,
                              thermal_expansion: float,
                              rotor_speed: float) -> Dict[str, float]:
        """
        Calculate bearing loads from various sources
        
        Args:
            rotor_weight: Rotor weight component (kN)
            steam_thrust: Steam thrust force (kN)
            thermal_expansion: Thermal expansion effect (mm)
            rotor_speed: Current rotor speed (RPM)
            
        Returns:
            Dictionary with bearing load results
        """
        # Static load from rotor weight
        static_load = rotor_weight
        
        # Dynamic load from steam thrust (for thrust bearings)
        if self.config.bearing_type == "thrust":
            thrust_load = steam_thrust
        else:
            thrust_load = 0.0
        
        # Thermal load from differential expansion
        thermal_load = abs(thermal_expansion) * self.config.stiffness_coefficient / 1000.0  # Convert to kN
        
        # Dynamic load from unbalance (speed dependent)
        unbalance_force = (rotor_speed / 3600.0) ** 2 * 0.1  # Simplified unbalance force
        
        # Total bearing load
        total_load = static_load + thrust_load + thermal_load + unbalance_force
        
        # Apply wear factor (worn bearings carry more load)
        total_load *= (2.0 - self.wear_factor)
        
        self.current_load = total_load
        
        return {
            'total_load': total_load,
            'static_load': static_load,
            'thrust_load': thrust_load,
            'thermal_load': thermal_load,
            'unbalance_load': unbalance_force,
            'load_factor': total_load / self.config.design_load_capacity
        }
    
    def set_lubrication_state(self, oil_temp: float, oil_flow: float, oil_quality: Dict):
        """
        Accept lubrication state from external lubrication system
        
        Args:
            oil_temp: Oil temperature from lubrication system (°C)
            oil_flow: Oil flow rate from lubrication system (L/min)
            oil_quality: Oil quality metrics dictionary
        """
        # Validate inputs to prevent NaN propagation
        if np.isfinite(oil_temp) and oil_temp > 0:
            self.oil_temperature = oil_temp
            # Mark that we have external oil temperature
            self.external_oil_temp = True
            self.external_oil_temperature = oil_temp
        
        if np.isfinite(oil_flow) and oil_flow > 0:
            self.oil_flow_rate = oil_flow
        
        # Update oil quality metrics
        if isinstance(oil_quality, dict):
            contamination = oil_quality.get('contamination', 0.0)
            if np.isfinite(contamination):
                self.oil_contamination_level = contamination

    def calculate_bearing_temperature(self,
                                    oil_inlet_temp: float,
                                    bearing_load: float,
                                    rotor_speed: float,
                                    dt: float) -> Dict[str, float]:
        """
        Calculate bearing temperatures with corrected physics and NaN prevention
        
        Args:
            oil_inlet_temp: Oil inlet temperature (°C)
            bearing_load: Current bearing load (kN)
            rotor_speed: Rotor speed (RPM)
            dt: Time step (hours)
            
        Returns:
            Dictionary with temperature results
        """
        # Validate inputs
        oil_inlet_temp = max(20.0, min(150.0, oil_inlet_temp)) if np.isfinite(oil_inlet_temp) else 60.0
        bearing_load = max(0.0, bearing_load) if np.isfinite(bearing_load) else 0.0
        rotor_speed = max(0.0, rotor_speed) if np.isfinite(rotor_speed) else 0.0
        dt = max(0.0, dt) if np.isfinite(dt) else 1.0
        
        # CORRECTED: Heat generation from friction using proper tribology physics
        # Friction power = Friction_torque × Angular_velocity
        # Friction_torque = μ × Normal_force × bearing_radius
        
        # Bearing geometry (typical turbine bearing dimensions)
        bearing_radius = 0.15  # m (typical 300mm diameter bearing)
        
        # Convert units properly
        bearing_load_n = bearing_load * 1000.0  # Convert kN to N
        angular_velocity = rotor_speed * 2 * np.pi / 60.0  # Convert RPM to rad/s
        
        # Calculate friction torque (N⋅m)
        friction_torque = self.config.friction_coefficient * bearing_load_n * bearing_radius
        
        # Calculate friction power (W)
        friction_power = friction_torque * angular_velocity
        
        # Apply realistic limits (typical turbine bearing: 1-50 kW max)
        max_friction_power = 50000.0  # W (50 kW maximum realistic)
        friction_power = min(friction_power, max_friction_power)
        
        # Ensure friction power is finite and positive
        if not np.isfinite(friction_power) or friction_power < 0:
            friction_power = 0.0
        
        # Heat transfer to oil
        oil_heat_capacity = 2000.0  # J/kg/K
        oil_density = 850.0         # kg/m³
        
        # Ensure oil flow rate is valid
        if not np.isfinite(self.oil_flow_rate) or self.oil_flow_rate <= 0:
            self.oil_flow_rate = 10.0  # Default flow rate L/min
        
        oil_mass_flow = self.oil_flow_rate / 60.0 * oil_density / 1000.0  # kg/s
        
        # Temperature rise calculation with safety checks
        if oil_mass_flow > 0 and np.isfinite(oil_mass_flow):
            temp_rise = friction_power / (oil_mass_flow * oil_heat_capacity)
            # Limit temperature rise to reasonable values
            temp_rise = min(50.0, max(0.0, temp_rise))
        else:
            temp_rise = 0.0
        
        # Ensure temp_rise is finite
        if not np.isfinite(temp_rise):
            temp_rise = 0.0
        
        # Use external oil temperature if available, otherwise calculate internally
        if hasattr(self, 'external_oil_temp') and self.external_oil_temp:
            # Use externally provided oil temperature (from lubrication system)
            # Don't override it with internal calculations
            pass  # Keep the external oil temperature
        else:
            # Calculate oil temperature internally (fallback)
            time_constant = 30.0  # seconds
            oil_temp_target = oil_inlet_temp + temp_rise
            
            # Ensure target temperature is reasonable
            oil_temp_target = max(20.0, min(150.0, oil_temp_target))
            
            # Ensure current oil temperature is valid
            if not np.isfinite(self.oil_temperature):
                self.oil_temperature = oil_inlet_temp
            
            temp_change = (oil_temp_target - self.oil_temperature) / time_constant * dt * 3600.0
            
            # Limit temperature change rate
            temp_change = max(-10.0, min(10.0, temp_change))
            
            self.oil_temperature += temp_change
            
            # Ensure oil temperature stays within bounds
            self.oil_temperature = max(20.0, min(150.0, self.oil_temperature))
        
        # Metal temperature (higher than oil temperature)
        metal_temp_rise = temp_rise * 1.5  # Metal runs hotter than oil
        self.metal_temperature = oil_inlet_temp + metal_temp_rise
        
        # Ensure metal temperature is reasonable
        self.metal_temperature = max(30.0, min(200.0, self.metal_temperature))
        
        # Final validation of all outputs
        results = {
            'oil_temperature': self.oil_temperature if np.isfinite(self.oil_temperature) else 60.0,
            'metal_temperature': self.metal_temperature if np.isfinite(self.metal_temperature) else 90.0,
            'temperature_rise': temp_rise if np.isfinite(temp_rise) else 0.0,
            'friction_power': friction_power if np.isfinite(friction_power) else 0.0,
            'oil_flow_rate': self.oil_flow_rate if np.isfinite(self.oil_flow_rate) else 10.0
        }
        
        return results
    
    def update_bearing_wear(self,
                          bearing_load: float,
                          oil_contamination: float,
                          dt: float) -> Dict[str, float]:
        """
        Update bearing wear and degradation
        
        Args:
            bearing_load: Current bearing load (kN)
            oil_contamination: Oil contamination level (ppm)
            dt: Time step (hours)
            
        Returns:
            Dictionary with wear results
        """
        # Load-based wear
        load_factor = bearing_load / self.config.design_load_capacity
        load_wear_rate = 0.00001 * (load_factor ** 2) * dt  # Wear rate per hour
        
        # Contamination-based wear
        contamination_wear_rate = 0.000005 * oil_contamination * dt
        
        # Total wear
        total_wear = load_wear_rate + contamination_wear_rate
        self.wear_factor = max(0.5, self.wear_factor - total_wear)
        
        # Clearance increase due to wear
        clearance_increase = total_wear * 0.01  # mm clearance increase
        self.clearance_increase += clearance_increase
        
        # Update efficiency factor
        self.efficiency_factor = self.wear_factor * 0.9 + 0.1  # Minimum 10% efficiency
        
        # Update operating hours
        self.operating_hours += dt
        
        return {
            'wear_factor': self.wear_factor,
            'clearance_increase': self.clearance_increase,
            'efficiency_factor': self.efficiency_factor,
            'load_wear_rate': load_wear_rate,
            'contamination_wear_rate': contamination_wear_rate,
            'operating_hours': self.operating_hours
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get bearing state for monitoring"""
        return {
            f'{self.config.bearing_id}_load': self.current_load,
            f'{self.config.bearing_id}_oil_temp': self.oil_temperature,
            f'{self.config.bearing_id}_metal_temp': self.metal_temperature,
            f'{self.config.bearing_id}_vibration_disp': self.vibration_displacement,
            f'{self.config.bearing_id}_vibration_vel': self.vibration_velocity,
            f'{self.config.bearing_id}_wear_factor': self.wear_factor,
            f'{self.config.bearing_id}_clearance_increase': self.clearance_increase,
            f'{self.config.bearing_id}_operating_hours': self.operating_hours
        }
    
    def setup_maintenance_integration(self, maintenance_system, component_id: str):
        """
        Set up maintenance integration for individual bearing
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
            component_id: Unique identifier for this bearing
        """
        print(f"BEARING {component_id}: Setting up maintenance integration")
        
        # Define monitoring configuration for bearing parameters
        monitoring_config = {
            'bearing_temperature': {
                'attribute': 'metal_temperature',
                'threshold': 120.0,  # °C temperature threshold
                'comparison': 'greater_than',
                'action': 'turbine_bearing_inspection',
                'cooldown_hours': 24.0  # Daily cooldown
            },
            'bearing_wear': {
                'attribute': 'wear_factor',
                'threshold': 0.8,  # 80% remaining (20% wear)
                'comparison': 'less_than',
                'action': 'turbine_bearing_replacement',
                'cooldown_hours': 168.0  # Weekly cooldown
            },
            'bearing_clearance': {
                'attribute': 'clearance_increase',
                'threshold': 0.1,  # mm clearance increase
                'comparison': 'greater_than',
                'action': 'bearing_clearance_check',
                'cooldown_hours': 72.0  # 3-day cooldown
            },
            'oil_contamination': {
                'attribute': 'oil_contamination_level',
                'threshold': 8.0,  # ppm contamination threshold
                'comparison': 'greater_than',
                'action': 'turbine_oil_change',
                'cooldown_hours': 48.0  # 2-day cooldown
            }
        }
        
        # Register with maintenance system using event bus
        maintenance_system.register_component(component_id, self, monitoring_config)
        
        print(f"  Registered {component_id} with {len(monitoring_config)} monitoring parameters")
        
        # Store reference for coordination
        self.maintenance_system = maintenance_system
        self.component_id = component_id
    
    def perform_maintenance(self, maintenance_type: str = None, **kwargs):
        """
        Perform maintenance operations on bearing
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        if maintenance_type == "turbine_bearing_inspection":
            # Perform bearing inspection
            current_temp = self.metal_temperature
            current_wear = (1.0 - self.wear_factor) * 100.0  # Convert to percentage
            current_clearance = self.clearance_increase
            
            findings = f"Bearing temperature: {current_temp:.1f}°C, "
            findings += f"wear: {current_wear:.1f}%, clearance increase: {current_clearance:.3f}mm"
            
            recommendations = []
            if current_temp > 110.0:
                recommendations.append("Monitor bearing temperature closely")
            if current_wear > 15.0:
                recommendations.append("Schedule bearing replacement within 6 months")
            if current_clearance > 0.08:
                recommendations.append("Check bearing alignment")
            
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'Comprehensive bearing inspection completed',
                'findings': findings,
                'recommendations': recommendations,
                'effectiveness_score': 1.0,  # Inspection always successful
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Inspection tools', 'Measurement equipment']
            }
        
        elif maintenance_type == "turbine_bearing_replacement":
            # Perform bearing replacement
            old_wear = (1.0 - self.wear_factor) * 100.0
            
            # Reset bearing to new condition
            self.wear_factor = 1.0
            self.clearance_increase = 0.0
            self.efficiency_factor = 1.0
            self.metal_temperature = min(self.metal_temperature, 90.0)  # Reduce temperature
            
            performance_improvement = old_wear  # Percentage improvement
            
            return {
                'success': True,
                'duration_hours': 12.0,
                'work_performed': 'Bearing replacement completed',
                'findings': f"Replaced bearing with {old_wear:.1f}% wear",
                'performance_improvement': performance_improvement,
                'effectiveness_score': 1.0,
                'next_maintenance_due': 35040.0,  # Every 4 years
                'parts_used': ['New bearing assembly', 'Bearing housing gaskets', 'Lubricating oil']
            }
        
        elif maintenance_type == "bearing_clearance_check":
            # Perform clearance check and adjustment
            original_clearance = self.clearance_increase
            
            # Adjust clearance (simulated improvement)
            clearance_reduction = min(0.05, self.clearance_increase * 0.5)  # 50% improvement up to 0.05mm
            self.clearance_increase -= clearance_reduction
            self.clearance_increase = max(0.0, self.clearance_increase)
            
            # Improve efficiency slightly
            self.efficiency_factor = min(1.0, self.efficiency_factor + 0.02)
            
            return {
                'success': True,
                'duration_hours': 3.0,
                'work_performed': 'Bearing clearance check and adjustment',
                'findings': f"Reduced clearance from {original_clearance:.3f}mm to {self.clearance_increase:.3f}mm",
                'performance_improvement': (clearance_reduction / max(0.001, original_clearance)) * 100.0,
                'effectiveness_score': 0.8,
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Shim stock', 'Measurement tools']
            }
        
        elif maintenance_type == "bearing_alignment":
            # Perform bearing alignment
            # Improve efficiency and reduce vibration
            alignment_improvement = 0.05  # 5% improvement
            self.efficiency_factor = min(1.0, self.efficiency_factor + alignment_improvement)
            
            # Reduce vibration levels
            self.vibration_displacement *= 0.8  # 20% reduction
            self.vibration_velocity *= 0.8
            
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': 'Bearing alignment completed',
                'findings': 'Improved bearing concentricity and reduced vibration',
                'performance_improvement': alignment_improvement * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 17520.0,  # Every 2 years
                'parts_used': ['Alignment tools', 'Precision shims']
            }
        
        elif maintenance_type == "thrust_bearing_adjustment":
            # Perform thrust bearing adjustment (only applicable to thrust bearings)
            if self.config.bearing_type == "thrust":
                # Optimize thrust bearing position
                self.efficiency_factor = min(1.0, self.efficiency_factor + 0.03)
                self.metal_temperature = max(80.0, self.metal_temperature - 5.0)  # Reduce temperature
                
                return {
                    'success': True,
                    'duration_hours': 4.0,
                    'work_performed': 'Thrust bearing adjustment completed',
                    'findings': 'Optimized thrust bearing position and clearances',
                    'performance_improvement': 3.0,
                    'effectiveness_score': 0.85,
                    'next_maintenance_due': 8760.0,  # Annual
                    'parts_used': ['Adjustment tools', 'Thrust collar']
                }
            else:
                return {
                    'success': False,
                    'duration_hours': 0.0,
                    'work_performed': 'Thrust bearing adjustment not applicable',
                    'error_message': f'Bearing type {self.config.bearing_type} is not a thrust bearing',
                    'effectiveness_score': 0.0
                }
        
        elif maintenance_type == "turbine_oil_change":
            # Perform oil change (affects oil contamination)
            original_contamination = self.oil_contamination_level
            
            # Reset oil contamination to clean levels
            self.oil_contamination_level = 1.0  # Clean oil
            
            # Improve efficiency slightly
            self.efficiency_factor = min(1.0, self.efficiency_factor + 0.01)
            
            # Reduce temperature slightly
            self.metal_temperature = max(80.0, self.metal_temperature - 2.0)
            
            contamination_reduction = original_contamination - self.oil_contamination_level
            
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': 'Turbine oil change completed',
                'findings': f"Reduced oil contamination from {original_contamination:.1f}ppm to {self.oil_contamination_level:.1f}ppm",
                'performance_improvement': (contamination_reduction / max(1.0, original_contamination)) * 100.0,
                'effectiveness_score': 0.95,
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Turbine oil', 'Oil filters', 'Drain plugs']
            }
        
        elif maintenance_type == "routine_maintenance":
            # Perform routine maintenance
            # Minor improvements across all parameters
            self.efficiency_factor = min(1.0, self.efficiency_factor + 0.01)
            self.oil_contamination_level = max(1.0, self.oil_contamination_level - 0.5)
            self.metal_temperature = max(80.0, self.metal_temperature - 1.0)
            
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': 'Routine bearing maintenance completed',
                'findings': 'General maintenance activities completed',
                'effectiveness_score': 0.7,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['General maintenance supplies']
            }
        
        else:
            # Unknown maintenance type
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f'Unknown maintenance type: {maintenance_type}',
                'error_message': f'Maintenance type {maintenance_type} not supported for bearing',
                'effectiveness_score': 0.0
            }
    
    def reset(self) -> None:
        """Reset bearing to initial conditions"""
        self.current_load = 0.0
        self.oil_temperature = 85.0
        self.metal_temperature = 90.0
        self.oil_flow_rate = 10.0
        self.oil_pressure = 0.2
        self.vibration_displacement = 0.0
        self.vibration_velocity = 0.0
        self.vibration_acceleration = 0.0
        self.operating_hours = 0.0
        self.load_cycles = 0
        self.wear_factor = 1.0
        self.efficiency_factor = 1.0
        self.clearance_increase = 0.0
        self.oil_contamination_level = 0.0
        self.external_oil_temp = False
        self.external_oil_temperature = 85.0


class VibrationMonitor:
    """
    Vibration monitoring system - analogous to specialized monitoring in condenser
    
    This model implements:
    1. Multi-frequency vibration analysis
    2. Critical speed monitoring
    3. Trend analysis and prediction
    4. Alarm and trip logic
    """
    
    def __init__(self, config: RotorDynamicsConfig):
        """Initialize vibration monitor"""
        self.config = config
        
        # Current vibration state
        self.displacement_x = 0.0                # mils X-direction displacement
        self.displacement_y = 0.0                # mils Y-direction displacement
        self.velocity_x = 0.0                    # in/s X-direction velocity
        self.velocity_y = 0.0                    # in/s Y-direction velocity
        self.acceleration_x = 0.0                # g X-direction acceleration
        self.acceleration_y = 0.0                # g Y-direction acceleration
        
        # Frequency analysis
        self.fundamental_frequency = 60.0        # Hz fundamental frequency (1X)
        self.harmonic_amplitudes = [0.0] * 10    # Harmonic amplitudes (1X to 10X)
        self.subsynchronous_amplitude = 0.0      # Subsynchronous vibration
        
        # Trend tracking
        self.vibration_history = []              # Historical vibration data
        self.trend_slope = 0.0                   # Vibration trend (mils/hour)
        
        # Alarm states
        self.displacement_alarm = False
        self.velocity_alarm = False
        self.acceleration_alarm = False
        self.critical_speed_alarm = False
        
    def calculate_vibration_response(self,
                                   rotor_speed: float,
                                   unbalance_force: float,
                                   bearing_stiffness: float,
                                   bearing_damping: float,
                                   thermal_bow: float) -> Dict[str, float]:
        """
        Calculate vibration response to various excitation sources
        
        Args:
            rotor_speed: Current rotor speed (RPM)
            unbalance_force: Unbalance force magnitude (N)
            bearing_stiffness: Effective bearing stiffness (N/m)
            bearing_damping: Effective bearing damping (N⋅s/m)
            thermal_bow: Thermal bow magnitude (mm)
            
        Returns:
            Dictionary with vibration response
        """
        # Convert speed to frequency
        rotation_frequency = rotor_speed / 60.0  # Hz
        omega = 2 * np.pi * rotation_frequency   # rad/s
        
        # System natural frequency
        rotor_mass = 15000.0  # kg
        natural_frequency = np.sqrt(bearing_stiffness / rotor_mass) / (2 * np.pi)  # Hz
        
        # Frequency ratio
        frequency_ratio = rotation_frequency / natural_frequency
        
        # Damping ratio
        critical_damping = 2 * np.sqrt(bearing_stiffness * rotor_mass)
        damping_ratio = bearing_damping / critical_damping
        
        # Unbalance response (1X vibration)
        denominator = np.sqrt((1 - frequency_ratio**2)**2 + (2 * damping_ratio * frequency_ratio)**2)
        unbalance_response = unbalance_force / bearing_stiffness / denominator
        
        # Thermal bow response (1X vibration)
        thermal_response = thermal_bow * frequency_ratio**2 / denominator
        
        # Total 1X vibration
        total_1x = unbalance_response + thermal_response
        
        # Convert to displacement (mm to mils)
        displacement_1x = total_1x * 39.37  # mils
        
        # Calculate velocity and acceleration
        velocity_1x = displacement_1x * omega / 1000.0  # in/s
        acceleration_1x = velocity_1x * omega / 9.81    # g
        
        # Higher harmonics (simplified)
        displacement_2x = displacement_1x * 0.1  # 2X typically 10% of 1X
        displacement_3x = displacement_1x * 0.05 # 3X typically 5% of 1X
        
        # Total vibration (RMS)
        total_displacement = np.sqrt(displacement_1x**2 + displacement_2x**2 + displacement_3x**2)
        total_velocity = np.sqrt(velocity_1x**2 + (velocity_1x * 0.1)**2 + (velocity_1x * 0.05)**2)
        total_acceleration = np.sqrt(acceleration_1x**2 + (acceleration_1x * 0.1)**2 + (acceleration_1x * 0.05)**2)
        
        # Update state
        self.displacement_x = total_displacement
        self.displacement_y = total_displacement * 0.8  # Assume some phase difference
        self.velocity_x = total_velocity
        self.velocity_y = total_velocity * 0.8
        self.acceleration_x = total_acceleration
        self.acceleration_y = total_acceleration * 0.8
        
        # Update harmonic amplitudes
        self.harmonic_amplitudes[0] = displacement_1x  # 1X
        self.harmonic_amplitudes[1] = displacement_2x  # 2X
        self.harmonic_amplitudes[2] = displacement_3x  # 3X
        
        return {
            'displacement_total': total_displacement,
            'velocity_total': total_velocity,
            'acceleration_total': total_acceleration,
            'displacement_1x': displacement_1x,
            'displacement_2x': displacement_2x,
            'frequency_ratio': frequency_ratio,
            'natural_frequency': natural_frequency
        }
    
    def check_critical_speeds(self, rotor_speed: float) -> Dict[str, bool]:
        """
        Check proximity to critical speeds
        
        Args:
            rotor_speed: Current rotor speed (RPM)
            
        Returns:
            Dictionary with critical speed warnings
        """
        warnings = {}
        
        # Check first critical speed
        first_critical_margin = abs(rotor_speed - self.config.first_critical_speed) / self.config.first_critical_speed
        warnings['first_critical_warning'] = first_critical_margin < self.config.critical_speed_margin
        
        # Check second critical speed
        second_critical_margin = abs(rotor_speed - self.config.second_critical_speed) / self.config.second_critical_speed
        warnings['second_critical_warning'] = second_critical_margin < self.config.critical_speed_margin
        
        # Overall critical speed alarm
        self.critical_speed_alarm = warnings['first_critical_warning'] or warnings['second_critical_warning']
        warnings['critical_speed_alarm'] = self.critical_speed_alarm
        
        return warnings
    
    def update_alarms(self) -> Dict[str, bool]:
        """Update vibration alarms"""
        # Displacement alarms
        max_displacement = max(abs(self.displacement_x), abs(self.displacement_y))
        self.displacement_alarm = max_displacement > self.config.displacement_alarm
        displacement_trip = max_displacement > self.config.displacement_trip
        
        # Velocity alarms
        max_velocity = max(abs(self.velocity_x), abs(self.velocity_y))
        self.velocity_alarm = max_velocity > self.config.velocity_alarm
        velocity_trip = max_velocity > self.config.velocity_trip
        
        # Acceleration alarms
        max_acceleration = max(abs(self.acceleration_x), abs(self.acceleration_y))
        self.acceleration_alarm = max_acceleration > self.config.acceleration_alarm
        acceleration_trip = max_acceleration > self.config.acceleration_trip
        
        return {
            'displacement_alarm': self.displacement_alarm,
            'displacement_trip': displacement_trip,
            'velocity_alarm': self.velocity_alarm,
            'velocity_trip': velocity_trip,
            'acceleration_alarm': self.acceleration_alarm,
            'acceleration_trip': acceleration_trip,
            'critical_speed_alarm': self.critical_speed_alarm
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get vibration state for monitoring"""
        return {
            'vibration_displacement_x': self.displacement_x,
            'vibration_displacement_y': self.displacement_y,
            'vibration_velocity_x': self.velocity_x,
            'vibration_velocity_y': self.velocity_y,
            'vibration_acceleration_x': self.acceleration_x,
            'vibration_acceleration_y': self.acceleration_y,
            'vibration_1x_amplitude': self.harmonic_amplitudes[0],
            'vibration_2x_amplitude': self.harmonic_amplitudes[1],
            'vibration_trend_slope': self.trend_slope
        }


class RotorDynamicsModel:
    """
    Complete rotor dynamics system - analogous to main condenser physics
    
    This model implements:
    1. Rotor speed and acceleration dynamics
    2. Multiple bearing coordination
    3. Vibration monitoring and analysis
    4. Thermal effects and stress analysis
    5. Protection system integration
    """
    
    def __init__(self, config: Optional[RotorDynamicsConfig] = None):
        """Initialize rotor dynamics model"""
        if config is None:
            config = RotorDynamicsConfig()
        
        self.config = config
        
        # Create bearing objects
        self.bearings = {}
        if hasattr(config, 'bearing_configs') and config.bearing_configs:
            for bearing_config in config.bearing_configs:
                self.bearings[bearing_config.bearing_id] = BearingModel(bearing_config)
        else:
            # Create default bearing configuration
            self._create_default_bearings()
        
        # Vibration monitoring
        self.vibration_monitor = VibrationMonitor(config)
        
        # Rotor state
        self.rotor_speed = 0.0                   # RPM current speed
        self.rotor_acceleration = 0.0            # RPM/s acceleration
        self.target_speed = 0.0                  # RPM target speed
        
        # Mechanical state
        self.total_torque = 0.0                  # N⋅m total applied torque
        self.friction_torque = 0.0               # N⋅m friction torque
        self.net_torque = 0.0                    # N⋅m net torque
        
        # Thermal state
        self.rotor_temperature = 450.0           # °C average rotor temperature
        self.thermal_expansion = 0.0             # mm thermal expansion
        self.thermal_bow = 0.0                   # mm thermal bow
        
        # Performance tracking
        self.operating_hours = 0.0               # Total operating hours
        self.startup_cycles = 0                  # Number of startup cycles
        self.overspeed_events = 0                # Number of overspeed events
        
    def _create_default_bearings(self):
        """Create default bearing configuration using unified config parameters"""
        bearing_locations = ["hp_inlet", "hp_outlet", "lp_center", "lp_outlet"]
        bearing_types = ["journal", "journal", "thrust", "journal"]
        
        for i in range(self.config.num_bearings):
            bearing_id = f"TB-{i+1:03d}"
            location = bearing_locations[i] if i < len(bearing_locations) else f"bearing_{i+1}"
            bearing_type = bearing_types[i] if i < len(bearing_types) else "journal"
            
            # Create bearing config dict from unified config parameters
            bearing_config_dict = {
                'bearing_id': bearing_id,
                'bearing_type': bearing_type,
                'location': location,
                'design_load_capacity': self.config.design_load_capacity,
                'design_speed': 3600.0,  # RPM
                'oil_film_thickness': 0.05,  # mm
                'bearing_clearance': self.config.bearing_clearance,
                'max_load': self.config.design_load_capacity * 1.2,  # 20% margin
                'max_temperature': 120.0,  # °C
                'max_vibration': self.config.vibration_trip_level,
                'stiffness_coefficient': self.config.bearing_stiffness,
                'damping_coefficient': self.config.bearing_damping,
                'friction_coefficient': self.config.friction_coefficient
            }
            
            self.bearings[bearing_id] = BearingModel(bearing_id, bearing_config_dict)
    
    def calculate_rotor_dynamics(self,
                               applied_torque: float,
                               target_speed: float,
                               dt: float) -> Dict[str, float]:
        """
        Calculate rotor speed and acceleration dynamics
        
        Args:
            applied_torque: Applied torque from steam (N⋅m)
            target_speed: Target rotor speed (RPM)
            dt: Time step (hours)
            
        Returns:
            Dictionary with rotor dynamics results
        """
        # Convert time step to seconds
        dt_seconds = dt * 3600.0
        
        # Calculate friction torque from bearings
        total_friction = 0.0
        for bearing in self.bearings.values():
            bearing_friction = (bearing.current_load * 1000.0 * 
                              bearing.config.friction_coefficient * 
                              bearing.config.bearing_clearance / 1000.0)  # N⋅m
            total_friction += bearing_friction
        
        self.friction_torque = total_friction
        
        # Net torque
        self.net_torque = applied_torque - self.friction_torque
        
        # Angular acceleration (Newton's second law for rotation)
        # τ = I⋅α, where α is in rad/s²
        angular_acceleration = self.net_torque / self.config.rotor_inertia  # rad/s²
        
        # Convert to RPM/s
        self.rotor_acceleration = angular_acceleration * 60.0 / (2 * np.pi)  # RPM/s
        
        # Update rotor speed
        speed_change = self.rotor_acceleration * dt_seconds  # RPM
        self.rotor_speed += speed_change
        
        # Apply speed limits
        self.rotor_speed = max(0.0, min(self.rotor_speed, self.config.max_speed))
        
        # Track overspeed events
        if self.rotor_speed > self.config.max_speed * 0.99:
            self.overspeed_events += 1
        
        return {
            'rotor_speed': self.rotor_speed,
            'rotor_acceleration': self.rotor_acceleration,
            'net_torque': self.net_torque,
            'friction_torque': self.friction_torque,
            'angular_acceleration': angular_acceleration,
            'speed_change': speed_change
        }
    
    def calculate_thermal_effects(self,
                                steam_temperature: float,
                                ambient_temperature: float,
                                dt: float) -> Dict[str, float]:
        """
        Calculate thermal expansion and bow effects
        
        Args:
            steam_temperature: Average steam temperature (°C)
            ambient_temperature: Ambient temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with thermal effects
        """
        # Rotor temperature (first-order lag)
        time_constant = 2.0  # hours thermal time constant
        temp_change = (steam_temperature - self.rotor_temperature) / time_constant * dt
        self.rotor_temperature += temp_change
        
        # Thermal expansion
        temp_difference = self.rotor_temperature - ambient_temperature
        expansion = (temp_difference * self.config.thermal_expansion_coefficient * 
                    self.config.rotor_length * 1000.0)  # mm
        self.thermal_expansion = expansion
        
        # Thermal bow (due to temperature gradients)
        if self.rotor_speed < 100.0:  # Thermal bow mainly occurs at low speeds
            thermal_gradient = abs(temp_change) / dt if dt > 0 else 0
            bow_increase = thermal_gradient * 0.001 * dt  # mm thermal bow
            self.thermal_bow = min(self.config.thermal_bow_limit, 
                                 self.thermal_bow + bow_increase)
        else:
            # Thermal bow reduces at operating speed
            self.thermal_bow *= 0.95
        
        return {
            'rotor_temperature': self.rotor_temperature,
            'thermal_expansion': self.thermal_expansion,
            'thermal_bow': self.thermal_bow,
            'temperature_change': temp_change
        }
    
    def update_state(self,
                    applied_torque: float,
                    target_speed: float,
                    steam_temperature: float,
                    steam_thrust: float,
                    oil_inlet_temperature: float,
                    oil_contamination: float,
                    dt: float) -> Dict[str, float]:
        """
        Update complete rotor dynamics state
        
        Args:
            applied_torque: Applied torque from turbine (N⋅m)
            target_speed: Target rotor speed (RPM)
            steam_temperature: Steam temperature (°C)
            steam_thrust: Steam thrust force (kN)
            oil_inlet_temperature: Bearing oil inlet temperature (°C)
            oil_contamination: Oil contamination level (ppm)
            dt: Time step (hours)
            
        Returns:
            Dictionary with complete rotor dynamics results
        """
        # Calculate rotor dynamics
        rotor_results = self.calculate_rotor_dynamics(applied_torque, target_speed, dt)
        
        # Calculate thermal effects
        thermal_results = self.calculate_thermal_effects(steam_temperature, 25.0, dt)
        
        # Update individual bearings
        bearing_results = {}
        total_bearing_load = 0.0
        max_bearing_temp = 0.0
        
        rotor_weight_per_bearing = self.config.rotor_mass * 9.81 / 1000.0 / len(self.bearings)  # kN per bearing
        
        for bearing_id, bearing in self.bearings.items():
            # Calculate bearing loads
            load_results = bearing.calculate_bearing_loads(
                rotor_weight_per_bearing, steam_thrust / len(self.bearings),
                self.thermal_expansion, self.rotor_speed
            )
            
            # Calculate bearing temperatures
            temp_results = bearing.calculate_bearing_temperature(
                oil_inlet_temperature, bearing.current_load, self.rotor_speed, dt
            )
            
            # Update bearing wear
            wear_results = bearing.update_bearing_wear(
                bearing.current_load, oil_contamination, dt
            )
            
            bearing_results[bearing_id] = {
                **load_results,
                **temp_results,
                **wear_results
            }
            
            total_bearing_load += bearing.current_load
            max_bearing_temp = max(max_bearing_temp, bearing.metal_temperature)
        
        # Calculate vibration response
        # Average bearing stiffness and damping
        avg_stiffness = sum(b.config.stiffness_coefficient for b in self.bearings.values()) / len(self.bearings)
        avg_damping = sum(b.config.damping_coefficient for b in self.bearings.values()) / len(self.bearings)
        
        # Unbalance force (simplified)
        unbalance_force = (self.rotor_speed / 60.0) ** 2 * 0.1  # N
        
        vibration_results = self.vibration_monitor.calculate_vibration_response(
            self.rotor_speed, unbalance_force, avg_stiffness, avg_damping, self.thermal_bow
        )
        
        # Check critical speeds
        critical_speed_warnings = self.vibration_monitor.check_critical_speeds(self.rotor_speed)
        
        # Update vibration alarms
        vibration_alarms = self.vibration_monitor.update_alarms()
        
        # Update operating hours
        self.operating_hours += dt
        
        return {
            # Rotor dynamics
            'rotor_speed': self.rotor_speed,
            'rotor_acceleration': self.rotor_acceleration,
            'net_torque': self.net_torque,
            'friction_torque': self.friction_torque,
            
            # Thermal effects
            'rotor_temperature': self.rotor_temperature,
            'thermal_expansion': self.thermal_expansion,
            'thermal_bow': self.thermal_bow,
            
            # Bearing performance
            'total_bearing_load': total_bearing_load,
            'max_bearing_temperature': max_bearing_temp,
            'bearing_results': bearing_results,
            
            # Vibration monitoring
            'vibration_displacement': vibration_results['displacement_total'],
            'vibration_velocity': vibration_results['velocity_total'],
            'vibration_acceleration': vibration_results['acceleration_total'],
            'vibration_1x': vibration_results['displacement_1x'],
            'natural_frequency': vibration_results['natural_frequency'],
            
            # Alarms and warnings
            'critical_speed_warnings': critical_speed_warnings,
            'vibration_alarms': vibration_alarms,
            
            # Operating time
            'operating_hours': self.operating_hours,
            'overspeed_events': self.overspeed_events
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'rotor_speed': self.rotor_speed,
            'rotor_acceleration': self.rotor_acceleration,
            'rotor_temperature': self.rotor_temperature,
            'thermal_expansion': self.thermal_expansion,
            'thermal_bow': self.thermal_bow,
            'net_torque': self.net_torque,
            'friction_torque': self.friction_torque,
            'operating_hours': self.operating_hours,
            'overspeed_events': self.overspeed_events
        }
        
        # Add bearing states
        for bearing in self.bearings.values():
            state_dict.update(bearing.get_state_dict())
        
        # Add vibration states
        state_dict.update(self.vibration_monitor.get_state_dict())
        
        return state_dict
    
    def reset(self) -> None:
        """Reset rotor dynamics to initial conditions"""
        self.rotor_speed = 0.0
        self.rotor_acceleration = 0.0
        self.target_speed = 0.0
        self.total_torque = 0.0
        self.friction_torque = 0.0
        self.net_torque = 0.0
        self.rotor_temperature = 450.0
        self.thermal_expansion = 0.0
        self.thermal_bow = 0.0
        self.operating_hours = 0.0
        self.startup_cycles = 0
        self.overspeed_events = 0
        
        # Reset bearings
        for bearing in self.bearings.values():
            bearing.reset()
        
        # Reset vibration monitor
        self.vibration_monitor.displacement_x = 0.0
        self.vibration_monitor.displacement_y = 0.0
        self.vibration_monitor.velocity_x = 0.0
        self.vibration_monitor.velocity_y = 0.0
        self.vibration_monitor.acceleration_x = 0.0
        self.vibration_monitor.acceleration_y = 0.0
        self.vibration_monitor.harmonic_amplitudes = [0.0] * 10
        self.vibration_monitor.vibration_history = []
        self.vibration_monitor.trend_slope = 0.0
        self.vibration_monitor.displacement_alarm = False
        self.vibration_monitor.velocity_alarm = False
        self.vibration_monitor.acceleration_alarm = False
        self.vibration_monitor.critical_speed_alarm = False


# Example usage and testing
if __name__ == "__main__":
    # Create rotor dynamics system with default configuration
    rotor_dynamics = RotorDynamicsModel()
    
    print("Rotor Dynamics Model - Parameter Validation")
    print("=" * 50)
    print(f"System ID: {rotor_dynamics.config.system_id}")
    print(f"Number of Bearings: {len(rotor_dynamics.bearings)}")
    print(f"Rotor Mass: {rotor_dynamics.config.rotor_mass} kg")
    print(f"Rotor Inertia: {rotor_dynamics.config.rotor_inertia} kg⋅m²")
    print(f"Rated Speed: {rotor_dynamics.config.rated_speed} RPM")
    print(f"Max Speed: {rotor_dynamics.config.max_speed} RPM")
    print()
    
    # Test rotor dynamics operation
    for hour in range(48):  # 48 hours
        # Simulate startup and operation
        if hour < 2:
            # Startup phase
            applied_torque = 50000.0  # N⋅m startup torque
            target_speed = 1800.0     # RPM intermediate speed
        elif hour < 4:
            # Acceleration to rated speed
            applied_torque = 30000.0  # N⋅m
            target_speed = 3600.0     # RPM rated speed
        else:
            # Normal operation
            applied_torque = 25000.0  # N⋅m steady-state torque
            target_speed = 3600.0     # RPM rated speed
        
        result = rotor_dynamics.update_state(
            applied_torque=applied_torque,
            target_speed=target_speed,
            steam_temperature=285.0,    # °C steam temperature
            steam_thrust=100.0,         # kN steam thrust
            oil_inlet_temperature=40.0, # °C oil inlet temperature
            oil_contamination=5.0,      # ppm oil contamination
            dt=1.0                      # 1 hour time step
        )
        
        if hour % 8 == 0:  # Print every 8 hours
            print(f"Hour {hour}:")
            print(f"  Rotor Speed: {result['rotor_speed']:.0f} RPM")
            print(f"  Rotor Temperature: {result['rotor_temperature']:.1f} °C")
            print(f"  Thermal Expansion: {result['thermal_expansion']:.3f} mm")
            print(f"  Vibration (1X): {result['vibration_1x']:.2f} mils")
            print(f"  Total Bearing Load: {result['total_bearing_load']:.1f} kN")
            print(f"  Max Bearing Temp: {result['max_bearing_temperature']:.1f} °C")
            
            # Show bearing status
            for bearing_id, bearing_result in result['bearing_results'].items():
                print(f"    {bearing_id}: Load {bearing_result['total_load']:.1f} kN, "
                      f"Temp {bearing_result['metal_temperature']:.1f} °C, "
                      f"Wear {bearing_result['wear_factor']:.3f}")
            
            # Show alarms
            if any(result['vibration_alarms'].values()):
                active_alarms = [k for k, v in result['vibration_alarms'].items() if v]
                print(f"  Active Alarms: {', '.join(active_alarms)}")
            
            print()
    
    print(f"Final State Summary:")
    final_state = rotor_dynamics.get_state_dict()
    print(f"  Operating Hours: {final_state['operating_hours']:.0f}")
    print(f"  Overspeed Events: {final_state['overspeed_events']}")
    print(f"  Final Speed: {final_state['rotor_speed']:.0f} RPM")
    print(f"  Thermal Bow: {final_state['thermal_bow']:.3f} mm")
