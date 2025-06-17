"""
Heat Flow Tracking System for Nuclear Plant Secondary Side

This module provides comprehensive heat flow tracking throughout the secondary
system to ensure proper energy conservation and physics-based calculations.

Key Features:
1. Enthalpy-based heat flow calculations
2. Component-level heat flow interfaces
3. System-wide energy balance validation
4. Debugging and diagnostic capabilities
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class HeatFlowState:
    """
    Complete heat flow state for the secondary system
    
    All values in MW (megawatts) for consistency
    """
    
    # Primary side inputs
    reactor_thermal_power: float = 0.0          # MW from reactor core
    primary_loop_losses: float = 0.0            # MW lost in primary loops
    sg_heat_input: float = 0.0                  # MW input to steam generators
    
    # Steam generator outputs
    steam_enthalpy_flow: float = 0.0            # MW in steam to turbine
    sg_thermal_losses: float = 0.0              # MW lost in steam generators
    sg_efficiency: float = 0.0                  # Steam generator efficiency
    
    # Turbine energy flows
    turbine_steam_input: float = 0.0            # MW steam enthalpy input
    turbine_work_output: float = 0.0            # MW mechanical work output
    turbine_exhaust_enthalpy: float = 0.0       # MW in exhaust steam
    extraction_steam_enthalpy: float = 0.0      # MW in extraction steam
    turbine_internal_losses: float = 0.0        # MW internal turbine losses
    
    # Condenser heat flows
    condenser_steam_input: float = 0.0          # MW exhaust steam enthalpy
    condenser_heat_rejection: float = 0.0       # MW rejected to cooling water
    condensate_enthalpy_output: float = 0.0     # MW in condensate
    condenser_losses: float = 0.0               # MW condenser losses
    
    # Feedwater system heat flows
    feedwater_heating: float = 0.0              # MW from extraction steam
    feedwater_pump_work: float = 0.0            # MW feedwater pump work
    feedwater_losses: float = 0.0               # MW feedwater system losses
    
    # Auxiliary systems
    auxiliary_steam_consumption: float = 0.0    # MW auxiliary steam use
    auxiliary_heat_losses: float = 0.0          # MW other system losses
    
    # Electrical generation
    generator_mechanical_input: float = 0.0     # MW mechanical input
    generator_electrical_output: float = 0.0    # MW electrical output
    generator_losses: float = 0.0               # MW generator losses
    auxiliary_power_consumption: float = 0.0    # MW plant auxiliary power
    net_electrical_output: float = 0.0          # MW net electrical output
    
    # Energy balance validation
    total_energy_input: float = 0.0             # MW total energy input
    total_energy_output: float = 0.0            # MW total energy output
    energy_balance_error: float = 0.0           # MW energy imbalance
    energy_balance_percent_error: float = 0.0   # % energy imbalance
    
    # Performance metrics
    overall_thermal_efficiency: float = 0.0     # Overall plant efficiency
    heat_rate: float = 0.0                      # kJ/kWh heat rate
    steam_cycle_efficiency: float = 0.0         # Steam cycle efficiency


class HeatFlowProvider(ABC):
    """
    Abstract interface for components that provide heat flow information
    
    All components in the secondary system should implement this interface
    to enable comprehensive heat flow tracking.
    """
    
    @abstractmethod
    def get_heat_flows(self) -> Dict[str, float]:
        """
        Get current heat flows for this component
        
        Returns:
            Dictionary with heat flow values in MW
        """
        pass
    
    @abstractmethod
    def get_enthalpy_flows(self) -> Dict[str, float]:
        """
        Get current enthalpy flows for this component
        
        Returns:
            Dictionary with enthalpy flow values in MW
        """
        pass


class ThermodynamicProperties:
    """
    Thermodynamic property calculations for heat flow analysis
    
    Provides consistent property calculations across all components
    """
    
    @staticmethod
    def steam_enthalpy(temperature: float, pressure: float, quality: float = 1.0) -> float:
        """
        Calculate steam enthalpy (kJ/kg) - CORRECTED for realistic PWR conditions
        
        Args:
            temperature: Steam temperature (°C)
            pressure: Steam pressure (MPa)
            quality: Steam quality (0-1, default 1.0 for superheated)
            
        Returns:
            Steam enthalpy in kJ/kg
        """
        # Saturation properties
        sat_temp = ThermodynamicProperties.saturation_temperature(pressure)
        h_f = ThermodynamicProperties.saturation_enthalpy_liquid(pressure)
        h_g = ThermodynamicProperties.saturation_enthalpy_vapor(pressure)
        h_fg = h_g - h_f
        
        if quality < 1.0:
            # Wet steam: h = h_f + x * h_fg
            return h_f + quality * h_fg
        elif temperature <= sat_temp + 0.1:
            # Saturated steam
            return h_g
        else:
            # Superheated steam: h = h_g + cp * (T - T_sat)
            superheat = temperature - sat_temp
            cp_steam = 2.1  # kJ/kg/K approximate specific heat of steam
            return h_g + cp_steam * superheat
    
    @staticmethod
    def liquid_enthalpy(temperature: float, pressure: float = 0.1) -> float:
        """
        Calculate liquid water enthalpy (kJ/kg)
        
        Args:
            temperature: Water temperature (°C)
            pressure: Water pressure (MPa, default 0.1)
            
        Returns:
            Liquid enthalpy in kJ/kg
        """
        # Simplified correlation for liquid water
        # h = cp * T (reference at 0°C)
        cp_water = 4.18  # kJ/kg/K
        return cp_water * temperature
    
    @staticmethod
    def saturation_temperature(pressure: float) -> float:
        """Calculate saturation temperature for given pressure (°C)"""
        if pressure <= 0.001:
            return 10.0
        
        # Antoine equation coefficients for water
        A, B, C = 8.07131, 1730.63, 233.426
        pressure_bar = pressure * 10.0
        pressure_bar = np.clip(pressure_bar, 0.01, 100.0)
        
        temp_c = B / (A - np.log10(pressure_bar)) - C
        return np.clip(temp_c, 10.0, 374.0)
    
    @staticmethod
    def saturation_enthalpy_liquid(pressure: float) -> float:
        """Calculate saturation enthalpy of liquid water (kJ/kg)"""
        temp = ThermodynamicProperties.saturation_temperature(pressure)
        return 4.18 * temp
    
    @staticmethod
    def saturation_enthalpy_vapor(pressure: float) -> float:
        """Calculate saturation enthalpy of steam (kJ/kg)"""
        temp = ThermodynamicProperties.saturation_temperature(pressure)
        h_f = ThermodynamicProperties.saturation_enthalpy_liquid(pressure)
        h_fg = 2257.0 * (1.0 - temp / 374.0) ** 0.38
        return h_f + h_fg
    
    @staticmethod
    def enthalpy_flow_mw(mass_flow: float, specific_enthalpy: float) -> float:
        """
        Calculate enthalpy flow in MW
        
        Args:
            mass_flow: Mass flow rate (kg/s)
            specific_enthalpy: Specific enthalpy (kJ/kg)
            
        Returns:
            Enthalpy flow in MW
        """
        return mass_flow * specific_enthalpy / 1000.0  # Convert kJ/s to MW


class HeatFlowTracker:
    """
    Main heat flow tracking system for the secondary side
    
    This class coordinates heat flow tracking across all components
    and provides comprehensive energy balance analysis.
    """
    
    def __init__(self):
        """Initialize heat flow tracker"""
        self.heat_flow_state = HeatFlowState()
        self.component_flows = {}  # Store individual component flows
        self.flow_history = []     # Store historical flow data
        self.validation_tolerance = 0.01  # 1% tolerance for energy balance
        
    def update_component_flows(self, component_name: str, flows: Dict[str, float]) -> None:
        """
        Update heat flows for a specific component
        
        Args:
            component_name: Name of the component
            flows: Dictionary of heat flows in MW
        """
        self.component_flows[component_name] = flows.copy()
    
    def calculate_system_heat_flows(self) -> HeatFlowState:
        """
        Calculate complete system heat flows from component data
        
        Returns:
            Complete heat flow state
        """
        state = HeatFlowState()
        
        # Extract steam generator flows
        if 'steam_generator' in self.component_flows:
            sg_flows = self.component_flows['steam_generator']
            state.sg_heat_input = sg_flows.get('primary_heat_input', 0.0)
            state.steam_enthalpy_flow = sg_flows.get('steam_enthalpy_output', 0.0)
            state.sg_thermal_losses = sg_flows.get('thermal_losses', 0.0)
            state.sg_efficiency = sg_flows.get('thermal_efficiency', 0.0)
        
        # Extract turbine flows
        if 'turbine' in self.component_flows:
            turbine_flows = self.component_flows['turbine']
            state.turbine_steam_input = turbine_flows.get('steam_enthalpy_input', 0.0)
            state.turbine_work_output = turbine_flows.get('mechanical_work_output', 0.0)
            state.turbine_exhaust_enthalpy = turbine_flows.get('exhaust_enthalpy_output', 0.0)
            state.extraction_steam_enthalpy = turbine_flows.get('extraction_enthalpy_output', 0.0)
            state.turbine_internal_losses = turbine_flows.get('internal_losses', 0.0)
        
        # Extract condenser flows
        if 'condenser' in self.component_flows:
            condenser_flows = self.component_flows['condenser']
            state.condenser_steam_input = condenser_flows.get('steam_enthalpy_input', 0.0)
            state.condenser_heat_rejection = condenser_flows.get('heat_rejection_output', 0.0)
            state.condensate_enthalpy_output = condenser_flows.get('condensate_enthalpy_output', 0.0)
            state.condenser_losses = condenser_flows.get('thermal_losses', 0.0)
        
        # Extract feedwater system flows
        if 'feedwater' in self.component_flows:
            fw_flows = self.component_flows['feedwater']
            state.feedwater_heating = fw_flows.get('extraction_heating', 0.0)
            state.feedwater_pump_work = fw_flows.get('pump_work_input', 0.0)
            state.feedwater_losses = fw_flows.get('system_losses', 0.0)
        
        # Calculate electrical generation
        state.generator_mechanical_input = state.turbine_work_output
        state.generator_electrical_output = state.generator_mechanical_input * 0.985  # 98.5% generator efficiency
        state.generator_losses = state.generator_mechanical_input - state.generator_electrical_output
        state.auxiliary_power_consumption = state.generator_electrical_output * 0.02  # 2% auxiliary power
        state.net_electrical_output = state.generator_electrical_output - state.auxiliary_power_consumption
        
        # Calculate energy balance - CORRECTED
        # Total energy input to the system
        state.total_energy_input = (state.sg_heat_input + 
                                  state.feedwater_pump_work)
        
        # Total energy output from the system
        # Energy must be conserved: Input = Electrical Output + Heat Rejection + All Losses
        state.total_energy_output = (state.net_electrical_output + 
                                   state.condenser_heat_rejection + 
                                   state.sg_thermal_losses + 
                                   state.turbine_internal_losses + 
                                   state.condenser_losses + 
                                   state.feedwater_losses + 
                                   state.generator_losses + 
                                   state.auxiliary_heat_losses)
        
        state.energy_balance_error = state.total_energy_input - state.total_energy_output
        
        if state.total_energy_input > 0:
            state.energy_balance_percent_error = (state.energy_balance_error / state.total_energy_input) * 100.0
        else:
            state.energy_balance_percent_error = 0.0
        
        # Calculate performance metrics
        if state.total_energy_input > 0:
            state.overall_thermal_efficiency = state.net_electrical_output / state.total_energy_input
            state.steam_cycle_efficiency = state.turbine_work_output / state.steam_enthalpy_flow if state.steam_enthalpy_flow > 0 else 0.0
        
        if state.net_electrical_output > 0:
            state.heat_rate = (state.total_energy_input * 1000.0) / (state.net_electrical_output * 1000.0) * 3.6  # kJ/kWh
        
        self.heat_flow_state = state
        return state
    
    def validate_energy_balance(self) -> Dict[str, float]:
        """
        Validate energy balance and identify discrepancies
        
        Returns:
            Dictionary with validation results
        """
        state = self.heat_flow_state
        
        validation = {
            'energy_balance_error_mw': state.energy_balance_error,
            'energy_balance_percent_error': state.energy_balance_percent_error,
            'balance_acceptable': abs(state.energy_balance_percent_error) < (self.validation_tolerance * 100),
            'total_input_mw': state.total_energy_input,
            'total_output_mw': state.total_energy_output,
            'largest_output_component': self._find_largest_output_component(),
            'steam_generator_balance': self._validate_steam_generator_balance(),
            'turbine_balance': self._validate_turbine_balance(),
            'condenser_balance': self._validate_condenser_balance()
        }
        
        return validation
    
    def _find_largest_output_component(self) -> str:
        """Find the component with the largest energy output"""
        state = self.heat_flow_state
        
        outputs = {
            'condenser_heat_rejection': state.condenser_heat_rejection,
            'net_electrical_output': state.net_electrical_output,
            'thermal_losses': (state.sg_thermal_losses + state.turbine_internal_losses + 
                             state.condenser_losses + state.feedwater_losses),
            'generator_losses': state.generator_losses
        }
        
        return max(outputs, key=outputs.get)
    
    def _validate_steam_generator_balance(self) -> Dict[str, float]:
        """Validate steam generator energy balance"""
        state = self.heat_flow_state
        
        sg_input = state.sg_heat_input
        sg_output = state.steam_enthalpy_flow + state.sg_thermal_losses
        sg_error = sg_input - sg_output
        sg_error_percent = (sg_error / sg_input * 100.0) if sg_input > 0 else 0.0
        
        return {
            'input_mw': sg_input,
            'output_mw': sg_output,
            'error_mw': sg_error,
            'error_percent': sg_error_percent,
            'balance_ok': abs(sg_error_percent) < (self.validation_tolerance * 100)
        }
    
    def _validate_turbine_balance(self) -> Dict[str, float]:
        """Validate turbine energy balance"""
        state = self.heat_flow_state
        
        turbine_input = state.turbine_steam_input
        turbine_output = (state.turbine_work_output + 
                         state.turbine_exhaust_enthalpy + 
                         state.extraction_steam_enthalpy + 
                         state.turbine_internal_losses)
        turbine_error = turbine_input - turbine_output
        turbine_error_percent = (turbine_error / turbine_input * 100.0) if turbine_input > 0 else 0.0
        
        return {
            'input_mw': turbine_input,
            'output_mw': turbine_output,
            'error_mw': turbine_error,
            'error_percent': turbine_error_percent,
            'balance_ok': abs(turbine_error_percent) < (self.validation_tolerance * 100)
        }
    
    def _validate_condenser_balance(self) -> Dict[str, float]:
        """Validate condenser energy balance"""
        state = self.heat_flow_state
        
        condenser_input = state.condenser_steam_input
        condenser_output = state.condenser_heat_rejection + state.condensate_enthalpy_output + state.condenser_losses
        condenser_error = condenser_input - condenser_output
        condenser_error_percent = (condenser_error / condenser_input * 100.0) if condenser_input > 0 else 0.0
        
        return {
            'input_mw': condenser_input,
            'output_mw': condenser_output,
            'error_mw': condenser_error,
            'error_percent': condenser_error_percent,
            'balance_ok': abs(condenser_error_percent) < (self.validation_tolerance * 100)
        }
    
    def get_heat_flow_summary(self) -> Dict[str, float]:
        """
        Get comprehensive heat flow summary
        
        Returns:
            Dictionary with all heat flow data
        """
        state = self.heat_flow_state
        validation = self.validate_energy_balance()
        
        return {
            # Primary energy flows
            'reactor_thermal_power': state.reactor_thermal_power,
            'sg_heat_input': state.sg_heat_input,
            'steam_enthalpy_flow': state.steam_enthalpy_flow,
            
            # Turbine energy flows
            'turbine_work_output': state.turbine_work_output,
            'turbine_exhaust_enthalpy': state.turbine_exhaust_enthalpy,
            'extraction_steam_enthalpy': state.extraction_steam_enthalpy,
            
            # Heat rejection
            'condenser_heat_rejection': state.condenser_heat_rejection,
            'total_heat_rejection': (state.condenser_heat_rejection + 
                                   state.feedwater_heating + 
                                   state.auxiliary_heat_losses),
            
            # Electrical output
            'gross_electrical_output': state.generator_electrical_output,
            'net_electrical_output': state.net_electrical_output,
            
            # Performance metrics
            'overall_thermal_efficiency': state.overall_thermal_efficiency,
            'steam_cycle_efficiency': state.steam_cycle_efficiency,
            'heat_rate': state.heat_rate,
            
            # Energy balance validation
            'energy_balance_error': state.energy_balance_error,
            'energy_balance_percent_error': state.energy_balance_percent_error,
            'energy_balance_ok': validation['balance_acceptable'],
            
            # Component balances
            'sg_balance_ok': validation['steam_generator_balance']['balance_ok'],
            'turbine_balance_ok': validation['turbine_balance']['balance_ok'],
            'condenser_balance_ok': validation['condenser_balance']['balance_ok']
        }
    
    def add_to_history(self, timestamp: float) -> None:
        """Add current state to historical data"""
        history_entry = {
            'timestamp': timestamp,
            'heat_flows': self.get_heat_flow_summary(),
            'component_flows': self.component_flows.copy()
        }
        self.flow_history.append(history_entry)
        
        # Limit history size
        if len(self.flow_history) > 1000:
            self.flow_history = self.flow_history[-1000:]
    
    def reset(self) -> None:
        """Reset heat flow tracker to initial state"""
        self.heat_flow_state = HeatFlowState()
        self.component_flows = {}
        self.flow_history = []


# Example usage and testing
if __name__ == "__main__":
    print("Heat Flow Tracking System - Validation Test")
    print("=" * 50)
    
    # Create heat flow tracker
    tracker = HeatFlowTracker()
    
    # Simulate component heat flows for a typical PWR
    # Steam Generator
    sg_flows = {
        'primary_heat_input': 3000.0,      # MW thermal input
        'steam_enthalpy_output': 2950.0,   # MW steam enthalpy
        'thermal_losses': 50.0,            # MW SG losses
        'thermal_efficiency': 0.983        # SG efficiency
    }
    tracker.update_component_flows('steam_generator', sg_flows)
    
    # Turbine
    turbine_flows = {
        'steam_enthalpy_input': 2950.0,    # MW steam input
        'mechanical_work_output': 1020.0,  # MW mechanical work
        'exhaust_enthalpy_output': 1800.0, # MW exhaust enthalpy
        'extraction_enthalpy_output': 100.0, # MW extraction steam
        'internal_losses': 30.0            # MW turbine losses
    }
    tracker.update_component_flows('turbine', turbine_flows)
    
    # Condenser
    condenser_flows = {
        'steam_enthalpy_input': 1800.0,    # MW exhaust steam
        'heat_rejection_output': 1750.0,   # MW heat rejection
        'condensate_enthalpy_output': 40.0, # MW condensate enthalpy
        'thermal_losses': 10.0             # MW condenser losses
    }
    tracker.update_component_flows('condenser', condenser_flows)
    
    # Feedwater System
    fw_flows = {
        'extraction_heating': 100.0,       # MW feedwater heating
        'pump_work_input': 15.0,           # MW pump work
        'system_losses': 5.0               # MW system losses
    }
    tracker.update_component_flows('feedwater', fw_flows)
    
    # Calculate system heat flows
    state = tracker.calculate_system_heat_flows()
    validation = tracker.validate_energy_balance()
    summary = tracker.get_heat_flow_summary()
    
    print(f"System Heat Flow Analysis:")
    print(f"  Total Energy Input: {state.total_energy_input:.1f} MW")
    print(f"  Total Energy Output: {state.total_energy_output:.1f} MW")
    print(f"  Energy Balance Error: {state.energy_balance_error:.1f} MW ({state.energy_balance_percent_error:.2f}%)")
    print(f"  Energy Balance OK: {validation['balance_acceptable']}")
    print()
    
    print(f"Major Energy Flows:")
    print(f"  Steam Generator Heat Input: {state.sg_heat_input:.1f} MW")
    print(f"  Turbine Work Output: {state.turbine_work_output:.1f} MW")
    print(f"  Condenser Heat Rejection: {state.condenser_heat_rejection:.1f} MW")
    print(f"  Net Electrical Output: {state.net_electrical_output:.1f} MW")
    print()
    
    print(f"Performance Metrics:")
    print(f"  Overall Thermal Efficiency: {state.overall_thermal_efficiency:.1%}")
    print(f"  Steam Cycle Efficiency: {state.steam_cycle_efficiency:.1%}")
    print(f"  Heat Rate: {state.heat_rate:.0f} kJ/kWh")
    print()
    
    print(f"Component Energy Balance Validation:")
    print(f"  Steam Generator: {validation['steam_generator_balance']['balance_ok']} "
          f"({validation['steam_generator_balance']['error_percent']:.2f}%)")
    print(f"  Turbine: {validation['turbine_balance']['balance_ok']} "
          f"({validation['turbine_balance']['error_percent']:.2f}%)")
    print(f"  Condenser: {validation['condenser_balance']['balance_ok']} "
          f"({validation['condenser_balance']['error_percent']:.2f}%)")
    
    print("\nHeat flow tracking system ready for integration!")
