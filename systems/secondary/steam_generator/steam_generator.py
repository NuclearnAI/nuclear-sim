"""
Steam Generator Physics Model

This module implements a comprehensive physics-based model for PWR steam generators,
with parameters based on typical commercial PWR designs (Westinghouse 4-loop).

Parameter Sources:
- Westinghouse AP1000 Design Control Document
- NUREG-1150: Severe Accident Risks
- Todreas & Kazimi: Nuclear Systems I & II
- El-Wakil: Nuclear Heat Transport
- Operating experience from commercial PWRs

Physical Basis:
- Heat transfer: Dittus-Boelter and Chen correlations
- Two-phase flow: Homogeneous equilibrium model
- Thermodynamics: NIST steam tables (simplified correlations)
- Mass/energy balance: First principles conservation equations
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

# Import state management interfaces
# Removed StateProviderMixin import - this is now an individual unit managed by enhanced system

warnings.filterwarnings("ignore")


@dataclass
class SteamGeneratorConfig:
    """
    Steam generator configuration parameters based on Westinghouse Model F design
    
    References:
    - Westinghouse AP1000 DCD Chapter 5
    - NUREG-0800 Standard Review Plan
    - Steam Generator Reference Book (EPRI)
    """
    
    # Physical dimensions (Westinghouse Model F basis)
    heat_transfer_area: float = 5100.0  # m² (AP1000: ~5100 m² per SG)
    tube_count: int = 3388  # Number of U-tubes (AP1000 actual count)
    tube_inner_diameter: float = 0.0191  # m (3/4" tubes, 19.1mm ID)
    tube_outer_diameter: float = 0.0222  # m (22.2mm OD)
    tube_length: float = 19.8  # m effective heat transfer length
    
    # Heat transfer coefficients (from Dittus-Boelter correlation)
    # Primary side: Nu = 0.023 * Re^0.8 * Pr^0.4
    # For PWR conditions: Re ~3e5, Pr ~0.9, k ~0.6 W/m/K
    primary_htc: float = 28000.0  # W/m²/K (typical range 25000-35000)
    
    # Secondary side: Chen correlation for nucleate boiling
    # Typical values for PWR steam generators: 15000-25000 W/m²/K
    secondary_htc: float = 18000.0  # W/m²/K
    
    # Tube material properties (Inconel 690)
    tube_wall_conductivity: float = 16.2  # W/m/K (Inconel 690 at 300°C)
    tube_wall_thickness: float = 0.00155  # m (1.55mm wall thickness)
    
    # Operating parameters (AP1000 design basis)
    design_thermal_power: float = 1085.0e6  # W per SG (3255 MWt / 3 SGs)
    primary_design_flow: float = 5700.0  # kg/s per SG (AP1000: 17100 kg/s total / 3)
    secondary_design_flow: float = 555.0  # kg/s steam flow per SG
    
    # Design pressures (typical PWR values)
    design_pressure_primary: float = 15.51  # MPa (2250 psia)
    design_pressure_secondary: float = 6.895  # MPa (1000 psia)
    
    # Steam generator inventory (based on AP1000 design)
    secondary_water_mass: float = 68000.0  # kg total water inventory per SG
    steam_dome_volume: float = 28.0  # m³ steam space volume
    
    # Control parameters (tuned for realistic response)
    feedwater_control_gain: float = 0.08  # Proportional gain for level control
    steam_pressure_control_gain: float = 0.05  # Proportional gain for pressure control


class SteamGenerator:
    """
    Individual steam generator physics model for PWR
    
    This model implements the core physics for a single steam generator:
    1. Heat transfer from primary to secondary (U-tube bundle)
    2. Two-phase flow dynamics on secondary side
    3. Mass and energy balance equations
    4. Steam quality and void fraction calculations
    5. Water level dynamics with swell effects
    
    Physical Models Used:
    - Heat Transfer: Overall heat transfer coefficient method
    - Two-Phase Flow: Homogeneous equilibrium model
    - Steam Properties: Simplified NIST correlations
    - Level Dynamics: Mass balance with density effects
    
    Note: This is an individual unit managed by EnhancedSteamGeneratorPhysics.
    Does not inherit from StateProviderMixin to prevent duplicate registration.
    """
    
    def __init__(self, config: Optional[SteamGeneratorConfig] = None):
        """Initialize steam generator physics model"""
        self.config = config if config is not None else SteamGeneratorConfig()
        
        # Initialize state variables to typical PWR operating conditions
        # Primary side (hot leg inlet, cold leg outlet)
        self.primary_inlet_temp = 327.0  # °C (621°F - typical PWR hot leg)
        self.primary_outlet_temp = 293.0  # °C (559°F - typical PWR cold leg)
        
        # Secondary side (saturated steam conditions)
        self.secondary_pressure = 6.895  # MPa (1000 psia - typical PWR steam pressure)
        self.secondary_temperature = 285.8  # °C (saturation temp at 6.895 MPa)
        
        # Steam generator internal state
        self.steam_quality = 0.99  # Steam outlet quality (PWR steam generators produce dry steam)
        self.water_level = 12.5  # m above tube sheet (normal operating level)
        self.steam_void_fraction = 0.45  # Volume fraction of steam in two-phase region
        
        # Flow rates (steady-state design values)
        self.steam_flow_rate = 555.0  # kg/s
        self.feedwater_flow_rate = 555.0  # kg/s (mass balance)
        self.feedwater_temperature = 227.0  # °C (441°F - typical feedwater temp)
        
        # Calculated parameters
        self.tube_wall_temp = 310.0  # °C (between primary and secondary temps)
        self.heat_transfer_rate = 1085.0e6  # W (design thermal power)
        
        # Performance tracking
        self.overall_htc = 0.0  # Will be calculated
        self.heat_flux = 0.0  # W/m²
        
    def calculate_effective_heat_transfer_area(self, water_level: float) -> float:
        """
        Calculate effective heat transfer area based on water level
        
        Physical Basis:
        - Heat transfer only occurs where tubes are submerged in water
        - Lower water level reduces wetted surface area
        - Below minimum level, only emergency heat transfer possible
        
        Args:
            water_level: Current steam generator water level (m)
            
        Returns:
            Effective heat transfer area (m²)
        """
        normal_level = 12.5  # m (normal operating level)
        design_area = self.config.heat_transfer_area  # m² (full design area)
        
        # Level factor: relationship between level and wetted area
        if water_level >= normal_level:
            # Above normal level - full area available
            level_factor = 1.0
        else:
            # Below normal level - reduced area
            min_level = 8.0  # m (minimum level for meaningful heat transfer)
            
            if water_level <= min_level:
                # Emergency level - only minimal heat transfer possible
                level_factor = 0.1  # 10% of design area
            else:
                # Linear interpolation between minimum and normal level
                level_factor = 0.1 + 0.9 * (water_level - min_level) / (normal_level - min_level)
        
        effective_area = design_area * level_factor
        return effective_area

    def calculate_heat_transfer(self, 
                              primary_temp_in: float,
                              primary_temp_out: float,
                              primary_flow: float,
                              secondary_pressure: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate heat transfer from primary to secondary side using overall HTC method
        
        Physical Basis:
        - Overall heat transfer: Q = U * A_eff * LMTD
        - Effective area depends on water level (wetted surface area)
        - Thermal resistance network: 1/U = 1/h_p + t_w/k_w + 1/h_s
        - Log mean temperature difference for counter-current flow
        
        Args:
            primary_temp_in: Primary coolant inlet temperature (°C)
            primary_temp_out: Primary coolant outlet temperature (°C)  
            primary_flow: Primary coolant flow rate (kg/s)
            secondary_pressure: Secondary side pressure (MPa)
            
        Returns:
            tuple: (heat_transfer_rate_W, heat_transfer_details)
        """
        # Calculate saturation temperature for secondary pressure
        # Using Antoine equation for water: log10(P) = A - B/(C + T)
        # Rearranged: T = B/(A - log10(P)) - C
        # Simplified correlation valid for 1-10 MPa
        sat_temp = self._saturation_temperature(secondary_pressure)
        
        # Log Mean Temperature Difference (LMTD) calculation
        # For counter-current flow in U-tube steam generator
        delta_t1 = primary_temp_in - sat_temp  # Hot end temperature difference
        delta_t2 = primary_temp_out - sat_temp  # Cold end temperature difference
        
        if abs(delta_t1 - delta_t2) < 1.0:
            # Avoid division by zero for small temperature differences
            lmtd = (delta_t1 + delta_t2) / 2.0
        else:
            lmtd = (delta_t1 - delta_t2) / np.log(delta_t1 / delta_t2)
        
        # Overall heat transfer coefficient calculation
        # Thermal resistance network: R_total = R_primary + R_wall + R_secondary
        
        # Primary side heat transfer coefficient (turbulent flow in tubes)
        # Adjusted for flow rate effects: h ∝ flow^0.8
        flow_factor = (primary_flow / self.config.primary_design_flow) ** 0.8
        h_primary = self.config.primary_htc * flow_factor
        
        # Secondary side heat transfer coefficient (nucleate boiling)
        # Pressure effect on boiling: h ∝ P^0.15 (Chen correlation)
        pressure_factor = (secondary_pressure / self.config.design_pressure_secondary) ** 0.15
        h_secondary = self.config.secondary_htc * pressure_factor
        
        # Thermal resistances
        r_primary = 1.0 / h_primary
        r_wall = self.config.tube_wall_thickness / self.config.tube_wall_conductivity
        r_secondary = 1.0 / h_secondary
        
        # Overall heat transfer coefficient
        overall_htc = 1.0 / (r_primary + r_wall + r_secondary)
        
        # Calculate effective heat transfer area based on current water level
        effective_area = self.calculate_effective_heat_transfer_area(self.water_level)
        
        # Heat transfer rate using effective area (level-dependent)
        heat_transfer_rate = overall_htc * effective_area * lmtd
        
        # ENHANCED PHYSICAL CONSTRAINTS: cannot exceed energy available from primary coolant
        # Q_max = m_dot * cp * (T_in - T_out)
        cp_primary = 5200.0  # J/kg/K (specific heat of water at PWR conditions)
        max_heat_from_primary = primary_flow * cp_primary * (primary_temp_in - primary_temp_out)
        
        # STRICT ENERGY CONSERVATION: Additional checks for zero/low thermal power scenarios
        # If primary temperature difference is very small, severely limit heat transfer
        temp_difference = primary_temp_in - primary_temp_out
        if temp_difference < 1.0:  # Less than 1°C difference
            heat_transfer_rate = 0.0  # No meaningful heat transfer possible
        elif temp_difference < 5.0:  # Less than 5°C difference  
            # Severely reduced heat transfer for low temperature differences
            heat_transfer_rate = min(heat_transfer_rate, max_heat_from_primary * 0.1)
        else:
            # Normal operation - limit to available primary energy
            heat_transfer_rate = min(heat_transfer_rate, max_heat_from_primary)
        
        # Additional check: if primary flow is very low, limit heat transfer
        if primary_flow < 100.0:  # Less than 100 kg/s (very low flow)
            heat_transfer_rate = 0.0
        
        # Final validation: ensure heat transfer is physically reasonable
        if heat_transfer_rate < 0:
            heat_transfer_rate = 0.0
        
        # Calculate tube wall temperature (thermal circuit analysis)
        heat_flux = heat_transfer_rate / self.config.heat_transfer_area
        primary_avg_temp = (primary_temp_in + primary_temp_out) / 2.0
        
        # Temperature drop from primary fluid to tube wall
        delta_t_primary = heat_flux / h_primary
        tube_wall_temp_inner = primary_avg_temp - delta_t_primary
        
        # Temperature drop across tube wall
        delta_t_wall = heat_flux * r_wall
        tube_wall_temp_outer = tube_wall_temp_inner - delta_t_wall
        
        self.tube_wall_temp = (tube_wall_temp_inner + tube_wall_temp_outer) / 2.0
        self.overall_htc = overall_htc
        self.heat_flux = heat_flux
        
        details = {
            'overall_htc': overall_htc,
            'lmtd': lmtd,
            'sat_temp_secondary': sat_temp,
            'tube_wall_temp': self.tube_wall_temp,
            'heat_flux': heat_flux,
            'h_primary': h_primary,
            'h_secondary': h_secondary,
            'delta_t1': delta_t1,
            'delta_t2': delta_t2,
            'flow_factor': flow_factor,
            'pressure_factor': pressure_factor
        }
        
        return heat_transfer_rate, details
    
    def calculate_secondary_side_dynamics(self,
                                        heat_input: float,
                                        steam_flow_out: float,
                                        feedwater_flow_in: float,
                                        feedwater_temp: float,
                                        dt: float) -> Dict[str, float]:
        """
        Calculate secondary side mass and energy balance with two-phase flow effects
        
        Physical Basis:
        - Mass balance: dm/dt = m_in - m_out
        - Energy balance: dE/dt = H_in - H_out + Q_in
        - Pressure dynamics: Based on steam demand and inventory changes
        - Steam quality: Based on moisture separation efficiency and design
        
        Args:
            heat_input: Heat transfer rate from primary (W)
            steam_flow_out: Steam flow rate leaving SG (kg/s)
            feedwater_flow_in: Feedwater flow rate entering SG (kg/s)
            feedwater_temp: Feedwater temperature (°C)
            dt: Time step (s)
            
        Returns:
            Dictionary with secondary side state changes
        """
        # Current thermodynamic properties
        sat_temp = self._saturation_temperature(self.secondary_pressure)
        h_f = self._saturation_enthalpy_liquid(self.secondary_pressure)  # kJ/kg
        h_g = self._saturation_enthalpy_vapor(self.secondary_pressure)   # kJ/kg
        h_fg = h_g - h_f  # Latent heat of vaporization
        h_fw = self._water_enthalpy(feedwater_temp, self.secondary_pressure)  # kJ/kg
        
        # Fluid densities
        rho_f = self._water_density(sat_temp, self.secondary_pressure)  # kg/m³
        rho_g = self._steam_density(sat_temp, self.secondary_pressure)  # kg/m³
        
        # Mass balance
        mass_change_rate = feedwater_flow_in - steam_flow_out  # kg/s
        
        # Energy balance (convert heat_input to kJ/s)
        heat_input_kj = heat_input / 1000.0  # Convert W to kJ/s
        
        # Steam generation rate from energy balance
        # Energy available for steam generation = heat input - sensible heating of feedwater
        energy_for_steam_gen = heat_input_kj - feedwater_flow_in * (h_f - h_fw)
        steam_generation_rate = energy_for_steam_gen / h_fg  # kg/s
        steam_generation_rate = max(0, steam_generation_rate)  # Cannot be negative
        
        # CRITICAL FIX: If feedwater flow is zero, steam generation must be zero
        # Cannot generate steam without feedwater input
        if feedwater_flow_in < 0.1:  # Less than 0.1 kg/s (essentially zero)
            steam_generation_rate = 0.0
        
        # FIXED PRESSURE DYNAMICS - Based on steam demand and inventory, NOT energy balance
        # Pressure responds to steam flow demand vs steam generation capability
        steam_demand_factor = steam_flow_out / self.config.secondary_design_flow  # Normalized demand
        steam_supply_factor = steam_generation_rate / self.config.secondary_design_flow  # Normalized supply
        
        # Pressure change based on supply-demand imbalance
        supply_demand_imbalance = steam_supply_factor - steam_demand_factor
        
        # Pressure dynamics: higher demand -> lower pressure, higher supply -> higher pressure
        base_pressure_change_rate = -supply_demand_imbalance * 0.01  # MPa/s (tuned for realistic response)
        
        # Additional pressure effects
        # 1. Inventory depletion effect
        if feedwater_flow_in < 0.1 and steam_flow_out > 0.1:
            # Rapid pressure drop when steam is extracted without feedwater replacement
            inventory_depletion_rate = -steam_flow_out / self.config.secondary_water_mass  # 1/s
            pressure_drop_rate = inventory_depletion_rate * self.secondary_pressure * 5.0
            base_pressure_change_rate += pressure_drop_rate
        
        # 2. Heat input effect (secondary effect on pressure)
        design_heat_input = self.config.design_thermal_power / 1000.0  # kJ/s
        heat_input_factor = heat_input_kj / design_heat_input
        heat_pressure_effect = (heat_input_factor - 1.0) * 0.002  # Small effect: 0.2% per 100% heat change
        
        pressure_change_rate = base_pressure_change_rate + heat_pressure_effect
        pressure_change_rate = np.clip(pressure_change_rate, -0.05, 0.05)  # Limit rate of change
        
        new_pressure = self.secondary_pressure + pressure_change_rate * dt
        new_pressure = np.clip(new_pressure, 0.1, 8.5)  # Physical limits
        
        # Water level dynamics with swell effects
        # Cross-sectional area of steam generator (simplified cylindrical geometry)
        sg_diameter = 4.0  # m (typical large PWR steam generator)
        sg_cross_section = np.pi * (sg_diameter / 2.0) ** 2  # m²
        
        # Level change due to mass inventory change
        level_change_mass = mass_change_rate * dt / (rho_f * sg_cross_section)
        
        # Level change due to steam generation (swell effect)
        # Steam bubbles increase apparent liquid level
        specific_volume_liquid = 1.0 / rho_f
        specific_volume_steam = 1.0 / rho_g
        volume_expansion = steam_generation_rate * dt * (specific_volume_steam - specific_volume_liquid)
        level_change_swell = volume_expansion / sg_cross_section
        
        total_level_change = level_change_mass + level_change_swell
        new_water_level = self.water_level + total_level_change
        new_water_level = np.clip(new_water_level, 8.0, 16.0)  # Physical limits
        
        # FIXED STEAM QUALITY CALCULATION - Based on moisture separation physics
        # Steam quality should be relatively stable in well-designed PWR steam generators
        # and primarily depend on separator/dryer performance, not energy balance
        
        # Design steam quality for PWR (target)
        design_quality = 0.995  # 99.5% quality for well-designed PWR SG
        
        # Quality degradation factors
        quality_degradation = 0.0
        
        # 1. Water level effect - low level reduces separation efficiency
        if new_water_level < 11.0:  # Below normal operating level
            level_factor = (11.0 - new_water_level) / 3.0  # Normalized degradation
            quality_degradation += level_factor * 0.02  # Up to 2% quality loss
        
        # 2. Flow rate effect - very high steam flow reduces separation time
        flow_factor = steam_flow_out / self.config.secondary_design_flow
        if flow_factor > 1.1:  # Above 110% design flow
            flow_degradation = (flow_factor - 1.1) * 0.01  # 1% per 10% excess flow
            quality_degradation += min(flow_degradation, 0.03)  # Max 3% degradation
        
        # 3. Heat flux effect - very high heat flux can cause carryover
        design_heat_flux = self.config.design_thermal_power / self.config.heat_transfer_area
        current_heat_flux = heat_input / self.config.heat_transfer_area
        heat_flux_ratio = current_heat_flux / design_heat_flux
        if heat_flux_ratio > 1.2:  # Above 120% design heat flux
            heat_flux_degradation = (heat_flux_ratio - 1.2) * 0.005  # 0.5% per 10% excess
            quality_degradation += min(heat_flux_degradation, 0.02)  # Max 2% degradation
        
        # Calculate new steam quality
        target_quality = design_quality - quality_degradation
        target_quality = np.clip(target_quality, 0.90, 1.0)  # Physical limits
        
        # Smooth transition to target quality (first-order lag)
        quality_time_constant = 30.0  # seconds (realistic for moisture separator response)
        quality_change_rate = (target_quality - self.steam_quality) / quality_time_constant
        new_steam_quality = self.steam_quality + quality_change_rate * dt
        new_steam_quality = np.clip(new_steam_quality, 0.90, 1.0)
        
        # Void fraction from steam quality (homogeneous flow model)
        # α = x * ρ_f / (x * ρ_f + (1-x) * ρ_g)
        if new_steam_quality > 0:
            new_void_fraction = (new_steam_quality * rho_f) / (
                new_steam_quality * rho_f + (1 - new_steam_quality) * rho_g
            )
        else:
            new_void_fraction = 0.0
        
        new_void_fraction = np.clip(new_void_fraction, 0.0, 0.8)  # Physical limits
        
        # Calculate energy balance for reporting (not used for state updates)
        energy_in_feedwater = feedwater_flow_in * h_fw  # kJ/s
        energy_in_heat = heat_input_kj  # kJ/s
        energy_out_steam = steam_flow_out * h_g  # kJ/s
        energy_change_rate = energy_in_feedwater + energy_in_heat - energy_out_steam  # kJ/s
        
        return {
            'pressure_change_rate': pressure_change_rate,
            'level_change_rate': total_level_change / dt,
            'steam_quality_change': (new_steam_quality - self.steam_quality) / dt,
            'void_fraction_change': (new_void_fraction - self.steam_void_fraction) / dt,
            'new_pressure': new_pressure,
            'new_water_level': new_water_level,
            'new_steam_quality': new_steam_quality,
            'new_void_fraction': new_void_fraction,
            'steam_generation_rate': steam_generation_rate,
            'energy_balance': energy_change_rate,
            'level_change_mass': level_change_mass,
            'level_change_swell': level_change_swell,
            'mass_change_rate': mass_change_rate,
            'supply_demand_imbalance': supply_demand_imbalance,
            'quality_degradation': quality_degradation,
            'target_quality': target_quality
        }
    
    def update_state(self,
                    primary_temp_in: float,
                    primary_temp_out: float,
                    primary_flow: float,
                    steam_flow_out: float,
                    feedwater_flow_in: float,
                    feedwater_temp: float,
                    dt: float) -> Dict[str, float]:
        """
        Update steam generator state for one time step
        
        This is the main integration function that advances all state variables
        by one time step using the calculated physics models.
        
        Args:
            primary_temp_in: Primary inlet temperature (°C)
            primary_temp_out: Primary outlet temperature (°C)
            primary_flow: Primary flow rate (kg/s)
            steam_flow_out: Steam flow rate out (kg/s)
            feedwater_flow_in: Feedwater flow rate in (kg/s)
            feedwater_temp: Feedwater temperature (°C)
            dt: Time step (s)
            
        Returns:
            Dictionary with updated state and performance metrics
        """
        # Calculate heat transfer from primary to secondary
        heat_transfer, ht_details = self.calculate_heat_transfer(
            primary_temp_in, primary_temp_out, primary_flow, self.secondary_pressure
        )
        
        # Calculate secondary side dynamics
        secondary_dynamics = self.calculate_secondary_side_dynamics(
            heat_transfer, steam_flow_out, feedwater_flow_in, feedwater_temp, dt
        )
        
        # Update state variables
        self.primary_inlet_temp = primary_temp_in
        self.primary_outlet_temp = primary_temp_out
        self.secondary_pressure = secondary_dynamics['new_pressure']
        self.water_level = secondary_dynamics['new_water_level']
        self.steam_quality = secondary_dynamics['new_steam_quality']
        self.steam_void_fraction = secondary_dynamics['new_void_fraction']
        self.steam_flow_rate = steam_flow_out
        self.feedwater_flow_rate = feedwater_flow_in
        self.feedwater_temperature = feedwater_temp
        self.heat_transfer_rate = heat_transfer
        
        # Update secondary temperature (saturation temperature at current pressure)
        self.secondary_temperature = self._saturation_temperature(self.secondary_pressure)
        
        # Calculate performance metrics
        thermal_efficiency = heat_transfer / self.config.design_thermal_power
        steam_production_rate = secondary_dynamics['steam_generation_rate']
        
        # Heat transfer effectiveness
        max_possible_heat_transfer = (primary_flow * 5200.0 * 
                                    (primary_temp_in - self.secondary_temperature))
        if max_possible_heat_transfer > 0:
            effectiveness = heat_transfer / max_possible_heat_transfer
        else:
            effectiveness = 0.0
        
        return {
            # Primary outputs
            'heat_transfer_rate': heat_transfer,
            'thermal_efficiency': thermal_efficiency,
            'effectiveness': effectiveness,
            
            # Secondary side state
            'secondary_pressure': self.secondary_pressure,
            'secondary_temperature': self.secondary_temperature,
            'water_level': self.water_level,
            'steam_quality': self.steam_quality,
            'steam_void_fraction': self.steam_void_fraction,
            
            # Flow and generation rates
            'steam_production_rate': steam_production_rate,
            'steam_flow_rate': self.steam_flow_rate,
            'feedwater_flow_rate': self.feedwater_flow_rate,
            
            # Dynamics
            'pressure_change_rate': secondary_dynamics['pressure_change_rate'],
            'level_change_rate': secondary_dynamics['level_change_rate'],
            'mass_change_rate': secondary_dynamics['mass_change_rate'],
            
            # Heat transfer details
            'tube_wall_temperature': self.tube_wall_temp,
            'overall_htc': ht_details['overall_htc'],
            'heat_flux': ht_details['heat_flux'],
            'lmtd': ht_details['lmtd'],
            
            # Performance indicators
            'h_primary': ht_details['h_primary'],
            'h_secondary': ht_details['h_secondary'],
            'flow_factor': ht_details['flow_factor'],
            'pressure_factor': ht_details['pressure_factor']
        }
    
    # Thermodynamic property correlations
    # These are simplified correlations valid for PWR operating conditions
    # For production use, would use NIST REFPROP or similar
    
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
    
    def _saturation_enthalpy_liquid(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of liquid water (kJ/kg)"""
        temp = self._saturation_temperature(pressure_mpa)
        # Simplified correlation based on temperature
        # h_f ≈ cp * T for liquid water
        return 4.18 * temp  # kJ/kg
    
    def _saturation_enthalpy_vapor(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of steam (kJ/kg)"""
        temp = self._saturation_temperature(pressure_mpa)
        h_f = self._saturation_enthalpy_liquid(pressure_mpa)
        
        # Latent heat correlation (simplified)
        # h_fg decreases with pressure, goes to zero at critical point
        h_fg = 2257.0 * (1.0 - temp / 374.0) ** 0.38  # Approximate correlation
        
        return h_f + h_fg
    
    def _water_enthalpy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate enthalpy of liquid water (kJ/kg)"""
        # For liquid water, enthalpy is primarily temperature dependent
        # Small pressure correction for compressed liquid
        h_sat = 4.18 * temp_c
        pressure_correction = 0.001 * (pressure_mpa - 0.1) * temp_c  # Small correction
        return h_sat + pressure_correction
    
    def _water_density(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate density of liquid water (kg/m³)"""
        # Temperature effect dominates for liquid water
        # ρ = ρ₀ * (1 - β * ΔT) where β is thermal expansion coefficient
        rho_0 = 1000.0  # kg/m³ at 0°C
        beta = 0.0003  # 1/°C thermal expansion coefficient
        
        rho_temp = rho_0 * (1.0 - beta * temp_c)
        
        # Small pressure effect (compressibility)
        compressibility = 4.5e-10  # 1/Pa
        pressure_effect = 1.0 + compressibility * pressure_mpa * 1e6
        
        return rho_temp * pressure_effect
    
    def _steam_density(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate density of steam (kg/m³)"""
        # Ideal gas law with steam gas constant
        temp_k = temp_c + 273.15
        R_steam = 461.5  # J/kg/K specific gas constant for steam
        
        # ρ = P / (R * T)
        pressure_pa = pressure_mpa * 1e6
        density = pressure_pa / (R_steam * temp_k)
        
        return density
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            'primary_inlet_temp': self.primary_inlet_temp,
            'primary_outlet_temp': self.primary_outlet_temp,
            'secondary_pressure': self.secondary_pressure,
            'secondary_temperature': self.secondary_temperature,
            'water_level': self.water_level,
            'steam_quality': self.steam_quality,
            'steam_void_fraction': self.steam_void_fraction,
            'steam_flow_rate': self.steam_flow_rate,
            'feedwater_flow_rate': self.feedwater_flow_rate,
            'feedwater_temperature': self.feedwater_temperature,
            'heat_transfer_rate': self.heat_transfer_rate,
            'tube_wall_temp': self.tube_wall_temp,
            'overall_htc': self.overall_htc,
            'heat_flux': self.heat_flux
        }
    
    def reset(self) -> None:
        """Reset to initial steady-state conditions"""
        self.primary_inlet_temp = 327.0
        self.primary_outlet_temp = 293.0
        self.secondary_pressure = 6.895
        self.secondary_temperature = 285.8
        self.steam_quality = 0.99  # PWR steam generators produce dry steam
        self.water_level = 12.5
        self.steam_void_fraction = 0.45
        self.steam_flow_rate = 555.0
        self.feedwater_flow_rate = 555.0
        self.feedwater_temperature = 227.0
        self.tube_wall_temp = 310.0
        self.heat_transfer_rate = 1085.0e6
        self.overall_htc = 0.0
        self.heat_flux = 0.0


# Example usage and testing
if __name__ == "__main__":
    # Create steam generator model
    sg = SteamGenerator()
    
    print("Steam Generator Physics Model - Parameter Validation")
    print("=" * 60)
    print("Based on Westinghouse AP1000 Design")
    print()
    
    # Display key parameters and their sources
    config = sg.config
    print("Key Design Parameters:")
    print(f"  Heat Transfer Area: {config.heat_transfer_area:.0f} m² (AP1000: ~5100 m²)")
    print(f"  Tube Count: {config.tube_count} (AP1000 actual)")
    print(f"  Design Power: {config.design_thermal_power/1e6:.0f} MW per SG")
    print(f"  Primary Flow: {config.primary_design_flow:.0f} kg/s per SG")
    print(f"  Secondary Flow: {config.secondary_design_flow:.0f} kg/s per SG")
    print()
    
    # Test steady-state operation
    print("Steady-State Test:")
    result = sg.update_state(
        primary_temp_in=327.0,   # °C (typical PWR hot leg)
        primary_temp_out=293.0,  # °C (typical PWR cold leg)
        primary_flow=5700.0,     # kg/s (design flow)
        steam_flow_out=555.0,    # kg/s (design steam flow)
        feedwater_flow_in=555.0, # kg/s (design feedwater flow)
        feedwater_temp=227.0,    # °C (typical feedwater temp)
        dt=1.0
    )
    
    print("Results:")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
    
    print(f"\nSteam Generator State:")
    state = sg.get_state_dict()
    for key, value in state.items():
        print(f"  {key}: {value:.2f}")
