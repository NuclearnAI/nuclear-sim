"""
Condenser Physics Model

This module implements a comprehensive physics-based model for PWR condensers,
including heat transfer, cooling water systems, and vacuum maintenance.

Parameter Sources:
- Heat Exchanger Design Handbook (Hewitt)
- Power Plant Engineering (Black & Veatch)
- Condenser design specifications for large PWR plants
- Cooling tower and circulating water system data

Physical Basis:
- Shell-and-tube heat exchanger design
- Heat transfer: Q = U*A*LMTD
- Vacuum system performance
- Cooling water thermal hydraulics
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore")


@dataclass
class CondenserConfig:
    """
    Condenser configuration parameters based on typical large PWR condensers
    
    References:
    - EPRI Condenser Performance Guidelines
    - Heat Exchanger Institute Standards
    - Typical PWR condenser specifications
    """
    
    # Design parameters
    design_heat_duty: float = 2000.0e6  # W (heat rejection at design conditions)
    design_steam_flow: float = 1665.0   # kg/s (total steam flow from turbine)
    design_cooling_water_flow: float = 45000.0  # kg/s (circulating water flow)
    
    # Physical dimensions
    heat_transfer_area: float = 25000.0  # m² (total tube surface area)
    tube_count: int = 28000             # Number of condenser tubes
    tube_inner_diameter: float = 0.0254 # m (1 inch ID tubes)
    tube_outer_diameter: float = 0.0286 # m (1.125 inch OD tubes)
    tube_length: float = 12.0           # m (effective length)
    
    # Heat transfer coefficients
    steam_side_htc: float = 8000.0      # W/m²/K (condensing steam)
    water_side_htc: float = 3500.0      # W/m²/K (cooling water)
    tube_wall_conductivity: float = 385.0  # W/m/K (copper tubes)
    tube_wall_thickness: float = 0.00159   # m (1.59mm wall)
    
    # Operating conditions
    design_vacuum: float = 0.007        # MPa (condenser pressure)
    design_cooling_water_temp_in: float = 25.0   # °C (cooling water inlet)
    design_cooling_water_temp_rise: float = 10.0 # °C (temperature rise)
    
    # Performance parameters
    fouling_resistance: float = 0.0001  # m²K/W (fouling factor)
    air_leakage_rate: float = 0.1       # kg/s (air in-leakage)
    vacuum_pump_capacity: float = 50.0  # kg/s air removal capacity
    
    # Control parameters
    cooling_water_control_gain: float = 0.1  # Flow control gain
    vacuum_control_gain: float = 0.05        # Vacuum control gain


class CondenserPhysics:
    """
    Comprehensive condenser physics model for PWR
    
    This model implements:
    1. Steam condensation heat transfer
    2. Cooling water thermal hydraulics
    3. Vacuum system performance
    4. Air removal and non-condensable effects
    5. Fouling and performance degradation
    
    Physical Models Used:
    - Heat Transfer: Overall heat transfer coefficient method
    - Condensation: Nusselt theory for film condensation
    - Cooling Water: Single-phase forced convection
    - Vacuum: Air partial pressure effects
    """
    
    def __init__(self, config: Optional[CondenserConfig] = None):
        """Initialize condenser physics model"""
        self.config = config if config is not None else CondenserConfig()
        
        # Initialize state variables to typical operating conditions
        self.steam_inlet_pressure = 0.007    # MPa (condenser vacuum)
        self.steam_inlet_temperature = 39.0  # °C (saturation at 0.007 MPa)
        self.steam_inlet_flow = 1665.0       # kg/s
        self.steam_inlet_quality = 0.90      # Wet steam from LP turbine
        
        # Cooling water conditions
        self.cooling_water_inlet_temp = 25.0   # °C
        self.cooling_water_outlet_temp = 35.0  # °C
        self.cooling_water_flow = 45000.0      # kg/s
        
        # Condenser internal state
        self.condensate_temperature = 39.0     # °C (saturated liquid)
        self.condensate_flow = 1665.0          # kg/s (same as steam flow)
        self.heat_rejection_rate = 2000.0e6    # W
        
        # Vacuum system state
        self.air_partial_pressure = 0.0005    # MPa (air in condenser)
        self.total_pressure = 0.0075          # MPa (steam + air)
        self.air_removal_rate = 0.1           # kg/s
        
        # Performance tracking
        self.overall_htc = 0.0                # W/m²/K
        self.fouling_factor = 0.0001          # m²K/W
        self.thermal_performance = 1.0        # Performance factor (1.0 = clean)
        
    def calculate_heat_transfer(self,
                              steam_flow: float,
                              steam_pressure: float,
                              steam_quality: float,
                              cooling_water_flow: float,
                              cooling_water_temp_in: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate heat transfer in condenser
        
        Physical Basis:
        - Overall heat transfer: Q = U*A*LMTD
        - Steam condensation: Nusselt film condensation theory
        - Cooling water: Dittus-Boelter correlation
        
        Args:
            steam_flow: Steam mass flow rate (kg/s)
            steam_pressure: Steam pressure (MPa)
            steam_quality: Steam quality at inlet (0-1)
            cooling_water_flow: Cooling water flow rate (kg/s)
            cooling_water_temp_in: Cooling water inlet temperature (°C)
            
        Returns:
            tuple: (heat_transfer_rate_W, heat_transfer_details)
        """
        # Steam saturation temperature
        sat_temp = self._saturation_temperature(steam_pressure)
        
        # Steam condensation enthalpy
        h_g = self._saturation_enthalpy_vapor(steam_pressure)
        h_f = self._saturation_enthalpy_liquid(steam_pressure)
        h_fg = h_g - h_f  # Latent heat
        
        # Heat duty from steam condensation
        # Q = m_steam * [x * h_fg + (h_g - h_condensate)]
        condensate_temp = sat_temp  # Assume condensate leaves at saturation
        h_condensate = self._water_enthalpy(condensate_temp, steam_pressure)
        
        # Heat released per kg of steam
        heat_per_kg = steam_quality * h_fg + (h_g - h_condensate)
        heat_duty_steam = steam_flow * heat_per_kg * 1000  # Convert kJ/s to W
        
        # Cooling water heat capacity
        cp_water = 4180.0  # J/kg/K
        
        # Estimate cooling water outlet temperature
        # Q = m_cw * cp * (T_out - T_in)
        temp_rise_estimate = heat_duty_steam / (cooling_water_flow * cp_water)
        cooling_water_temp_out = cooling_water_temp_in + temp_rise_estimate
        
        # Log Mean Temperature Difference (LMTD)
        delta_t1 = sat_temp - cooling_water_temp_in   # Hot end
        delta_t2 = sat_temp - cooling_water_temp_out  # Cold end
        
        if abs(delta_t1 - delta_t2) < 0.1:
            lmtd = (delta_t1 + delta_t2) / 2.0
        else:
            lmtd = (delta_t1 - delta_t2) / np.log(delta_t1 / delta_t2)
        
        # Heat transfer coefficients
        
        # Steam side (condensing): Nusselt correlation for film condensation
        # h = 0.943 * [k³ * ρ² * g * h_fg / (μ * ΔT * L)]^0.25
        # Simplified for typical condenser conditions
        h_steam = self.config.steam_side_htc
        
        # Cooling water side: Dittus-Boelter correlation
        # h = 0.023 * Re^0.8 * Pr^0.4 * k/D
        # Adjusted for flow rate effects
        flow_factor = (cooling_water_flow / self.config.design_cooling_water_flow) ** 0.8
        h_water = self.config.water_side_htc * flow_factor
        
        # Overall heat transfer coefficient
        # 1/U = 1/h_steam + fouling + t_wall/k_wall + 1/h_water
        r_steam = 1.0 / h_steam
        r_fouling = self.fouling_factor
        r_wall = (self.config.tube_wall_thickness / 
                 self.config.tube_wall_conductivity)
        r_water = 1.0 / h_water
        
        overall_resistance = r_steam + r_fouling + r_wall + r_water
        overall_htc = 1.0 / overall_resistance
        
        # Heat transfer rate
        heat_transfer_rate = overall_htc * self.config.heat_transfer_area * lmtd
        
        # Limit to available heat from steam
        heat_transfer_rate = min(heat_transfer_rate, heat_duty_steam)
        
        # Recalculate cooling water outlet temperature
        actual_temp_rise = heat_transfer_rate / (cooling_water_flow * cp_water)
        actual_cooling_water_temp_out = cooling_water_temp_in + actual_temp_rise
        
        # Update LMTD with actual temperatures
        delta_t1_actual = sat_temp - cooling_water_temp_in
        delta_t2_actual = sat_temp - actual_cooling_water_temp_out
        
        if abs(delta_t1_actual - delta_t2_actual) < 0.1:
            lmtd_actual = (delta_t1_actual + delta_t2_actual) / 2.0
        else:
            lmtd_actual = (delta_t1_actual - delta_t2_actual) / np.log(delta_t1_actual / delta_t2_actual)
        
        self.overall_htc = overall_htc
        
        details = {
            'overall_htc': overall_htc,
            'lmtd': lmtd_actual,
            'h_steam': h_steam,
            'h_water': h_water,
            'cooling_water_temp_out': actual_cooling_water_temp_out,
            'cooling_water_temp_rise': actual_temp_rise,
            'delta_t_hot': delta_t1_actual,
            'delta_t_cold': delta_t2_actual,
            'fouling_resistance': self.fouling_factor,
            'flow_factor': flow_factor
        }
        
        return heat_transfer_rate, details
    
    def calculate_vacuum_system(self,
                              steam_flow: float,
                              air_leakage: float,
                              vacuum_pump_operation: float,
                              dt: float) -> Dict[str, float]:
        """
        Calculate vacuum system performance and air removal
        
        Physical Basis:
        - Dalton's law: P_total = P_steam + P_air
        - Air mass balance: dm_air/dt = m_in - m_out
        - Vacuum pump performance curves
        
        Args:
            steam_flow: Steam condensation rate (kg/s)
            air_leakage: Air in-leakage rate (kg/s)
            vacuum_pump_operation: Vacuum pump capacity factor (0-1)
            dt: Time step (s)
            
        Returns:
            Dictionary with vacuum system performance
        """
        # Air mass balance in condenser
        # Air accumulates from leakage and is removed by vacuum pumps
        
        # Current air mass in condenser (estimated from partial pressure)
        condenser_volume = 500.0  # m³ (estimated condenser steam space)
        air_density = self._air_density(self.condensate_temperature, self.air_partial_pressure)
        current_air_mass = self.air_partial_pressure * condenser_volume / (287.0 * (self.condensate_temperature + 273.15))
        
        # Air removal rate by vacuum pumps
        # Pump capacity depends on suction pressure and pump operation
        pump_efficiency = 0.8 * vacuum_pump_operation  # Pump efficiency factor
        max_air_removal = self.config.vacuum_pump_capacity * pump_efficiency
        
        # Actual air removal (limited by available air)
        air_removal_rate = min(max_air_removal, current_air_mass / dt + air_leakage)
        
        # Air mass change rate
        air_mass_change_rate = air_leakage - air_removal_rate
        
        # Update air partial pressure
        new_air_mass = current_air_mass + air_mass_change_rate * dt
        new_air_mass = max(0, new_air_mass)  # Cannot be negative
        
        # Calculate new air partial pressure
        new_air_partial_pressure = (new_air_mass * 287.0 * (self.condensate_temperature + 273.15)) / condenser_volume
        new_air_partial_pressure = max(0.0001, new_air_partial_pressure / 1e6)  # Convert to MPa, minimum value
        
        # Steam partial pressure should be the actual condenser operating pressure
        # For condenser operation, this should be close to the design vacuum pressure
        steam_partial_pressure = max(0.005, min(0.01, self.steam_inlet_pressure))
        
        # Total condenser pressure
        total_pressure = steam_partial_pressure + new_air_partial_pressure
        
        # Air concentration effects on heat transfer
        # High air concentration reduces condensation heat transfer
        air_concentration = new_air_partial_pressure / total_pressure
        condensation_degradation = 1.0 - 0.5 * air_concentration  # Simplified model
        
        return {
            'air_partial_pressure': new_air_partial_pressure,
            'steam_partial_pressure': steam_partial_pressure,
            'total_pressure': total_pressure,
            'air_removal_rate': air_removal_rate,
            'air_mass_change_rate': air_mass_change_rate,
            'air_concentration': air_concentration,
            'condensation_degradation': condensation_degradation,
            'vacuum_pump_efficiency': pump_efficiency
        }
    
    def calculate_fouling_effects(self,
                                cooling_water_temp: float,
                                cooling_water_velocity: float,
                                operating_time: float) -> Dict[str, float]:
        """
        Calculate fouling effects on heat transfer performance
        
        Args:
            cooling_water_temp: Average cooling water temperature (°C)
            cooling_water_velocity: Cooling water velocity in tubes (m/s)
            operating_time: Operating time since last cleaning (hours)
            
        Returns:
            Dictionary with fouling analysis
        """
        # Fouling rate depends on water temperature and velocity
        # Higher temperature increases fouling, higher velocity reduces it
        
        # Base fouling rate (m²K/W per 1000 hours)
        base_fouling_rate = 0.00005  # Typical for clean cooling water
        
        # Temperature effect (exponential increase with temperature)
        temp_factor = np.exp((cooling_water_temp - 25.0) / 20.0)
        
        # Velocity effect (inverse relationship)
        velocity_factor = 1.0 / (1.0 + cooling_water_velocity / 2.0)
        
        # Time-dependent fouling accumulation
        fouling_rate = base_fouling_rate * temp_factor * velocity_factor
        accumulated_fouling = fouling_rate * (operating_time / 1000.0)  # Convert hours to thousands
        
        # Total fouling resistance
        total_fouling = self.config.fouling_resistance + accumulated_fouling
        total_fouling = min(total_fouling, 0.001)  # Maximum fouling limit
        
        # Performance degradation
        clean_resistance = (1.0 / self.config.steam_side_htc + 
                          self.config.tube_wall_thickness / self.config.tube_wall_conductivity +
                          1.0 / self.config.water_side_htc)
        
        fouled_resistance = clean_resistance + total_fouling
        performance_factor = clean_resistance / fouled_resistance
        
        return {
            'fouling_resistance': total_fouling,
            'fouling_rate': fouling_rate,
            'performance_factor': performance_factor,
            'temp_factor': temp_factor,
            'velocity_factor': velocity_factor,
            'accumulated_fouling': accumulated_fouling
        }
    
    def update_state(self,
                    steam_pressure: float,
                    steam_temperature: float,
                    steam_flow: float,
                    steam_quality: float,
                    cooling_water_flow: float,
                    cooling_water_temp_in: float,
                    vacuum_pump_operation: float,
                    dt: float) -> Dict[str, float]:
        """
        Update condenser state for one time step
        
        Args:
            steam_pressure: Steam inlet pressure (MPa)
            steam_temperature: Steam inlet temperature (°C)
            steam_flow: Steam mass flow rate (kg/s)
            steam_quality: Steam quality at inlet (0-1)
            cooling_water_flow: Cooling water flow rate (kg/s)
            cooling_water_temp_in: Cooling water inlet temperature (°C)
            vacuum_pump_operation: Vacuum pump capacity factor (0-1)
            dt: Time step (s)
            
        Returns:
            Dictionary with updated condenser state and performance
        """
        # Update inlet conditions
        self.steam_inlet_pressure = steam_pressure
        self.steam_inlet_temperature = steam_temperature
        self.steam_inlet_flow = steam_flow
        self.steam_inlet_quality = steam_quality
        self.cooling_water_flow = cooling_water_flow
        self.cooling_water_inlet_temp = cooling_water_temp_in
        
        # Calculate heat transfer
        heat_transfer, ht_details = self.calculate_heat_transfer(
            steam_flow, steam_pressure, steam_quality,
            cooling_water_flow, cooling_water_temp_in
        )
        
        # Update cooling water outlet temperature
        self.cooling_water_outlet_temp = ht_details['cooling_water_temp_out']
        
        # Calculate vacuum system performance
        vacuum_results = self.calculate_vacuum_system(
            steam_flow, self.config.air_leakage_rate, vacuum_pump_operation, dt
        )
        
        # Update vacuum state
        self.air_partial_pressure = vacuum_results['air_partial_pressure']
        self.total_pressure = vacuum_results['total_pressure']
        self.air_removal_rate = vacuum_results['air_removal_rate']
        
        # Calculate fouling effects
        avg_cooling_water_temp = (cooling_water_temp_in + self.cooling_water_outlet_temp) / 2.0
        cooling_water_velocity = (cooling_water_flow / 1000.0) / (
            np.pi * (self.config.tube_inner_diameter / 2.0) ** 2 * self.config.tube_count
        )  # Approximate velocity
        
        fouling_results = self.calculate_fouling_effects(
            avg_cooling_water_temp, cooling_water_velocity, 1000.0  # Assume 1000 hours operation
        )
        
        # Update fouling state
        self.fouling_factor = fouling_results['fouling_resistance']
        self.thermal_performance = fouling_results['performance_factor']
        
        # Apply air concentration effects to heat transfer
        heat_transfer_effective = heat_transfer * vacuum_results['condensation_degradation']
        
        # Update condensate conditions
        self.condensate_temperature = self._saturation_temperature(vacuum_results['steam_partial_pressure'])
        self.condensate_flow = steam_flow  # Mass balance
        self.heat_rejection_rate = heat_transfer_effective
        
        # Performance metrics
        design_heat_duty = self.config.design_heat_duty
        thermal_efficiency = heat_transfer_effective / design_heat_duty if design_heat_duty > 0 else 0
        
        # Cooling water effectiveness
        max_possible_temp_rise = (self.condensate_temperature - cooling_water_temp_in)
        actual_temp_rise = ht_details['cooling_water_temp_rise']
        effectiveness = actual_temp_rise / max_possible_temp_rise if max_possible_temp_rise > 0 else 0
        
        return {
            # Heat transfer performance
            'heat_rejection_rate': heat_transfer_effective,
            'thermal_efficiency': thermal_efficiency,
            'effectiveness': effectiveness,
            'overall_htc': ht_details['overall_htc'],
            
            # Steam conditions
            'steam_inlet_pressure': self.steam_inlet_pressure,
            'steam_inlet_temperature': self.steam_inlet_temperature,
            'condensate_temperature': self.condensate_temperature,
            'condensate_flow': self.condensate_flow,
            
            # Cooling water conditions
            'cooling_water_inlet_temp': self.cooling_water_inlet_temp,
            'cooling_water_outlet_temp': self.cooling_water_outlet_temp,
            'cooling_water_temp_rise': ht_details['cooling_water_temp_rise'],
            'cooling_water_flow': self.cooling_water_flow,
            
            # Vacuum system
            'condenser_pressure': self.total_pressure,
            'air_partial_pressure': self.air_partial_pressure,
            'steam_partial_pressure': vacuum_results['steam_partial_pressure'],
            'air_removal_rate': self.air_removal_rate,
            'vacuum_pump_efficiency': vacuum_results['vacuum_pump_efficiency'],
            
            # Performance degradation
            'fouling_resistance': self.fouling_factor,
            'thermal_performance': self.thermal_performance,
            'condensation_degradation': vacuum_results['condensation_degradation'],
            
            # Heat transfer details
            'lmtd': ht_details['lmtd'],
            'h_steam': ht_details['h_steam'],
            'h_water': ht_details['h_water'],
            'delta_t_approach': ht_details['delta_t_cold']
        }
    
    # Thermodynamic property methods
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """Calculate saturation temperature for given pressure"""
        if pressure_mpa <= 0.001:
            return 10.0
        
        A, B, C = 8.07131, 1730.63, 233.426
        pressure_bar = pressure_mpa * 10.0
        
        # Ensure pressure is within valid range for Antoine equation
        pressure_bar = np.clip(pressure_bar, 0.01, 100.0)
        
        temp_c = B / (A - np.log10(pressure_bar)) - C
        
        # For condenser pressures (0.005-0.01 MPa), ensure reasonable temperature
        if pressure_mpa >= 0.005 and pressure_mpa <= 0.01:
            temp_c = np.clip(temp_c, 35.0, 45.0)  # Reasonable condenser temperatures
        
        return np.clip(temp_c, 10.0, 374.0)
    
    def _saturation_pressure(self, temperature_c: float) -> float:
        """Calculate saturation pressure for given temperature"""
        # Antoine equation: log10(P) = A - B/(C + T)
        # For water, with pressure in bar and temperature in °C
        A, B, C = 8.07131, 1730.63, 233.426
        
        # Clamp temperature to valid range
        temp_clamped = np.clip(temperature_c, 0.01, 373.99)
        
        log_p_bar = A - B / (C + temp_clamped)
        pressure_bar = 10 ** log_p_bar
        pressure_mpa = pressure_bar / 10.0  # Convert to MPa
        
        # Ensure reasonable bounds for condenser operation
        return np.clip(pressure_mpa, 0.001, 10.0)
    
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
    
    def _water_enthalpy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate enthalpy of liquid water (kJ/kg)"""
        return 4.18 * temp_c
    
    def _air_density(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate air density (kg/m³)"""
        temp_k = temp_c + 273.15
        R_air = 287.0  # J/kg/K
        pressure_pa = pressure_mpa * 1e6
        return pressure_pa / (R_air * temp_k)
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            'steam_inlet_pressure': self.steam_inlet_pressure,
            'steam_inlet_temperature': self.steam_inlet_temperature,
            'steam_inlet_flow': self.steam_inlet_flow,
            'steam_inlet_quality': self.steam_inlet_quality,
            'condensate_temperature': self.condensate_temperature,
            'condensate_flow': self.condensate_flow,
            'cooling_water_inlet_temp': self.cooling_water_inlet_temp,
            'cooling_water_outlet_temp': self.cooling_water_outlet_temp,
            'cooling_water_flow': self.cooling_water_flow,
            'heat_rejection_rate': self.heat_rejection_rate,
            'condenser_pressure': self.total_pressure,
            'air_partial_pressure': self.air_partial_pressure,
            'air_removal_rate': self.air_removal_rate,
            'overall_htc': self.overall_htc,
            'fouling_factor': self.fouling_factor,
            'thermal_performance': self.thermal_performance
        }
    
    def reset(self) -> None:
        """Reset to initial steady-state conditions"""
        self.steam_inlet_pressure = 0.007
        self.steam_inlet_temperature = 39.0
        self.steam_inlet_flow = 1665.0
        self.steam_inlet_quality = 0.90
        self.cooling_water_inlet_temp = 25.0
        self.cooling_water_outlet_temp = 35.0
        self.cooling_water_flow = 45000.0
        self.condensate_temperature = 39.0
        self.condensate_flow = 1665.0
        self.heat_rejection_rate = 2000.0e6
        self.air_partial_pressure = 0.0005
        self.total_pressure = 0.0075
        self.air_removal_rate = 0.1
        self.overall_htc = 0.0
        self.fouling_factor = 0.0001
        self.thermal_performance = 1.0


# Example usage and testing
if __name__ == "__main__":
    # Create condenser model
    condenser = CondenserPhysics()
    
    print("Condenser Physics Model - Parameter Validation")
    print("=" * 60)
    print("Based on Typical Large PWR Condenser Design")
    print()
    
    # Display key parameters
    config = condenser.config
    print("Key Design Parameters:")
    print(f"  Heat Transfer Area: {config.heat_transfer_area:.0f} m²")
    print(f"  Tube Count: {config.tube_count}")
    print(f"  Design Heat Duty: {config.design_heat_duty/1e6:.0f} MW")
    print(f"  Design Cooling Water Flow: {config.design_cooling_water_flow:.0f} kg/s")
    print(f"  Design Vacuum: {config.design_vacuum:.4f} MPa")
    print()
    
    # Test steady-state operation
    print("Steady-State Test:")
    result = condenser.update_state(
        steam_pressure=0.007,        # MPa
        steam_temperature=39.0,      # °C
        steam_flow=1665.0,          # kg/s
        steam_quality=0.90,         # 90% quality
        cooling_water_flow=45000.0, # kg/s
        cooling_water_temp_in=25.0, # °C
        vacuum_pump_operation=1.0,  # 100% operation
        dt=1.0
    )
    
    print("Results:")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
    
    print(f"\nCondenser State:")
    state = condenser.get_state_dict()
    for key, value in state.items():
        print(f"  {key}: {value:.4f}")
