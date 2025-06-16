"""
Secondary Reactor Physics System

This module provides the integrated secondary reactor physics system for PWR plants,
combining steam generators, turbines, and condensers into a complete steam cycle model.
Enhanced with state management integration for comprehensive data collection.
"""

import numpy as np
from typing import Dict, Any, Optional
import pandas as pd

# Import state management interfaces
from simulator.state import StateProviderMixin

from .steam_generator import (
    SteamGenerator, 
    SteamGeneratorConfig,
    EnhancedSteamGeneratorPhysics,
    EnhancedSteamGeneratorConfig
)
from .turbine import (
    # Enhanced turbine physics
    EnhancedTurbinePhysics,
    EnhancedTurbineConfig,
    
    # Individual component systems
    TurbineStageSystem,
    TurbineStage,
    TurbineStageConfig,
    RotorDynamicsModel,
    RotorDynamicsConfig
)

# Legacy turbine removed - now using enhanced turbine physics
from .condenser import EnhancedCondenserPhysics, EnhancedCondenserConfig
from .feedwater import (
    # Enhanced feedwater physics
    EnhancedFeedwaterPhysics,
    EnhancedFeedwaterConfig,
    
    # Individual component systems
    FeedwaterPumpSystem,
    FeedwaterPump,
    FeedwaterPumpState,
    FeedwaterPumpConfig,
    ThreeElementControl,
    ThreeElementConfig,
    WaterQualityModel,
    WaterQualityConfig,
    PerformanceDiagnostics,
    FeedwaterProtectionSystem,
    FeedwaterProtectionConfig
)

__all__ = [
    # Steam Generator System
    'SteamGenerator',
    'SteamGeneratorConfig',
    'EnhancedSteamGeneratorPhysics',
    'EnhancedSteamGeneratorConfig',
    
    # Enhanced Turbine System
    'EnhancedTurbinePhysics',
    'EnhancedTurbineConfig',
    'TurbineStageSystem',
    'TurbineStage',
    'TurbineStageConfig',
    'RotorDynamicsModel',
    'RotorDynamicsConfig',
    
    # Legacy turbine removed - now using enhanced turbine physics only
    
    # Enhanced Condenser
    'EnhancedCondenserPhysics',
    'EnhancedCondenserConfig',
    
    # Enhanced Feedwater System
    'EnhancedFeedwaterPhysics',
    'EnhancedFeedwaterConfig',
    'FeedwaterPumpSystem',
    'FeedwaterPump',
    'FeedwaterPumpState',
    'FeedwaterPumpConfig',
    'ThreeElementControl',
    'ThreeElementConfig',
    'WaterQualityModel',
    'WaterQualityConfig',
    'PerformanceDiagnostics',
    'FeedwaterProtectionSystem',
    'FeedwaterProtectionConfig',
    
    # Integrated System
    'SecondaryReactorPhysics'
]




class SecondaryReactorPhysics(StateProviderMixin):
    """
    Integrated secondary reactor physics system with state management integration
    
    This class combines steam generators, turbines, and condensers to model
    the complete secondary side of a PWR nuclear power plant.
    
    The system models:
    1. Heat transfer from primary to secondary in steam generators
    2. Steam expansion and power generation in turbines
    3. Steam condensation and heat rejection in condensers
    4. Complete mass and energy balance across the steam cycle
    5. Control system interactions and feedback loops
    6. Comprehensive state management for all subsystems
    
    Implements StateProvider interface for automatic state collection.
    """
    
    def __init__(self, 
                 num_steam_generators: int = 3,
                 sg_config: SteamGeneratorConfig = None,
                 turbine_config: EnhancedTurbineConfig = None,
                 condenser_config: EnhancedCondenserConfig = None):
        """
        Initialize integrated secondary reactor physics
        
        Args:
            num_steam_generators: Number of steam generators (typically 2-4)
            sg_config: Steam generator configuration
            turbine_config: Enhanced turbine configuration  
            condenser_config: Condenser configuration
        """
        self.num_steam_generators = num_steam_generators
        
        # Initialize enhanced steam generator system
        enhanced_sg_config = EnhancedSteamGeneratorConfig(
            num_steam_generators=num_steam_generators
        )
        if sg_config is not None:
            enhanced_sg_config.sg_system_config.sg_config = sg_config
        
        self.steam_generator_system = EnhancedSteamGeneratorPhysics(enhanced_sg_config)
        
        # Use enhanced turbine physics instead of legacy
        self.turbine = EnhancedTurbinePhysics(turbine_config)
        self.condenser = EnhancedCondenserPhysics(condenser_config)
        
        # Initialize enhanced feedwater system
        from .feedwater import EnhancedFeedwaterPhysics, EnhancedFeedwaterConfig
        feedwater_config = EnhancedFeedwaterConfig(num_steam_generators=num_steam_generators)
        self.feedwater_system = EnhancedFeedwaterPhysics(feedwater_config)
        
        # System state variables
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        self.total_feedwater_flow = 0.0
        
        # Control parameters
        self.load_demand = 100.0  # % rated load
        self.feedwater_temperature = 227.0  # °C
        self.cooling_water_temperature = 25.0  # °C
        
    def update_system(self,
                     primary_conditions: dict,
                     control_inputs: dict,
                     dt: float) -> dict:
        """
        Update the complete secondary system for one time step
        
        Args:
            primary_conditions: Dictionary with primary side conditions for each SG
                - 'sg_X_inlet_temp': Primary inlet temperature for SG X (°C)
                - 'sg_X_outlet_temp': Primary outlet temperature for SG X (°C)
                - 'sg_X_flow': Primary flow rate for SG X (kg/s)
            control_inputs: Dictionary with control system inputs
                - 'load_demand': Electrical load demand (% rated)
                - 'feedwater_temp': Feedwater temperature (°C)
                - 'cooling_water_temp': Cooling water inlet temperature (°C)
                - 'cooling_water_flow': Cooling water flow rate (kg/s)
                - 'vacuum_pump_operation': Vacuum pump operation (0-1)
            dt: Time step (s)
            
        Returns:
            Dictionary with complete system state and performance
        """
        # Extract control inputs
        self.load_demand = control_inputs.get('load_demand', 100.0)
        self.feedwater_temperature = control_inputs.get('feedwater_temp', 227.0)
        self.cooling_water_temperature = control_inputs.get('cooling_water_temp', 25.0)
        cooling_water_flow = control_inputs.get('cooling_water_flow', 45000.0)
        vacuum_pump_operation = control_inputs.get('vacuum_pump_operation', 1.0)
        
        # First, check feedwater system availability (using previous state)
        feedwater_system_available = getattr(self.feedwater_system, 'system_availability', True)
        
        # Update enhanced steam generator system
        # Prepare primary conditions for enhanced steam generator system
        enhanced_primary_conditions = {
            'inlet_temps': [primary_conditions.get(f'sg_{i+1}_inlet_temp', 327.0) for i in range(self.num_steam_generators)],
            'outlet_temps': [primary_conditions.get(f'sg_{i+1}_outlet_temp', 293.0) for i in range(self.num_steam_generators)],
            'flow_rates': [primary_conditions.get(f'sg_{i+1}_flow', 5700.0) for i in range(self.num_steam_generators)]
        }
        
        # Calculate total steam demand based on load
        design_total_steam_flow = self.steam_generator_system.config.design_total_steam_flow
        total_steam_demand = design_total_steam_flow * (self.load_demand / 100.0)
        
        # FIXED: Ensure minimum reasonable steam flow even with feedwater issues
        if not feedwater_system_available:
            total_steam_demand = max(total_steam_demand * 0.5, design_total_steam_flow * 0.3)
        
        steam_demands = {
            'total_steam_flow': total_steam_demand,
            'steam_pressure': 6.895  # Target steam pressure
        }
        
        enhanced_system_conditions = {
            'feedwater_temperature': self.feedwater_temperature,
            'load_demand': self.load_demand / 100.0  # Convert to fraction
        }
        
        # Update enhanced steam generator system
        sg_system_result = self.steam_generator_system.update_system(
            primary_conditions=enhanced_primary_conditions,
            steam_demands=steam_demands,
            system_conditions=enhanced_system_conditions,
            control_inputs=control_inputs,
            dt=dt
        )
        
        # Extract results from enhanced system
        total_heat_transfer = sg_system_result['total_thermal_power']
        total_steam_production = sg_system_result['total_steam_flow']
        sg_results = sg_system_result['sg_individual_results']
        
        # Calculate average steam conditions entering turbine from enhanced system results
        if len(sg_results) > 0:
            avg_steam_pressure = sg_system_result['average_steam_pressure']
            avg_steam_temperature = sg_system_result['average_steam_temperature']
            avg_steam_quality = sg_system_result['average_steam_quality']
            
            # FIXED: Ensure steam temperature is realistic for turbine operation
            # Steam temperature should be saturation temperature at steam pressure
            # For superheated steam in PWR, add small superheat margin
            sat_temp_at_pressure = self._saturation_temperature(avg_steam_pressure)
            avg_steam_temperature = max(avg_steam_temperature, sat_temp_at_pressure)
            '''
            print(f"DEBUG: Steam Generator Output:")
            print(f"  Steam Pressure: {avg_steam_pressure:.2f} MPa")
            print(f"  Steam Temperature: {avg_steam_temperature:.1f}°C")
            print(f"  Saturation Temperature: {sat_temp_at_pressure:.1f}°C")
            print(f"  Steam Quality: {avg_steam_quality:.3f}")
            '''
        else:
            avg_steam_pressure = 6.895
            avg_steam_temperature = 285.8
            avg_steam_quality = 0.99
        
        # Total steam flow to turbine
        total_steam_flow = sum(sg_result['steam_flow_rate'] for sg_result in sg_results)
        
        # Update turbine
        turbine_result = self.turbine.update_state(
            steam_pressure=avg_steam_pressure,
            steam_temperature=avg_steam_temperature,
            steam_flow=total_steam_flow,
            steam_quality=avg_steam_quality,
            load_demand=self.load_demand,
            dt=dt
        )
        
        # Update condenser with turbine exhaust
        # Use the saturation temperature at condenser pressure for steam inlet temperature
        condenser_steam_temp = 39.0  # Saturation temperature at 0.007 MPa
        
        # Enhanced condenser parameters from control inputs with defaults
        makeup_water_quality = control_inputs.get('makeup_water_quality', {
            'tds': 300.0,
            'hardness': 100.0,
            'chloride': 30.0,
            'ph': 7.2,
            'dissolved_oxygen': 8.0
        })
        
        chemical_doses = control_inputs.get('chemical_doses', {
            'chlorine': 1.0,
            'antiscalant': 5.0,
            'corrosion_inhibitor': 10.0,
            'biocide': 0.0
        })
        
        motive_steam_pressure = control_inputs.get('motive_steam_pressure', 1.2)  # MPa
        motive_steam_temperature = control_inputs.get('motive_steam_temperature', 185.0)  # °C
        
        condenser_result = self.condenser.update_state(
            steam_pressure=turbine_result['condenser_pressure'],
            steam_temperature=condenser_steam_temp,
            steam_flow=turbine_result['effective_steam_flow'],
            steam_quality=0.90,  # Typical LP turbine exhaust quality
            cooling_water_flow=cooling_water_flow,
            cooling_water_temp_in=self.cooling_water_temperature,
            motive_steam_pressure=motive_steam_pressure,
            motive_steam_temperature=motive_steam_temperature,
            makeup_water_quality=makeup_water_quality,
            chemical_doses=chemical_doses,
            dt=dt / 3600.0  # Convert seconds to hours for enhanced condenser
        )
        
        # Prepare system conditions for feedwater pump system
        # FIXED: Feedwater pumps operate on condensate at condenser temperature (~40°C),
        # not the final feedwater temperature (227°C) which is after feedwater heaters
        condensate_temp = condenser_result.get('condensate_temperature', 40.0)  # °C
        
        feedwater_system_conditions = {
            'sg_pressure': avg_steam_pressure,
            'feedwater_temperature': condensate_temp,  # Use condensate temp, not final feedwater temp
            'suction_pressure': condenser_result['condenser_pressure'] + 0.5,  # FIXED: Higher suction pressure from condensate pumps
            'discharge_pressure': avg_steam_pressure + 0.5,  # Steam pressure + margin
        }
        
        # Add individual steam generator levels, steam flows, steam quality, and void fractions for enhanced three-element control
        # Get data from enhanced steam generator system results
        sg_levels = sg_system_result.get('sg_levels', [12.5] * self.num_steam_generators)
        sg_steam_flows = sg_system_result.get('sg_steam_flows', [0.0] * self.num_steam_generators)
        sg_steam_qualities = sg_system_result.get('sg_steam_qualities', [0.99] * self.num_steam_generators)
        
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            sg_level = sg_levels[i] if i < len(sg_levels) else 12.5
            sg_steam_flow = sg_steam_flows[i] if i < len(sg_steam_flows) else 0.0
            sg_steam_quality = sg_steam_qualities[i] if i < len(sg_steam_qualities) else 0.99
            # Void fraction can be calculated from steam quality if needed, or use default
            sg_void_fraction = 0.45  # Default value, could be enhanced later
            
            feedwater_system_conditions[f'{sg_key}_level'] = sg_level
            feedwater_system_conditions[f'{sg_key}_steam_flow'] = sg_steam_flow
            feedwater_system_conditions[f'{sg_key}_steam_quality'] = sg_steam_quality
            feedwater_system_conditions[f'{sg_key}_void_fraction'] = sg_void_fraction
        
        # Update enhanced feedwater system
        # Prepare SG conditions for enhanced feedwater system using enhanced system results
        sg_conditions = {
            'levels': sg_system_result.get('sg_levels', [12.5] * self.num_steam_generators),
            'pressures': sg_system_result.get('sg_pressures', [6.895] * self.num_steam_generators),
            'steam_flows': sg_system_result.get('sg_steam_flows', [0.0] * self.num_steam_generators),
            'steam_qualities': sg_system_result.get('sg_steam_qualities', [0.99] * self.num_steam_generators)
        }
        
        steam_generator_demands = {
            'total_flow': total_steam_flow
        }
        
        feedwater_result = self.feedwater_system.update_state(
            sg_conditions=sg_conditions,
            steam_generator_demands=steam_generator_demands,
            system_conditions=feedwater_system_conditions,
            control_inputs=control_inputs,
            dt=dt / 3600.0  # Convert seconds to hours for enhanced feedwater
        )
        
        # Extract feedwater flow for mass balance
        self.total_feedwater_flow = feedwater_result['total_flow_rate']
        
        # Calculate system performance metrics
        self.total_steam_flow = total_steam_flow
        self.total_heat_transfer = total_heat_transfer
        
        # ENHANCED THERMAL POWER VALIDATION FOR ELECTRICAL GENERATION
        # Calculate actual thermal power from steam generators
        thermal_power_mw = total_heat_transfer / 1e6  # Convert to MW
        
        # Calculate primary thermal power from primary conditions
        primary_thermal_power = 0.0
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            primary_inlet_temp = primary_conditions.get(f'{sg_key}_inlet_temp', 0.0)
            primary_outlet_temp = primary_conditions.get(f'{sg_key}_outlet_temp', 0.0)
            primary_flow = primary_conditions.get(f'{sg_key}_flow', 0.0)
            
            # Calculate thermal power for this loop: Q = m_dot * cp * delta_T
            if primary_flow > 0 and primary_inlet_temp > primary_outlet_temp:
                cp_primary = 5.2  # kJ/kg/K at PWR conditions
                delta_t = primary_inlet_temp - primary_outlet_temp
                loop_thermal_power = primary_flow * cp_primary * delta_t / 1000.0  # MW
                primary_thermal_power += loop_thermal_power
        
        # CRITICAL PHYSICS VALIDATION: NO FEEDWATER = NO ELECTRICAL POWER
        # Check actual feedwater flow from the feedwater system
        actual_feedwater_flow = feedwater_result.get('total_flow_rate', 0.0)
        
        # STRICT MINIMUM THRESHOLDS FOR ELECTRICAL GENERATION
        MIN_PRIMARY_THERMAL_MW = 10.0      # Minimum primary thermal power (MW)
        MIN_SECONDARY_THERMAL_MW = 10.0    # Minimum secondary heat transfer (MW)
        MIN_STEAM_FLOW_KGS = 500.0         # Minimum steam flow (kg/s) - INCREASED
        MIN_FEEDWATER_FLOW_KGS = 500.0     # Minimum feedwater flow (kg/s) - CRITICAL - INCREASED
        MIN_STEAM_PRESSURE_MPA = 1.0       # Minimum steam pressure (MPa)
        MIN_TEMPERATURE_DELTA = 5.0        # Minimum primary-secondary temp difference (°C)
        
        # Calculate average primary-secondary temperature difference
        avg_primary_temp = 0.0
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            primary_inlet_temp = primary_conditions.get(f'{sg_key}_inlet_temp', 0.0)
            avg_primary_temp += primary_inlet_temp
        avg_primary_temp /= self.num_steam_generators if self.num_steam_generators > 0 else 1
        
        # Get average secondary temperature (saturation temperature at steam pressure)
        avg_secondary_temp = self._saturation_temperature(avg_steam_pressure)
        temp_delta = avg_primary_temp - avg_secondary_temp
        
        # COMPREHENSIVE VALIDATION CONDITIONS
        validation_failures = []
        
        if primary_thermal_power < MIN_PRIMARY_THERMAL_MW:
            validation_failures.append(f"Primary thermal power too low: {primary_thermal_power:.2f} MW < {MIN_PRIMARY_THERMAL_MW} MW")
        
        if thermal_power_mw < MIN_SECONDARY_THERMAL_MW:
            validation_failures.append(f"Secondary heat transfer too low: {thermal_power_mw:.2f} MW < {MIN_SECONDARY_THERMAL_MW} MW")
        
        if total_steam_flow < MIN_STEAM_FLOW_KGS:
            validation_failures.append(f"Steam flow too low: {total_steam_flow:.1f} kg/s < {MIN_STEAM_FLOW_KGS} kg/s")
        
        # CRITICAL: Check feedwater flow - no feedwater means no electrical power generation
        if actual_feedwater_flow < MIN_FEEDWATER_FLOW_KGS:
            validation_failures.append(f"Feedwater flow too low: {actual_feedwater_flow:.1f} kg/s < {MIN_FEEDWATER_FLOW_KGS} kg/s")
        
        if avg_steam_pressure < MIN_STEAM_PRESSURE_MPA:
            validation_failures.append(f"Steam pressure too low: {avg_steam_pressure:.2f} MPa < {MIN_STEAM_PRESSURE_MPA} MPa")
        
        if temp_delta < MIN_TEMPERATURE_DELTA:
            validation_failures.append(f"Temperature difference too low: {temp_delta:.1f}°C < {MIN_TEMPERATURE_DELTA}°C")
        
        # ENERGY CONSERVATION CHECK
        # Ensure secondary heat transfer doesn't exceed primary thermal power
        if thermal_power_mw > primary_thermal_power * 1.05:  # Allow 5% margin for calculation differences
            validation_failures.append(f"Energy conservation violation: Secondary heat transfer ({thermal_power_mw:.2f} MW) > Primary thermal power ({primary_thermal_power:.2f} MW)")
        
        # REALISTIC THERMAL EFFICIENCY CALCULATION
        # Use primary thermal power as the reference for efficiency calculation
        # This ensures energy conservation and realistic efficiency values
        
        # Get electrical power from turbine (before validation checks)
        turbine_electrical_power = turbine_result['electrical_power_net']
        
        # Calculate realistic thermal efficiency based on primary thermal power
        if primary_thermal_power > 50.0:  # Minimum meaningful thermal power
            # Realistic PWR efficiency curve based on load
            load_fraction = self.load_demand / 100.0
            
            # Typical PWR efficiency characteristics:
            # - Peak efficiency ~34% at 100% load
            # - Efficiency decreases at part load due to thermodynamic losses
            # - Minimum efficiency ~28% at 50% load
            if load_fraction >= 1.0:
                base_efficiency = 0.34  # 34% at full load
            elif load_fraction >= 0.75:
                # Linear interpolation between 75% and 100% load
                base_efficiency = 0.32 + 0.02 * (load_fraction - 0.75) / 0.25
            elif load_fraction >= 0.50:
                # Linear interpolation between 50% and 75% load  
                base_efficiency = 0.28 + 0.04 * (load_fraction - 0.50) / 0.25
            else:
                # Below 50% load, efficiency drops more rapidly
                base_efficiency = 0.20 + 0.08 * (load_fraction / 0.50)
            
            # Calculate realistic electrical power based on efficiency curve
            realistic_electrical_power = primary_thermal_power * base_efficiency
            
            # Apply validation checks - reduce power if conditions aren't met
            power_reduction_factor = 1.0
            
            # CRITICAL: Check feedwater flow first - no feedwater = no power
            if actual_feedwater_flow < MIN_FEEDWATER_FLOW_KGS:
                power_reduction_factor = 0.0  # Complete shutdown for no feedwater
            
            # Check other critical operating conditions only if feedwater is available
            if power_reduction_factor > 0.0:
                if total_steam_flow < MIN_STEAM_FLOW_KGS:
                    power_reduction_factor *= 0.5  # 50% reduction for low steam flow
                
                if avg_steam_pressure < MIN_STEAM_PRESSURE_MPA:
                    power_reduction_factor *= 0.3  # 70% reduction for low steam pressure
                
                if temp_delta < MIN_TEMPERATURE_DELTA:
                    power_reduction_factor *= 0.2  # 80% reduction for poor heat transfer
                
                # Energy conservation check
                if thermal_power_mw > primary_thermal_power * 1.05:
                    power_reduction_factor = 0.0  # Complete shutdown for energy violation
            
            # Apply reductions
            self.electrical_power_output = realistic_electrical_power * power_reduction_factor
            
            # Calculate final thermal efficiency
            if primary_thermal_power > 0:
                self.thermal_efficiency = self.electrical_power_output / primary_thermal_power
            else:
                self.thermal_efficiency = 0.0
                
        else:
            # Insufficient thermal power for electrical generation
            self.electrical_power_output = 0.0
            self.thermal_efficiency = 0.0
        # Heat rate (kJ/kWh)
        if self.electrical_power_output > 0:
            heat_rate = (total_heat_transfer / 1000.0) / (self.electrical_power_output * 1000.0) * 3600.0
        else:
            heat_rate = 0.0
        
        # Compile complete system results
        system_result = {
            # Overall system performance
            'electrical_power_mw': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'heat_rate_kj_kwh': heat_rate,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            'total_feedwater_flow': self.total_feedwater_flow,
            
            # Steam generator performance
            'sg_avg_pressure': avg_steam_pressure,
            'sg_avg_temperature': avg_steam_temperature,
            'sg_avg_steam_quality': avg_steam_quality,
            'sg_total_heat_transfer': total_heat_transfer,
            'sg_individual_results': sg_results,
            
            # Turbine performance
            'turbine_mechanical_power': turbine_result['mechanical_power'],
            'turbine_electrical_power_gross': turbine_result['electrical_power_gross'],
            'turbine_electrical_power_net': turbine_result['electrical_power_net'],
            'turbine_efficiency': turbine_result['overall_efficiency'],
            'turbine_steam_rate': turbine_result['steam_rate'],
            'turbine_hp_power': turbine_result['hp_power'],
            'turbine_lp_power': turbine_result['lp_power'],
            
            # Condenser performance
            'condenser_heat_rejection': condenser_result['heat_rejection_rate'],
            'condenser_pressure': condenser_result['condenser_pressure'],
            'condenser_cooling_water_temp_rise': condenser_result['cooling_water_temp_rise'],
            'condenser_thermal_performance': condenser_result.get('thermal_performance_factor', 1.0),
            'condenser_vacuum_efficiency': condenser_result.get('vacuum_system_efficiency', 1.0),
            
            # Feedwater pump performance
            'feedwater_total_flow': feedwater_result['total_flow_rate'],
            'feedwater_total_power': feedwater_result['total_power_consumption'],
            'feedwater_running_pumps': feedwater_result['running_pumps'],
            'feedwater_num_running_pumps': feedwater_result['num_running_pumps'],
            'feedwater_system_available': feedwater_result['system_availability'],
            'feedwater_auto_control': feedwater_result['auto_control_active'],
            'feedwater_sg_flow_distribution': feedwater_result['sg_flow_distribution'],
            
            # Control and operating conditions
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_inlet_temp': self.cooling_water_temperature,
            'cooling_water_outlet_temp': condenser_result['cooling_water_outlet_temp'],
            
            # Detailed component states
            'steam_generator_system_state': self.steam_generator_system.get_state_dict(),
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict(),
            'feedwater_state': self.feedwater_system.get_state_dict()
        }
        return system_result
    
    def get_system_state(self) -> dict:
        """Get complete system state for monitoring and logging"""
        return {
            'num_steam_generators': self.num_steam_generators,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            'electrical_power_output': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'total_feedwater_flow': self.total_feedwater_flow,
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_temperature': self.cooling_water_temperature,
            'steam_generator_system': self.steam_generator_system.get_state_dict(),
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict(),
            'feedwater_state': self.feedwater_system.get_state_dict()
        }
    
    def reset_system(self, start_at_steady_state: bool = True, thermal_power_mw: float = 3000.0) -> None:
        """
        Reset all components to initial conditions
        
        Args:
            start_at_steady_state: If True, initialize to steady-state operation (default)
            thermal_power_mw: Reactor thermal power for steady-state calculation (default 3000 MW)
        """
        # Always reset components first
        self.turbine.reset()
        self.condenser.reset()
        self.steam_generator_system.reset() 
        self.feedwater_system.reset()
        
        # Reset system-level variables
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        self.total_feedwater_flow = 0.0
        self.load_demand = 100.0
        self.feedwater_temperature = 227.0
        self.cooling_water_temperature = 25.0
        
        # Optionally initialize to steady state
        if start_at_steady_state:
            self.initialize_to_steady_state(thermal_power_mw)
    
    def initialize_to_steady_state(self, thermal_power_mw: float) -> None:
        """
        Initialize all secondary systems to steady-state operation for given thermal power
        
        This method calculates the equilibrium operating point and sets all subsystems
        to their appropriate steady-state values, eliminating startup transients.
        
        Args:
            thermal_power_mw: Reactor thermal power in MW
        """
        # Calculate equilibrium operating point
        equilibrium = self._calculate_equilibrium_point(thermal_power_mw)
        
        # Initialize each subsystem to calculated steady state
        self._initialize_steam_generators_to_steady_state(equilibrium)
        self._initialize_feedwater_system_to_steady_state(equilibrium)
        self._initialize_turbine_to_steady_state(equilibrium)
        self._initialize_condenser_to_steady_state(equilibrium)
        
        # Set system-level state variables
        self.total_steam_flow = equilibrium['steam_flow']
        self.total_heat_transfer = equilibrium['heat_transfer']
        self.electrical_power_output = equilibrium['electrical_power']
        self.thermal_efficiency = equilibrium['thermal_efficiency']
        self.total_feedwater_flow = equilibrium['feedwater_flow']
        self.load_demand = equilibrium['load_demand']
    
    def _calculate_equilibrium_point(self, thermal_power_mw: float) -> Dict:
        """Calculate steady-state operating point for given thermal power"""
        
        # Calculate load demand based on thermal power
        # Assume rated thermal power is 3000 MW for typical PWR
        rated_thermal_power = 3000.0  # MW
        load_demand = min(100.0, (thermal_power_mw / rated_thermal_power) * 100.0)
        
        # Calculate steam flow based on thermal power and steam conditions
        # Typical PWR: ~1665 kg/s steam flow at 100% power
        design_steam_flow = 1665.0  # kg/s at 100% power
        steam_flow = design_steam_flow * (load_demand / 100.0)
        
        # Steam conditions at equilibrium
        steam_pressure = 6.895  # MPa typical PWR steam pressure
        steam_temperature = self._saturation_temperature(steam_pressure)  # ~285°C
        steam_quality = 0.99  # Typical steam quality
        
        # Feedwater flow equals steam flow at steady state (mass balance)
        feedwater_flow = steam_flow
        
        # Calculate electrical power based on realistic efficiency
        if load_demand >= 100.0:
            thermal_efficiency = 0.34  # 34% at full load
        elif load_demand >= 75.0:
            thermal_efficiency = 0.32 + 0.02 * (load_demand - 75.0) / 25.0
        elif load_demand >= 50.0:
            thermal_efficiency = 0.28 + 0.04 * (load_demand - 50.0) / 25.0
        else:
            thermal_efficiency = 0.20 + 0.08 * (load_demand / 50.0)
        
        electrical_power = thermal_power_mw * thermal_efficiency
        
        # Steam generator levels for steady-state operation
        sg_levels = [12.5] * self.num_steam_generators  # Normal operating level
        
        # Calculate pump speeds needed for feedwater flow
        # Each pump rated for 555 kg/s, so speed proportional to required flow
        pumps_needed = min(4, max(3, int(np.ceil(feedwater_flow / 555.0))))
        flow_per_pump = feedwater_flow / pumps_needed
        pump_speed = min(100.0, (flow_per_pump / 555.0) * 100.0)
        
        # Condenser conditions
        condenser_pressure = 0.007  # MPa typical condenser pressure
        condenser_temperature = self._saturation_temperature(condenser_pressure)  # ~39°C
        
        return {
            'thermal_power': thermal_power_mw,
            'load_demand': load_demand,
            'steam_flow': steam_flow,
            'steam_pressure': steam_pressure,
            'steam_temperature': steam_temperature,
            'steam_quality': steam_quality,
            'feedwater_flow': feedwater_flow,
            'electrical_power': electrical_power,
            'thermal_efficiency': thermal_efficiency,
            'heat_transfer': thermal_power_mw * 1e6,  # Convert to Watts
            'sg_levels': sg_levels,
            'pumps_needed': pumps_needed,
            'pump_speed': pump_speed,
            'condenser_pressure': condenser_pressure,
            'condenser_temperature': condenser_temperature
        }
    
    def _initialize_steam_generators_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize steam generators to steady-state levels and conditions"""
        # Set steam generator levels to normal operating level
        if hasattr(self.steam_generator_system, 'set_initial_levels'):
            self.steam_generator_system.set_initial_levels(equilibrium['sg_levels'])
        
        # Set steam production rates if method exists
        if hasattr(self.steam_generator_system, 'set_initial_steam_flow'):
            steam_flow_per_sg = equilibrium['steam_flow'] / self.num_steam_generators
            self.steam_generator_system.set_initial_steam_flow(steam_flow_per_sg)
    
    def _initialize_feedwater_system_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize feedwater pumps to steady-state operation"""
        # Initialize pumps to running state at calculated speeds
        if hasattr(self.feedwater_system, 'pump_system'):
            pump_system = self.feedwater_system.pump_system
            
            # Start required number of pumps in RUNNING state
            pump_ids = list(pump_system.pumps.keys())
            pumps_to_start = min(equilibrium['pumps_needed'], len(pump_ids))
            
            for i in range(pumps_to_start):
                pump_id = pump_ids[i]
                pump = pump_system.pumps[pump_id]
                
                # Set pump to RUNNING state with calculated speed and flow
                from systems.primary.coolant.pump_models import PumpStatus
                pump.state.status = PumpStatus.RUNNING
                pump.state.speed_percent = equilibrium['pump_speed']
                pump.state.speed_setpoint = equilibrium['pump_speed']
                pump.state.flow_rate = equilibrium['feedwater_flow'] / pumps_to_start
                pump.state.available = True
                pump.state.auto_control = True
                pump.state.trip_active = False
                pump.state.trip_reason = ""
                
                # Set appropriate hydraulic conditions
                pump.state.suction_pressure = 0.5  # MPa from condensate system
                pump.state.discharge_pressure = equilibrium['steam_pressure'] + 0.5
                pump.state.npsh_available = 25.0  # Adequate NPSH
                pump.state.differential_pressure = pump.state.discharge_pressure - pump.state.suction_pressure
                
                # Calculate power consumption for steady state
                pump._calculate_power_consumption()
            
            # Keep remaining pumps stopped
            for i in range(pumps_to_start, len(pump_ids)):
                pump_id = pump_ids[i]
                pump = pump_system.pumps[pump_id]
                pump.state.status = PumpStatus.STOPPED
                pump.state.speed_percent = 0.0
                pump.state.flow_rate = 0.0
                pump.state.power_consumption = 0.0
            
            # Update system totals
            pump_system.running_pumps = pump_ids[:pumps_to_start]
            pump_system.total_flow = equilibrium['feedwater_flow']
            pump_system.total_power = sum(pump_system.pumps[pid].state.power_consumption 
                                        for pid in pump_system.running_pumps)
            pump_system.system_available = True
    
    def _initialize_turbine_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize turbine to steady-state load"""
        # Set turbine load demand
        if hasattr(self.turbine, 'load_demand'):
            self.turbine.load_demand = equilibrium['load_demand'] / 100.0
        
        # Set turbine power output if possible
        if hasattr(self.turbine, 'total_power_output'):
            self.turbine.total_power_output = equilibrium['electrical_power']
    
    def _initialize_condenser_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize condenser to steady-state conditions"""
        # Set condenser pressure and temperature if possible
        if hasattr(self.condenser, 'condenser_pressure'):
            self.condenser.condenser_pressure = equilibrium['condenser_pressure']
        
        if hasattr(self.condenser, 'condenser_temperature'):
            self.condenser.condenser_temperature = equilibrium['condenser_temperature']
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """
        Calculate saturation temperature for given pressure
        
        Using improved correlation for water, valid 0.1-10 MPa
        Reference: NIST steam tables, simplified correlation
        """
        if pressure_mpa <= 0.001:
            return 10.0  # Very low pressure
        
        # FIXED: Use correct correlation for steam saturation temperature
        # For PWR pressures (6-7 MPa), saturation temperature should be ~280-290°C
        # Using simplified Clausius-Clapeyron relation
        
        # Reference point: 1 atm (0.101325 MPa) -> 100°C
        p_ref = 0.101325  # MPa
        t_ref = 100.0     # °C
        
        # Latent heat of vaporization (approximate)
        h_fg = 2257.0  # kJ/kg at 100°C
        
        # Gas constant for water vapor
        r_v = 0.4615  # kJ/kg/K
        
        # Clausius-Clapeyron equation: ln(P2/P1) = (h_fg/R_v) * (1/T1 - 1/T2)
        # Rearranged: T2 = 1 / (1/T1 - (R_v/h_fg) * ln(P2/P1))
        
        t_ref_k = t_ref + 273.15  # Convert to Kelvin
        pressure_ratio = pressure_mpa / p_ref
        
        if pressure_ratio > 0:
            temp_k = 1.0 / (1.0/t_ref_k - (r_v/h_fg) * np.log(pressure_ratio))
            temp_c = temp_k - 273.15
        else:
            temp_c = t_ref
        
        # For typical PWR steam pressure (6.9 MPa), this should give ~285°C
        return np.clip(temp_c, 10.0, 374.0)  # Physical limits for water
    
    def set_load_demand(self, load: float) -> None:
        """
        Set the electrical load demand for the system
        
        Args:
            load: Load demand as a percentage of rated power (0-100)
        """
        if 0 <= load <= 100:
            self.load_demand = load
        else:
            raise ValueError("Load demand must be between 0 and 100%")
    
    def get_state_dict(self) -> Dict[str, float]:
        """
        Get the current state of the secondary system as a dictionary.
        
        Returns:
            Dictionary with only system-level state variables (children manage their own states)
        """
        # Return only system-level coordination states
        # Children's states are collected automatically via StateProviderMixin auto-discovery
        state_dict = {
            'system_electrical_power': self.electrical_power_output,
            'system_thermal_efficiency': self.thermal_efficiency,
            'system_total_steam_flow': self.total_steam_flow,
            'system_total_heat_transfer': self.total_heat_transfer / 1e6,  # Convert to MW
            'system_load_demand': self.load_demand,
            'system_total_feedwater_flow': self.total_feedwater_flow,
            'system_feedwater_temperature': self.feedwater_temperature,
            'system_cooling_water_temperature': self.cooling_water_temperature,
            'system_operating_hours': self.operating_hours if hasattr(self, 'operating_hours') else 0.0,
            'system_num_steam_generators': self.num_steam_generators
        }

        return state_dict


# Example usage and testing
if __name__ == "__main__":
    print("Secondary Reactor Physics System - Integration Test")
    print("=" * 60)
    
    # Create integrated secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    print(f"Initialized system with {secondary_system.num_steam_generators} steam generators")
    print()
    
    
    # Test transient operation
    print("Transient Operation Test (Load Change):")
    
    # Primary conditions (typical PWR)
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,
        'sg_1_outlet_temp': 293.0,
        'sg_1_flow': 5700.0,
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    # Test load reduction
    for load in [100.0, 75.0, 50.0]:
        control_inputs = {
            'load_demand': load,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        result = secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=1.0
        )
        
        print(f"  Load {load:5.1f}%: Power {result['electrical_power_mw']:6.1f} MW, "
              f"Efficiency {result['thermal_efficiency']*100:5.2f}%, "
              f"Steam Flow {result['total_steam_flow']:6.0f} kg/s, "
              f"FW Flow {result['total_feedwater_flow']:6.0f} kg/s, "
              f"FW Pumps {result['feedwater_num_running_pumps']}")
    
    print()
    print("Secondary reactor physics implementation complete!")
    print("Components: Steam Generators, Turbine, Condenser, Feedwater Pumps")
    print("Features: Heat transfer, power generation, vacuum systems, feedwater control, three-element control")
