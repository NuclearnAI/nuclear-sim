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


class EnhancedSteamGeneratorPhysics(StateProviderMixin):
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
        Update enhanced steam generator system for one time step
        
        Args:
            primary_conditions: Primary side conditions for each SG
                - 'inlet_temps': List of primary inlet temperatures (°C)
                - 'outlet_temps': List of primary outlet temperatures (°C)
                - 'flow_rates': List of primary flow rates (kg/s)
            steam_demands: Steam demand conditions
                - 'total_steam_flow': Total steam flow demand (kg/s)
                - 'steam_pressure': Target steam pressure (MPa)
            system_conditions: Overall system conditions
                - 'feedwater_temperature': Feedwater temperature (°C)
                - 'load_demand': Load demand (0-1)
            control_inputs: Control system inputs
            dt: Time step (s)
            
        Returns:
            Dictionary with enhanced steam generator system results
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Extract system conditions
        self.load_demand = system_conditions.get('load_demand', 1.0)
        feedwater_temperature = system_conditions.get('feedwater_temperature', 227.0)
        
        # Extract steam demands
        total_steam_demand = steam_demands.get('total_steam_flow', self.config.design_total_steam_flow)
        target_pressure = steam_demands.get('steam_pressure', self.config.design_steam_pressure)
        
        # Calculate individual SG demands with load balancing
        individual_demands = self._calculate_load_distribution(
            total_steam_demand, primary_conditions
        )
        
        # Update individual steam generators
        sg_results = []
        total_thermal_power = 0.0
        total_steam_flow = 0.0
        
        for i, sg in enumerate(self.steam_generators):
            # Get primary conditions for this SG
            primary_inlet_temp = primary_conditions.get('inlet_temps', [327.0] * self.config.num_steam_generators)[i]
            primary_outlet_temp = primary_conditions.get('outlet_temps', [293.0] * self.config.num_steam_generators)[i]
            primary_flow = primary_conditions.get('flow_rates', [5700.0] * self.config.num_steam_generators)[i]
            
            # Get individual steam demand
            steam_flow_demand = individual_demands[i]
            feedwater_flow_demand = steam_flow_demand  # Mass balance
            
            # Update individual steam generator
            sg_result = sg.update_state(
                primary_temp_in=primary_inlet_temp,
                primary_temp_out=primary_outlet_temp,
                primary_flow=primary_flow,
                steam_flow_out=steam_flow_demand,
                feedwater_flow_in=feedwater_flow_demand,
                feedwater_temp=feedwater_temperature,
                dt=dt
            )
            
            sg_results.append(sg_result)
            total_thermal_power += sg_result['heat_transfer_rate']
            total_steam_flow += sg_result['steam_flow_rate']
        
        # Calculate system-level metrics
        self.total_thermal_power = total_thermal_power
        self.total_steam_flow = total_steam_flow
        
        # Calculate average conditions
        if self.steam_generators:
            self.average_steam_pressure = sum(sg.secondary_pressure for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_temperature = sum(sg.secondary_temperature for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_quality = sum(sg.steam_quality for sg in self.steam_generators) / len(self.steam_generators)
            
            # Calculate system efficiency
            design_power = self.config.design_total_thermal_power
            if design_power > 0:
                self.system_efficiency = min(1.0, total_thermal_power / design_power)
            else:
                self.system_efficiency = 0.0
        
        # Calculate performance metrics
        self.performance_factor = self._calculate_performance_factor(sg_results)
        self.load_balance_factor = self._calculate_load_balance_factor(sg_results)
        self.system_availability = self._check_system_availability(sg_results)
        
        # Update operating hours
        self.operating_hours += dt / 3600.0  # Convert seconds to hours
        
        return {
            # Overall system performance
            'total_thermal_power': self.total_thermal_power,
            'total_steam_flow': self.total_steam_flow,
            'average_steam_pressure': self.average_steam_pressure,
            'average_steam_temperature': self.average_steam_temperature,
            'average_steam_quality': self.average_steam_quality,
            'system_efficiency': self.system_efficiency,
            'system_availability': self.system_availability,
            'performance_factor': self.performance_factor,
            'load_balance_factor': self.load_balance_factor,
            
            # Individual SG results
            'sg_individual_results': sg_results,
            'sg_thermal_powers': [result['heat_transfer_rate'] for result in sg_results],
            'sg_steam_flows': [result['steam_flow_rate'] for result in sg_results],
            'sg_pressures': [sg.secondary_pressure for sg in self.steam_generators],
            'sg_levels': [sg.water_level for sg in self.steam_generators],
            'sg_steam_qualities': [sg.steam_quality for sg in self.steam_generators],
            
            # Control and operating conditions
            'control_mode': self.control_mode,
            'load_demand': self.load_demand,
            'operating_hours': self.operating_hours,
            'feedwater_temperature': feedwater_temperature,
            'target_steam_pressure': target_pressure,
            
            # System diagnostics
            'load_distribution': individual_demands,
            'thermal_power_distribution': [result['heat_transfer_rate'] for result in sg_results],
            'steam_flow_distribution': [result['steam_flow_rate'] for result in sg_results]
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
    
    def _calculate_performance_factor(self, sg_results: List[Dict]) -> float:
        """Calculate overall system performance factor"""
        if not sg_results:
            return 0.0
        
        # Average thermal efficiency across all SGs
        efficiencies = [result.get('thermal_efficiency', 0.0) for result in sg_results]
        avg_efficiency = sum(efficiencies) / len(efficiencies)
        
        # Average effectiveness across all SGs
        effectiveness_values = [result.get('effectiveness', 0.0) for result in sg_results]
        avg_effectiveness = sum(effectiveness_values) / len(effectiveness_values)
        
        # Combined performance factor
        performance_factor = (avg_efficiency + avg_effectiveness) / 2.0
        return min(1.0, max(0.0, performance_factor))
    
    def _calculate_load_balance_factor(self, sg_results: List[Dict]) -> float:
        """Calculate load balance effectiveness factor"""
        if not sg_results or len(sg_results) < 2:
            return 1.0
        
        # Calculate coefficient of variation for thermal power
        thermal_powers = [result.get('heat_transfer_rate', 0.0) for result in sg_results]
        if not thermal_powers or all(p == 0 for p in thermal_powers):
            return 1.0
        
        mean_power = sum(thermal_powers) / len(thermal_powers)
        if mean_power == 0:
            return 1.0
        
        variance = sum((p - mean_power) ** 2 for p in thermal_powers) / len(thermal_powers)
        std_dev = np.sqrt(variance)
        coefficient_of_variation = std_dev / mean_power
        
        # Convert to balance factor (1.0 = perfect balance, 0.0 = poor balance)
        load_balance_factor = max(0.0, 1.0 - coefficient_of_variation)
        return load_balance_factor
    
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
