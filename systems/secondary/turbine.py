"""
Steam Turbine Physics Model

This module implements a comprehensive physics-based model for PWR steam turbines,
including steam expansion, power generation, and thermodynamic calculations.

Parameter Sources:
- Steam Turbine Theory and Practice (Kearton)
- Power Plant Engineering (Black & Veatch)
- GE Steam Turbine Design Manual
- Typical PWR turbine specifications (1000+ MW units)

Physical Basis:
- Isentropic expansion with efficiency losses
- Reheat and moisture separation effects
- Multi-stage turbine modeling
- Generator electrical conversion
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore")


@dataclass
class TurbineConfig:
    """
    Steam turbine configuration parameters based on typical large PWR turbines
    
    References:
    - GE Steam Turbine specifications
    - Westinghouse turbine designs
    - EPRI Turbine Performance Guidelines
    """
    
    # Design parameters
    rated_power_mwe: float = 1100.0  # MW electrical (typical large PWR)
    design_steam_flow: float = 1665.0  # kg/s total steam flow (3 SGs × 555 kg/s)
    design_steam_pressure: float = 6.895  # MPa inlet pressure
    design_steam_temperature: float = 285.8  # °C inlet temperature
    
    # Turbine stages and efficiency
    hp_stages: int = 8  # High pressure turbine stages
    lp_stages: int = 6  # Low pressure turbine stages per flow
    lp_flows: int = 2   # Number of LP turbine flows (double flow)
    
    # Efficiency parameters (based on modern large steam turbines)
    hp_isentropic_efficiency: float = 0.88  # HP turbine efficiency
    lp_isentropic_efficiency: float = 0.92  # LP turbine efficiency
    mechanical_efficiency: float = 0.98     # Mechanical losses
    generator_efficiency: float = 0.985     # Generator efficiency
    
    # Pressure levels (typical PWR steam cycle)
    hp_exhaust_pressure: float = 1.2  # MPa (HP turbine exhaust to moisture separator)
    lp_inlet_pressure: float = 1.15   # MPa (LP turbine inlet after reheater)
    condenser_pressure: float = 0.007 # MPa (condenser vacuum)
    
    # Reheat parameters
    reheat_temperature: float = 285.0  # °C (reheat to near saturation)
    moisture_separator_efficiency: float = 0.995  # Moisture removal efficiency
    
    # Control parameters
    governor_response_time: float = 0.2  # seconds (turbine governor response)
    load_rejection_rate: float = 0.1     # per second (max load change rate)
    
    # Physical constraints
    max_steam_velocity: float = 600.0    # m/s (blade tip speed limit)
    min_steam_quality: float = 0.88      # Minimum steam quality for LP turbine
    max_power_rate_change: float = 50.0  # MW/s maximum power change rate


class TurbinePhysics:
    """
    Comprehensive steam turbine physics model for PWR
    
    This model implements:
    1. Multi-stage steam expansion with reheat
    2. Isentropic efficiency calculations
    3. Moisture separation and reheat effects
    4. Power generation and electrical conversion
    5. Control system dynamics
    
    Physical Models Used:
    - Isentropic expansion: h2s = h1 - η*(h1 - h2s_ideal)
    - Steam properties: Simplified correlations for enthalpy/entropy
    - Power calculation: P = m_dot * (h_in - h_out)
    - Control dynamics: First-order lag with rate limiting
    """
    
    def __init__(self, config: Optional[TurbineConfig] = None):
        """Initialize turbine physics model"""
        self.config = config if config is not None else TurbineConfig()
        
        # Initialize state variables to typical operating conditions
        self.steam_inlet_pressure = 6.895    # MPa
        self.steam_inlet_temperature = 285.8 # °C
        self.steam_inlet_flow = 1665.0       # kg/s
        self.steam_inlet_quality = 0.99      # Near dry steam
        
        # Turbine internal state
        self.hp_exhaust_pressure = 1.2      # MPa
        self.hp_exhaust_temperature = 187.0 # °C (saturation at 1.2 MPa)
        self.hp_exhaust_quality = 0.92      # After expansion
        
        self.lp_inlet_pressure = 1.15       # MPa (after moisture separator)
        self.lp_inlet_temperature = 185.0   # °C (after reheat)
        self.lp_inlet_quality = 0.99        # After moisture separation
        
        self.condenser_pressure = 0.007     # MPa
        self.condenser_temperature = 39.0   # °C (saturation at 0.007 MPa)
        
        # Power generation
        self.mechanical_power = 1100.0      # MW mechanical
        self.electrical_power = 1085.0      # MW electrical
        self.power_setpoint = 1100.0        # MW setpoint
        
        # Control state
        self.governor_valve_position = 100.0 # % open
        self.load_demand = 100.0            # % rated load
        
        # Performance tracking
        self.overall_efficiency = 0.0
        self.heat_rate = 0.0  # kJ/kWh
        self.steam_rate = 0.0 # kg/kWh
        
    def calculate_hp_turbine_expansion(self,
                                     inlet_pressure: float,
                                     inlet_temperature: float,
                                     inlet_flow: float,
                                     inlet_quality: float,
                                     exhaust_pressure: float) -> Dict[str, float]:
        """
        Calculate high pressure turbine expansion process
        
        Physical Basis:
        - Isentropic expansion with efficiency losses
        - h2 = h1 - η_is * (h1 - h2s)
        - Steam quality calculations for wet steam region
        
        Args:
            inlet_pressure: Steam inlet pressure (MPa)
            inlet_temperature: Steam inlet temperature (°C)
            inlet_flow: Steam mass flow rate (kg/s)
            inlet_quality: Steam quality at inlet (0-1)
            exhaust_pressure: Turbine exhaust pressure (MPa)
            
        Returns:
            Dictionary with HP turbine performance data
        """
        # Calculate inlet enthalpy
        if inlet_quality >= 0.99:
            # Superheated or dry saturated steam
            h_inlet = self._steam_enthalpy(inlet_temperature, inlet_pressure)
        else:
            # Wet steam
            h_f = self._saturation_enthalpy_liquid(inlet_pressure)
            h_g = self._saturation_enthalpy_vapor(inlet_pressure)
            h_inlet = h_f + inlet_quality * (h_g - h_f)
        
        # Calculate inlet entropy (simplified)
        s_inlet = self._steam_entropy(inlet_temperature, inlet_pressure, inlet_quality)
        
        # Isentropic expansion to exhaust pressure
        exhaust_sat_temp = self._saturation_temperature(exhaust_pressure)
        h_f_exhaust = self._saturation_enthalpy_liquid(exhaust_pressure)
        h_g_exhaust = self._saturation_enthalpy_vapor(exhaust_pressure)
        s_f_exhaust = self._saturation_entropy_liquid(exhaust_pressure)
        s_g_exhaust = self._saturation_entropy_vapor(exhaust_pressure)
        
        # Check if expansion ends in wet steam region
        if s_inlet < s_g_exhaust:
            # Expansion ends in wet steam region
            quality_isentropic = (s_inlet - s_f_exhaust) / (s_g_exhaust - s_f_exhaust)
            quality_isentropic = np.clip(quality_isentropic, 0.0, 1.0)
            h_exhaust_isentropic = h_f_exhaust + quality_isentropic * (h_g_exhaust - h_f_exhaust)
        else:
            # Expansion ends in superheated region (rare for HP turbine)
            quality_isentropic = 1.0
            h_exhaust_isentropic = h_g_exhaust
        
        # Actual enthalpy with efficiency losses
        enthalpy_drop_isentropic = h_inlet - h_exhaust_isentropic
        enthalpy_drop_actual = self.config.hp_isentropic_efficiency * enthalpy_drop_isentropic
        h_exhaust_actual = h_inlet - enthalpy_drop_actual
        
        # Calculate actual exhaust quality
        if h_exhaust_actual <= h_g_exhaust:
            quality_actual = (h_exhaust_actual - h_f_exhaust) / (h_g_exhaust - h_f_exhaust)
            quality_actual = np.clip(quality_actual, 0.0, 1.0)
            exhaust_temp_actual = exhaust_sat_temp
        else:
            quality_actual = 1.0
            # Superheated exhaust (calculate temperature)
            exhaust_temp_actual = exhaust_sat_temp + (h_exhaust_actual - h_g_exhaust) / 2.1
        
        # Power calculation
        power_hp = inlet_flow * enthalpy_drop_actual / 1000.0  # MW (convert kJ/s to MW)
        
        # Steam velocity and Mach number (simplified)
        specific_volume = self._specific_volume(exhaust_temp_actual, exhaust_pressure, quality_actual)
        steam_velocity = np.sqrt(2000 * enthalpy_drop_actual)  # Approximate velocity
        steam_velocity = np.clip(steam_velocity, 0, self.config.max_steam_velocity)
        
        return {
            'power_mw': power_hp,
            'exhaust_enthalpy': h_exhaust_actual,
            'exhaust_temperature': exhaust_temp_actual,
            'exhaust_quality': quality_actual,
            'enthalpy_drop': enthalpy_drop_actual,
            'isentropic_efficiency': self.config.hp_isentropic_efficiency,
            'steam_velocity': steam_velocity,
            'specific_volume': specific_volume
        }
    
    def calculate_moisture_separation_reheat(self,
                                           inlet_flow: float,
                                           inlet_enthalpy: float,
                                           inlet_quality: float,
                                           separator_pressure: float) -> Dict[str, float]:
        """
        Calculate moisture separator and reheater performance
        
        Physical Basis:
        - Mechanical moisture separation
        - Steam reheat to improve LP turbine efficiency
        - Mass and energy balance across separator/reheater
        
        Args:
            inlet_flow: Steam flow into separator (kg/s)
            inlet_enthalpy: Steam enthalpy (kJ/kg)
            inlet_quality: Steam quality (0-1)
            separator_pressure: Operating pressure (MPa)
            
        Returns:
            Dictionary with separator/reheater performance
        """
        # Moisture separation efficiency
        moisture_removed = (1.0 - inlet_quality) * self.config.moisture_separator_efficiency
        outlet_quality = inlet_quality + moisture_removed
        outlet_quality = np.clip(outlet_quality, inlet_quality, 0.999)
        
        # Separated water flow
        water_separated = inlet_flow * moisture_removed
        steam_flow_out = inlet_flow - water_separated
        
        # Energy balance for separation (no external heat addition in separator)
        h_f = self._saturation_enthalpy_liquid(separator_pressure)
        h_g = self._saturation_enthalpy_vapor(separator_pressure)
        
        # Outlet enthalpy after separation
        outlet_enthalpy_separated = h_f + outlet_quality * (h_g - h_f)
        
        # Reheat process (steam extraction from HP turbine or external steam)
        # Assume reheat brings steam close to saturation temperature
        reheat_temperature = self.config.reheat_temperature
        outlet_enthalpy_reheated = self._steam_enthalpy(reheat_temperature, separator_pressure)
        
        # Heat addition for reheat
        heat_addition = steam_flow_out * (outlet_enthalpy_reheated - outlet_enthalpy_separated)
        
        return {
            'steam_flow_out': steam_flow_out,
            'water_separated': water_separated,
            'outlet_quality': outlet_quality,
            'outlet_enthalpy': outlet_enthalpy_reheated,
            'outlet_temperature': reheat_temperature,
            'heat_addition': heat_addition,
            'separation_efficiency': self.config.moisture_separator_efficiency
        }
    
    def calculate_lp_turbine_expansion(self,
                                     inlet_pressure: float,
                                     inlet_temperature: float,
                                     inlet_flow: float,
                                     condenser_pressure: float) -> Dict[str, float]:
        """
        Calculate low pressure turbine expansion process
        
        Physical Basis:
        - Multi-stage expansion with high efficiency
        - Expansion to condenser vacuum conditions
        - Large volume flow handling in LP stages
        
        Args:
            inlet_pressure: LP turbine inlet pressure (MPa)
            inlet_temperature: LP turbine inlet temperature (°C)
            inlet_flow: Steam mass flow rate (kg/s)
            condenser_pressure: Condenser pressure (MPa)
            
        Returns:
            Dictionary with LP turbine performance data
        """
        # Calculate inlet enthalpy (reheated steam)
        h_inlet = self._steam_enthalpy(inlet_temperature, inlet_pressure)
        s_inlet = self._steam_entropy(inlet_temperature, inlet_pressure, 1.0)
        
        # Isentropic expansion to condenser pressure
        condenser_sat_temp = self._saturation_temperature(condenser_pressure)
        h_f_condenser = self._saturation_enthalpy_liquid(condenser_pressure)
        h_g_condenser = self._saturation_enthalpy_vapor(condenser_pressure)
        s_f_condenser = self._saturation_entropy_liquid(condenser_pressure)
        s_g_condenser = self._saturation_entropy_vapor(condenser_pressure)
        
        # Expansion to condenser (always ends in wet steam region)
        quality_isentropic = (s_inlet - s_f_condenser) / (s_g_condenser - s_f_condenser)
        quality_isentropic = np.clip(quality_isentropic, 0.0, 1.0)
        h_exhaust_isentropic = h_f_condenser + quality_isentropic * (h_g_condenser - h_f_condenser)
        
        # Actual enthalpy with efficiency losses
        enthalpy_drop_isentropic = h_inlet - h_exhaust_isentropic
        enthalpy_drop_actual = self.config.lp_isentropic_efficiency * enthalpy_drop_isentropic
        h_exhaust_actual = h_inlet - enthalpy_drop_actual
        
        # Calculate actual exhaust quality
        quality_actual = (h_exhaust_actual - h_f_condenser) / (h_g_condenser - h_f_condenser)
        quality_actual = np.clip(quality_actual, self.config.min_steam_quality, 1.0)
        
        # Power calculation (accounting for double flow LP turbine)
        power_lp = inlet_flow * enthalpy_drop_actual / 1000.0  # MW
        
        # Volume flow at exhaust (important for LP turbine design)
        specific_volume_exhaust = self._specific_volume(condenser_sat_temp, condenser_pressure, quality_actual)
        volume_flow_exhaust = inlet_flow * specific_volume_exhaust  # m³/s
        
        return {
            'power_mw': power_lp,
            'exhaust_enthalpy': h_exhaust_actual,
            'exhaust_temperature': condenser_sat_temp,
            'exhaust_quality': quality_actual,
            'enthalpy_drop': enthalpy_drop_actual,
            'isentropic_efficiency': self.config.lp_isentropic_efficiency,
            'volume_flow_exhaust': volume_flow_exhaust,
            'specific_volume_exhaust': specific_volume_exhaust
        }
    
    def calculate_power_conversion(self,
                                 mechanical_power: float,
                                 load_demand: float) -> Dict[str, float]:
        """
        Calculate mechanical to electrical power conversion
        
        Args:
            mechanical_power: Turbine mechanical power (MW)
            load_demand: Electrical load demand (% of rated)
            
        Returns:
            Dictionary with power conversion results
        """
        # Mechanical losses (bearings, gearbox if present)
        power_after_mechanical = mechanical_power * self.config.mechanical_efficiency
        
        # Generator efficiency (varies with load)
        load_fraction = load_demand / 100.0
        # Generator efficiency curve (typical for large generators)
        if load_fraction > 0.25:
            gen_efficiency = self.config.generator_efficiency * (0.95 + 0.05 * load_fraction)
        else:
            gen_efficiency = self.config.generator_efficiency * 0.90
        
        # Electrical power output
        electrical_power = power_after_mechanical * gen_efficiency
        
        # Auxiliary power consumption (cooling, controls, etc.)
        auxiliary_power = 0.02 * electrical_power  # 2% of gross power
        net_electrical_power = electrical_power - auxiliary_power
        
        return {
            'mechanical_power': mechanical_power,
            'electrical_power_gross': electrical_power,
            'electrical_power_net': net_electrical_power,
            'auxiliary_power': auxiliary_power,
            'mechanical_efficiency': self.config.mechanical_efficiency,
            'generator_efficiency': gen_efficiency,
            'overall_efficiency': net_electrical_power / mechanical_power if mechanical_power > 0 else 0
        }
    
    def update_state(self,
                    steam_pressure: float,
                    steam_temperature: float,
                    steam_flow: float,
                    steam_quality: float,
                    load_demand: float,
                    dt: float) -> Dict[str, float]:
        """
        Update turbine state for one time step
        
        This integrates all turbine physics models and updates state variables
        
        Args:
            steam_pressure: Inlet steam pressure (MPa)
            steam_temperature: Inlet steam temperature (°C)
            steam_flow: Steam mass flow rate (kg/s)
            steam_quality: Steam quality at inlet (0-1)
            load_demand: Electrical load demand (% rated)
            dt: Time step (s)
            
        Returns:
            Dictionary with updated turbine state and performance
        """
        # Update inlet conditions
        self.steam_inlet_pressure = steam_pressure
        self.steam_inlet_temperature = steam_temperature
        self.steam_inlet_flow = steam_flow
        self.steam_inlet_quality = steam_quality
        
        # Governor control dynamics (first-order lag)
        load_error = load_demand - self.load_demand
        load_change_rate = load_error / self.config.governor_response_time
        
        # Rate limiting
        max_change = self.config.load_rejection_rate * dt * 100  # % per time step
        load_change_rate = np.clip(load_change_rate, -max_change, max_change)
        
        self.load_demand += load_change_rate * dt
        self.load_demand = np.clip(self.load_demand, 0, 110)  # 0-110% load range
        
        # Governor valve position
        self.governor_valve_position = self.load_demand  # Simplified linear relationship
        
        # Effective steam flow based on valve position
        effective_steam_flow = steam_flow * (self.governor_valve_position / 100.0)
        
        # HP Turbine calculation
        hp_results = self.calculate_hp_turbine_expansion(
            steam_pressure, steam_temperature, effective_steam_flow,
            steam_quality, self.config.hp_exhaust_pressure
        )
        
        # Update HP exhaust conditions
        self.hp_exhaust_pressure = self.config.hp_exhaust_pressure
        self.hp_exhaust_temperature = hp_results['exhaust_temperature']
        self.hp_exhaust_quality = hp_results['exhaust_quality']
        
        # Moisture separator and reheater
        msr_results = self.calculate_moisture_separation_reheat(
            effective_steam_flow, hp_results['exhaust_enthalpy'],
            hp_results['exhaust_quality'], self.config.lp_inlet_pressure
        )
        
        # Update LP inlet conditions
        self.lp_inlet_pressure = self.config.lp_inlet_pressure
        self.lp_inlet_temperature = msr_results['outlet_temperature']
        self.lp_inlet_quality = msr_results['outlet_quality']
        
        # LP Turbine calculation
        lp_results = self.calculate_lp_turbine_expansion(
            self.lp_inlet_pressure, self.lp_inlet_temperature,
            msr_results['steam_flow_out'], self.config.condenser_pressure
        )
        
        # Update condenser conditions
        self.condenser_pressure = self.config.condenser_pressure
        self.condenser_temperature = lp_results['exhaust_temperature']
        
        # Total mechanical power
        total_mechanical_power = hp_results['power_mw'] + lp_results['power_mw']
        
        # Power conversion
        power_results = self.calculate_power_conversion(total_mechanical_power, self.load_demand)
        
        # Update power state
        self.mechanical_power = total_mechanical_power
        self.electrical_power = power_results['electrical_power_net']
        
        # Performance metrics
        if effective_steam_flow > 0:
            self.steam_rate = effective_steam_flow / self.electrical_power * 3600  # kg/MWh
            # Heat rate calculation (simplified)
            steam_enthalpy_in = self._steam_enthalpy(steam_temperature, steam_pressure)
            condenser_enthalpy = lp_results['exhaust_enthalpy']
            cycle_efficiency = (steam_enthalpy_in - condenser_enthalpy) / steam_enthalpy_in
            self.heat_rate = 3600 / cycle_efficiency if cycle_efficiency > 0 else 0  # kJ/kWh
        else:
            self.steam_rate = 0
            self.heat_rate = 0
        
        self.overall_efficiency = power_results['overall_efficiency']
        
        return {
            # Power outputs
            'mechanical_power': self.mechanical_power,
            'electrical_power_gross': power_results['electrical_power_gross'],
            'electrical_power_net': self.electrical_power,
            'auxiliary_power': power_results['auxiliary_power'],
            
            # Turbine performance
            'hp_power': hp_results['power_mw'],
            'lp_power': lp_results['power_mw'],
            'overall_efficiency': self.overall_efficiency,
            'steam_rate': self.steam_rate,
            'heat_rate': self.heat_rate,
            
            # Steam conditions
            'hp_exhaust_pressure': self.hp_exhaust_pressure,
            'hp_exhaust_temperature': self.hp_exhaust_temperature,
            'hp_exhaust_quality': self.hp_exhaust_quality,
            'lp_inlet_pressure': self.lp_inlet_pressure,
            'lp_inlet_temperature': self.lp_inlet_temperature,
            'condenser_pressure': self.condenser_pressure,
            'condenser_temperature': self.condenser_temperature,
            
            # Control state
            'load_demand': self.load_demand,
            'governor_valve_position': self.governor_valve_position,
            'effective_steam_flow': effective_steam_flow,
            
            # Detailed results
            'hp_efficiency': hp_results['isentropic_efficiency'],
            'lp_efficiency': lp_results['isentropic_efficiency'],
            'moisture_separated': msr_results['water_separated'],
            'reheat_heat_addition': msr_results['heat_addition']
        }
    
    # Thermodynamic property methods (simplified correlations)
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """Calculate saturation temperature for given pressure"""
        if pressure_mpa <= 0.001:
            return 10.0  # Very low pressure
        
        # Antoine equation for water
        A, B, C = 8.07131, 1730.63, 233.426
        pressure_bar = pressure_mpa * 10.0
        
        # Ensure pressure is within valid range for Antoine equation
        pressure_bar = np.clip(pressure_bar, 0.01, 100.0)
        
        temp_c = B / (A - np.log10(pressure_bar)) - C
        
        # For condenser pressures (0.005-0.01 MPa), ensure reasonable temperature
        if pressure_mpa >= 0.005 and pressure_mpa <= 0.01:
            temp_c = np.clip(temp_c, 35.0, 45.0)  # Reasonable condenser temperatures
        
        return np.clip(temp_c, 10.0, 374.0)
    
    def _saturation_enthalpy_liquid(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of liquid water (kJ/kg)"""
        temp = self._saturation_temperature(pressure_mpa)
        return 4.18 * temp
    
    def _saturation_enthalpy_vapor(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of steam (kJ/kg)"""
        temp = self._saturation_temperature(pressure_mpa)
        h_f = self._saturation_enthalpy_liquid(pressure_mpa)
        h_fg = 2257.0 * (1.0 - temp / 374.0) ** 0.38
        return h_f + h_fg
    
    def _steam_enthalpy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate steam enthalpy (kJ/kg)"""
        sat_temp = self._saturation_temperature(pressure_mpa)
        if temp_c <= sat_temp:
            # Saturated steam
            return self._saturation_enthalpy_vapor(pressure_mpa)
        else:
            # Superheated steam
            h_g = self._saturation_enthalpy_vapor(pressure_mpa)
            superheat = temp_c - sat_temp
            return h_g + 2.1 * superheat  # Approximate cp for steam
    
    def _steam_entropy(self, temp_c: float, pressure_mpa: float, quality: float = 1.0) -> float:
        """Calculate steam entropy (kJ/kg/K) - simplified"""
        sat_temp = self._saturation_temperature(pressure_mpa)
        s_f = 4.18 * np.log((sat_temp + 273.15) / 273.15)  # Approximate
        s_fg = 2257.0 / (sat_temp + 273.15)  # Approximate
        
        if quality < 1.0:
            return s_f + quality * s_fg
        else:
            s_g = s_f + s_fg
            if temp_c > sat_temp:
                # Superheated
                superheat_entropy = 2.1 * np.log((temp_c + 273.15) / (sat_temp + 273.15))
                return s_g + superheat_entropy
            else:
                return s_g
    
    def _saturation_entropy_liquid(self, pressure_mpa: float) -> float:
        """Calculate saturation entropy of liquid (kJ/kg/K)"""
        temp = self._saturation_temperature(pressure_mpa)
        return 4.18 * np.log((temp + 273.15) / 273.15)
    
    def _saturation_entropy_vapor(self, pressure_mpa: float) -> float:
        """Calculate saturation entropy of vapor (kJ/kg/K)"""
        temp = self._saturation_temperature(pressure_mpa)
        s_f = self._saturation_entropy_liquid(pressure_mpa)
        s_fg = 2257.0 / (temp + 273.15)
        return s_f + s_fg
    
    def _specific_volume(self, temp_c: float, pressure_mpa: float, quality: float = 1.0) -> float:
        """Calculate specific volume (m³/kg)"""
        if quality >= 1.0:
            # Steam
            temp_k = temp_c + 273.15
            R_steam = 461.5  # J/kg/K
            pressure_pa = pressure_mpa * 1e6
            return R_steam * temp_k / pressure_pa
        else:
            # Wet steam
            v_f = 0.001  # Liquid specific volume (approximately constant)
            v_g = self._specific_volume(temp_c, pressure_mpa, 1.0)
            return v_f + quality * (v_g - v_f)
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            'steam_inlet_pressure': self.steam_inlet_pressure,
            'steam_inlet_temperature': self.steam_inlet_temperature,
            'steam_inlet_flow': self.steam_inlet_flow,
            'steam_inlet_quality': self.steam_inlet_quality,
            'hp_exhaust_pressure': self.hp_exhaust_pressure,
            'hp_exhaust_temperature': self.hp_exhaust_temperature,
            'hp_exhaust_quality': self.hp_exhaust_quality,
            'lp_inlet_pressure': self.lp_inlet_pressure,
            'lp_inlet_temperature': self.lp_inlet_temperature,
            'condenser_pressure': self.condenser_pressure,
            'condenser_temperature': self.condenser_temperature,
            'mechanical_power': self.mechanical_power,
            'electrical_power': self.electrical_power,
            'load_demand': self.load_demand,
            'governor_valve_position': self.governor_valve_position,
            'overall_efficiency': self.overall_efficiency,
            'steam_rate': self.steam_rate,
            'heat_rate': self.heat_rate
        }
    
    def reset(self) -> None:
        """Reset to initial steady-state conditions"""
        self.steam_inlet_pressure = 6.895
        self.steam_inlet_temperature = 285.8
        self.steam_inlet_flow = 1665.0
        self.steam_inlet_quality = 0.99
        self.hp_exhaust_pressure = 1.2
        self.hp_exhaust_temperature = 187.0
        self.hp_exhaust_quality = 0.92
        self.lp_inlet_pressure = 1.15
        self.lp_inlet_temperature = 185.0
        self.lp_inlet_quality = 0.99
        self.condenser_pressure = 0.007
        self.condenser_temperature = 39.0
        self.mechanical_power = 1100.0
        self.electrical_power = 1085.0
        self.power_setpoint = 1100.0
        self.governor_valve_position = 100.0
        self.load_demand = 100.0
        self.overall_efficiency = 0.0
        self.heat_rate = 0.0
        self.steam_rate = 0
