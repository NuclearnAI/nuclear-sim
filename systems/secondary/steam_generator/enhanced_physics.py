"""
Enhanced Steam Generator Physics System

This module provides the enhanced steam generator system that orchestrates
multiple individual steam generators, following the same pattern as the
enhanced feedwater, condenser, and turbine systems.

Key Features:
1. Multi-SG coordination and load balancing
2. System-level control and optimization
3. Performance monitoring and diagnostics
4. Integrated protection systems
5. Comprehensive state management
"""

import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Import state management interfaces
from simulator.state import StateProviderMixin

# Import heat flow tracking
from ..heat_flow_tracker import HeatFlowProvider, ThermodynamicProperties

from .steam_generator import SteamGenerator, SteamGeneratorConfig


@dataclass
class SteamGeneratorSystemConfig:
    """Configuration for steam generator system"""
    num_steam_generators: int = 3                       # Number of steam generators
    sg_config: SteamGeneratorConfig = field(default_factory=SteamGeneratorConfig)
    auto_load_balancing: bool = True                    # Enable automatic load balancing
    system_coordination: bool = True                    # Enable system-level coordination
    performance_optimization: bool = True              # Enable performance optimization
    predictive_maintenance: bool = True                # Enable predictive maintenance


@dataclass
class EnhancedSteamGeneratorConfig:
    """
    Enhanced steam generator configuration that integrates all subsystems
    """
    
    # System configuration
    system_id: str = "ESG-001"                          # Enhanced steam generator system identifier
    num_steam_generators: int = 3                       # Number of steam generators
    
    # Design parameters
    design_total_thermal_power: float = 3255.0e6        # W total design thermal power (3255 MWt)
    design_total_steam_flow: float = 1665.0             # kg/s total design steam flow
    design_steam_pressure: float = 6.895                # MPa design steam pressure
    design_steam_temperature: float = 285.8             # °C design steam temperature
    
    # Subsystem configurations
    sg_system_config: SteamGeneratorSystemConfig = field(default_factory=SteamGeneratorSystemConfig)
    
    # Performance parameters
    design_efficiency: float = 0.98                     # Overall system design efficiency
    minimum_power_fraction: float = 0.1                 # Minimum power as fraction of design
    maximum_power_fraction: float = 1.05                # Maximum power as fraction of design
    
    # Control parameters
    auto_pressure_control: bool = True                  # Enable automatic pressure control
    load_following_enabled: bool = True                 # Enable load following
    system_optimization: bool = True                    # Enable system optimization


class EnhancedSteamGeneratorPhysics(StateProviderMixin, HeatFlowProvider):
    """
    Enhanced steam generator physics system - orchestrates multiple steam generators
    
    This system integrates:
    1. Multiple individual steam generators with coordination
    2. System-level load balancing and optimization
    3. Performance monitoring and diagnostics
    4. Protection systems and trip logic
    5. Comprehensive state management
    
    Physical Models Used:
    - Individual SG physics with system coordination
    - Load balancing algorithms
    - Performance optimization
    - System-level protection logic
    
    Implements StateProviderMixin for automatic state collection with proper naming.
    """
    
    def __init__(self, config: Optional[EnhancedSteamGeneratorConfig] = None):
        """Initialize enhanced steam generator physics system"""
        if config is None:
            config = EnhancedSteamGeneratorConfig()
        
        self.config = config
        
        # Initialize individual steam generators
        self.steam_generators = []
        for i in range(config.num_steam_generators):
            sg_config = config.sg_system_config.sg_config
            sg = SteamGenerator(sg_config)
            self.steam_generators.append(sg)
        
        # System state variables
        self.total_thermal_power = 0.0                   # W total thermal power
        self.total_steam_flow = 0.0                      # kg/s total steam flow
        self.average_steam_pressure = 6.895             # MPa average steam pressure
        self.average_steam_temperature = 285.8          # °C average steam temperature
        self.average_steam_quality = 0.99               # Average steam quality
        self.system_efficiency = 0.98                   # Overall system efficiency
        self.system_availability = True                 # System availability status
        
        # Performance tracking
        self.performance_factor = 1.0                   # Overall performance factor
        self.operating_hours = 0.0                      # Total operating hours
        self.load_balance_factor = 1.0                  # Load balance effectiveness
        
        # Control state
        self.control_mode = "automatic"                 # Control mode
        self.load_demand = 1.0                         # Load demand (0-1)
        
    def update_system(self,
                     primary_conditions: Dict[str, List[float]],
                     steam_demands: Dict[str, float],
                     system_conditions: Dict[str, float],
                     control_inputs: Dict[str, float] = None,
                     dt: float = 1.0) -> Dict[str, float]:
        """
        Streamlined enhanced steam generator system update
        
        Phase 2 Optimization: Removed redundant processing, simplified data flow.
        Focus on coordination and load balancing - let individual SGs handle physics.
        
        Args:
            primary_conditions: Primary side conditions for each SG
            steam_demands: Steam demand conditions  
            system_conditions: Overall system conditions
            control_inputs: Control system inputs
            dt: Time step (s)
            
        Returns:
            Dictionary with essential system results (streamlined)
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Phase 3: Steam Generator is Single Source of Truth for Steam Flow
        # Calculate actual steam flow based on load demand and physics, not external demand
        self.load_demand = system_conditions.get('load_demand', 1.0)
        feedwater_temperature = system_conditions.get('feedwater_temperature', 227.0)
        
        # Calculate actual steam flow based on load demand and design capacity
        load_demand_fraction = steam_demands.get('load_demand_fraction', self.load_demand)
        actual_total_steam_flow = self.config.design_total_steam_flow * load_demand_fraction
        
        # Simplified load distribution (core coordination function)
        individual_demands = self._calculate_load_distribution(actual_total_steam_flow, primary_conditions)
        
        # Direct update of individual steam generators (minimal wrapper processing)
        sg_results = []

        for i, sg in enumerate(self.steam_generators):
            # Direct parameter extraction - no redundant processing
            sg_result = sg.update_state(
                primary_temp_in=primary_conditions.get('inlet_temps', [327.0] * self.config.num_steam_generators)[i],
                primary_temp_out=primary_conditions.get('outlet_temps', [293.0] * self.config.num_steam_generators)[i],
                primary_flow=primary_conditions.get('flow_rates', [5700.0] * self.config.num_steam_generators)[i],
                steam_flow_out=individual_demands[i],
                feedwater_flow_in=individual_demands[i],  # Mass balance
                feedwater_temp=feedwater_temperature,
                dt=dt
            )
            
            sg_results.append(sg_result)
        
        # Streamlined system aggregation (essential metrics only)
        self.total_thermal_power = sum(result['heat_transfer_rate'] for result in sg_results)
        self.total_steam_flow = sum(result['steam_flow_rate'] for result in sg_results)
        
        # Essential system state (removed redundant calculations)
        if self.steam_generators:
            self.average_steam_pressure = sum(sg.secondary_pressure for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_temperature = sum(sg.secondary_temperature for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_quality = sum(sg.steam_quality for sg in self.steam_generators) / len(self.steam_generators)
        
        # Simplified performance tracking (removed complex metrics)
        self.system_availability = self._check_system_availability(sg_results)
        self.operating_hours += dt / 3600.0
        
        # Streamlined return data (essential results only)
        return {
            # Core system performance
            'total_thermal_power': self.total_thermal_power,
            'total_steam_flow': self.total_steam_flow,
            'average_steam_pressure': self.average_steam_pressure,
            'average_steam_temperature': self.average_steam_temperature,
            'average_steam_quality': self.average_steam_quality,
            'system_availability': self.system_availability,
            
            # Individual SG results (essential for downstream systems)
            'sg_individual_results': sg_results,
            'sg_steam_flows': [result['steam_flow_rate'] for result in sg_results],
            'sg_pressures': [sg.secondary_pressure for sg in self.steam_generators],
            'sg_levels': [sg.water_level for sg in self.steam_generators],
            'sg_steam_qualities': [sg.steam_quality for sg in self.steam_generators],
            
            # Essential control data
            'load_demand': self.load_demand,
            'operating_hours': self.operating_hours
        }
    
    def _calculate_load_distribution(self, 
                                   total_demand: float, 
                                   primary_conditions: Dict[str, List[float]]) -> List[float]:
        """
        Calculate optimal load distribution across steam generators
        
        Args:
            total_demand: Total steam flow demand (kg/s)
            primary_conditions: Primary side conditions for load balancing
            
        Returns:
            List of individual SG steam flow demands
        """
        if not self.config.sg_system_config.auto_load_balancing:
            # Equal distribution if auto load balancing is disabled
            individual_demand = total_demand / self.config.num_steam_generators
            return [individual_demand] * self.config.num_steam_generators
        
        # Get primary flow rates for load balancing
        primary_flows = primary_conditions.get('flow_rates', [5700.0] * self.config.num_steam_generators)
        
        # Calculate load distribution based on primary flow availability
        total_primary_flow = sum(primary_flows)
        if total_primary_flow > 0:
            # Distribute load proportional to primary flow availability
            individual_demands = []
            for flow in primary_flows:
                flow_fraction = flow / total_primary_flow
                individual_demand = total_demand * flow_fraction
                individual_demands.append(individual_demand)
        else:
            # Fallback to equal distribution
            individual_demand = total_demand / self.config.num_steam_generators
            individual_demands = [individual_demand] * self.config.num_steam_generators
        
        return individual_demands
    
    # Removed redundant performance calculation methods
    # Phase 2 Optimization: Let individual SGs handle their own performance metrics
    
    def _check_system_availability(self, sg_results: List[Dict]) -> bool:
        """Check overall system availability"""
        if not sg_results:
            return False
        
        # System is available if at least 2 out of 3 SGs are operating effectively
        effective_sgs = 0
        for result in sg_results:
            thermal_efficiency = result.get('thermal_efficiency', 0.0)
            if thermal_efficiency > 0.1:  # At least 10% efficiency
                effective_sgs += 1
        
        min_required_sgs = max(1, self.config.num_steam_generators - 1)  # N-1 redundancy
        return effective_sgs >= min_required_sgs
    
    def set_control_mode(self, mode: str) -> bool:
        """
        Set steam generator system control mode
        
        Args:
            mode: Control mode ('automatic', 'manual', 'emergency')
            
        Returns:
            Success status
        """
        valid_modes = ['automatic', 'manual', 'emergency']
        if mode in valid_modes:
            self.control_mode = mode
            return True
        return False
    
    def set_load_demand(self, load_demand: float) -> bool:
        """
        Set system load demand
        
        Args:
            load_demand: Load demand (0-1)
            
        Returns:
            Success status
        """
        if 0.0 <= load_demand <= 1.2:  # Allow up to 120% load
            self.load_demand = load_demand
            return True
        return False
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, float]:
        """
        Perform maintenance operations on steam generator systems
        
        Args:
            maintenance_type: Type of maintenance
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results
        """
        results = {}
        
        if maintenance_type == "sg_maintenance":
            # Perform steam generator maintenance
            sg_index = kwargs.get('sg_index', None)
            if sg_index is not None and 0 <= sg_index < len(self.steam_generators):
                # Maintenance on specific SG
                sg = self.steam_generators[sg_index]
                sg.reset()  # Reset to optimal conditions
                results[f'sg_{sg_index}_maintenance'] = True
            else:
                # Maintenance on all SGs
                for i, sg in enumerate(self.steam_generators):
                    sg.reset()
                    results[f'sg_{i}_maintenance'] = True
        
        elif maintenance_type == "system_optimization":
            # Optimize system performance
            self.performance_factor = min(1.0, self.performance_factor + 0.05)
            self.load_balance_factor = min(1.0, self.load_balance_factor + 0.05)
            results['system_optimization'] = True
        
        return results
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            # System-level state
            'system_total_thermal_power': self.total_thermal_power / 1e6,  # Convert to MW
            'system_total_steam_flow': self.total_steam_flow,
            'system_average_steam_pressure': self.average_steam_pressure,
            'system_average_steam_temperature': self.average_steam_temperature,
            'system_average_steam_quality': self.average_steam_quality,
            'system_efficiency': self.system_efficiency,
            'system_availability': float(self.system_availability),
            'system_performance_factor': self.performance_factor,
            'system_load_balance_factor': self.load_balance_factor,
            'system_operating_hours': self.operating_hours,
            'system_load_demand': self.load_demand,
            'system_num_steam_generators': self.config.num_steam_generators
        }
        
        # Add individual SG states
        for i, sg in enumerate(self.steam_generators):
            sg_state = sg.get_state_dict()
            for key, value in sg_state.items():
                state_dict[f'sg_{i+1}_{key}'] = value
        
        return state_dict
    
    def get_heat_flows(self) -> Dict[str, float]:
        """
        Get current heat flows for this component (MW)
        
        Returns:
            Dictionary with heat flow values in MW
        """
        # Calculate primary side heat input
        primary_heat_input = self.total_thermal_power / 1e6  # Convert W to MW
        
        # Calculate feedwater enthalpy input
        feedwater_temp = 227.0  # Typical feedwater temperature
        feedwater_enthalpy = ThermodynamicProperties.liquid_enthalpy(feedwater_temp)
        feedwater_enthalpy_input = ThermodynamicProperties.enthalpy_flow_mw(self.total_steam_flow, feedwater_enthalpy)
        
        # Calculate steam enthalpy output
        steam_enthalpy = ThermodynamicProperties.steam_enthalpy(
            self.average_steam_temperature, 
            self.average_steam_pressure, 
            self.average_steam_quality
        )
        steam_enthalpy_output = ThermodynamicProperties.enthalpy_flow_mw(self.total_steam_flow, steam_enthalpy)
        
        # Calculate thermal losses (approximately 2% of primary heat input)
        thermal_losses = primary_heat_input * 0.02
        
        # Calculate heat transfer efficiency
        if primary_heat_input > 0:
            heat_transfer_efficiency = (steam_enthalpy_output - feedwater_enthalpy_input) / primary_heat_input
        else:
            heat_transfer_efficiency = 0.0
        
        return {
            'primary_heat_input': primary_heat_input,
            'feedwater_enthalpy_input': feedwater_enthalpy_input,
            'steam_enthalpy_output': steam_enthalpy_output,
            'thermal_losses': thermal_losses,
            'heat_transfer_efficiency': heat_transfer_efficiency
        }
    
    def get_enthalpy_flows(self) -> Dict[str, float]:
        """
        Get current enthalpy flows for this component (MW)
        
        Returns:
            Dictionary with enthalpy flow values in MW
        """
        heat_flows = self.get_heat_flows()
        
        return {
            'inlet_enthalpy_flow': heat_flows['feedwater_enthalpy_input'],
            'outlet_enthalpy_flow': heat_flows['steam_enthalpy_output'],
            'enthalpy_added': heat_flows['steam_enthalpy_output'] - heat_flows['feedwater_enthalpy_input'],
            'primary_heat_input': heat_flows['primary_heat_input'],
            'thermal_efficiency': heat_flows['heat_transfer_efficiency']
        }
    
    def reset(self) -> None:
        """Reset enhanced steam generator system to initial conditions"""
        # Reset individual steam generators
        for sg in self.steam_generators:
            sg.reset()
        
        # Reset system state
        self.total_thermal_power = 0.0
        self.total_steam_flow = 0.0
        self.average_steam_pressure = self.config.design_steam_pressure
        self.average_steam_temperature = self.config.design_steam_temperature
        self.average_steam_quality = 0.99
        self.system_efficiency = self.config.design_efficiency
        self.system_availability = True
        
        # Reset performance tracking
        self.performance_factor = 1.0
        self.operating_hours = 0.0
        self.load_balance_factor = 1.0
        
        # Reset control state
        self.control_mode = "automatic"
        self.load_demand = 1.0


# Example usage and testing
if __name__ == "__main__":
    print("Enhanced Steam Generator Physics System - Integration Test")
    print("=" * 70)
    
    # Create enhanced steam generator system
    enhanced_sg = EnhancedSteamGeneratorPhysics()
    
    print(f"Created system with {enhanced_sg.config.num_steam_generators} steam generators")
    print(f"Design total thermal power: {enhanced_sg.config.design_total_thermal_power/1e6:.0f} MW")
    print(f"Design total steam flow: {enhanced_sg.config.design_total_steam_flow:.0f} kg/s")
    print()
    
    # Test normal operation
    print("Normal Operation Test:")
    print(f"{'Time':<6} {'Total Power':<12} {'Total Steam':<12} {'Efficiency':<12} {'Balance':<10} {'Available':<10}")
    print("-" * 70)
    
    for t in range(10):
        # Simulate varying primary conditions
        primary_conditions = {
            'inlet_temps': [327.0, 327.0, 327.0],
            'outlet_temps': [293.0, 293.0, 293.0],
            'flow_rates': [5700.0, 5700.0, 5700.0]
        }
        
        steam_demands = {
            'total_steam_flow': 1665.0,
            'steam_pressure': 6.895
        }
        
        system_conditions = {
            'feedwater_temperature': 227.0,
            'load_demand': 1.0
        }
        
        result = enhanced_sg.update_system(
            primary_conditions=primary_conditions,
            steam_demands=steam_demands,
            system_conditions=system_conditions,
            dt=1.0
        )
        
        status = "Yes" if result['system_availability'] else "No"
        
        print(f"{t:<6} {result['total_thermal_power']/1e6:<12.0f} "
              f"{result['total_steam_flow']:<12.0f} "
              f"{result['system_efficiency']:<12.3f} "
              f"{result['load_balance_factor']:<10.3f} "
              f"{status:<10}")
    
    print()
    print("Enhanced steam generator system ready for integration!")
