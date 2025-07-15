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
from typing import Dict, Optional, Tuple, List, Any
from simulator.state import auto_register
from ..component_descriptions import STEAM_GENERATOR_COMPONENT_DESCRIPTIONS
from .tsp_fouling_model import TSPFoulingModel, TSPFoulingConfig
from .tube_interior_fouling import TubeInteriorFouling
from ..water_chemistry import WaterChemistry, WaterChemistryConfig

# Import chemistry flow interfaces
from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies

# Import the new comprehensive config system
from .config import SteamGeneratorConfig

import numpy as np

warnings.filterwarnings("ignore")


@auto_register("SECONDARY", "steam_generator", id_source="config.system_id",
               description=STEAM_GENERATOR_COMPONENT_DESCRIPTIONS['steam_generator'])
class SteamGenerator(ChemistryFlowProvider):
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
    
    def __init__(self, config: Optional[SteamGeneratorConfig] = None, tsp_fouling_config: Optional[TSPFoulingConfig] = None, water_chemistry: Optional[WaterChemistry] = None):
        """Initialize steam generator physics model"""
        self.config = config if config is not None else SteamGeneratorConfig()
        
        # Initialize or use provided unified water chemistry system
        if water_chemistry is not None:
            self.water_chemistry = water_chemistry
        else:
            # Create own instance if not provided (for standalone use)
            self.water_chemistry = WaterChemistry(WaterChemistryConfig())
        
        # Initialize TSP fouling model with unique ID based on generator ID
        if tsp_fouling_config is None:
            tsp_fouling_config = TSPFoulingConfig()
        
        # Set unique TSP fouling ID based on system ID
        tsp_fouling_config.fouling_model_id = f"TSP-{self.config.system_id}"
        
        # Initialize TSP fouling model with unified water chemistry
        self.tsp_fouling = TSPFoulingModel(tsp_fouling_config, self.water_chemistry)
        
        # Initialize tube interior fouling model with unified water chemistry
        self.tube_interior_fouling = TubeInteriorFouling(self.config, self.water_chemistry)
        
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
        design_area = self.config.heat_transfer_area_per_sg  # m² (full design area)
        
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
        r_wall = self.config.tube_wall_thickness / self.config.tube_material_conductivity
        r_secondary = 1.0 / h_secondary
        
        # Overall heat transfer coefficient
        overall_htc = 1.0 / (r_primary + r_wall + r_secondary)
        
        # Apply TSP fouling degradation to heat transfer coefficient
        tsp_degradation_factor = 1.0 - self.tsp_fouling.heat_transfer_degradation
        overall_htc_with_tsp_fouling = overall_htc * tsp_degradation_factor
        
        # Apply tube interior scale thermal resistance
        # Thermal resistance from scale adds to the overall thermal resistance
        scale_thermal_resistance = self.tube_interior_fouling.scale_thermal_resistance
        if scale_thermal_resistance > 0:
            # Add scale resistance to overall thermal resistance
            # 1/U_total = 1/U_clean + R_scale
            clean_resistance = 1.0 / overall_htc_with_tsp_fouling
            total_resistance = clean_resistance + scale_thermal_resistance
            overall_htc_with_all_fouling = 1.0 / total_resistance
        else:
            overall_htc_with_all_fouling = overall_htc_with_tsp_fouling
        
        # Calculate effective heat transfer area based on current water level
        effective_area = self.calculate_effective_heat_transfer_area(self.water_level)
        
        # Heat transfer rate using effective area (level-dependent) and all fouling effects
        heat_transfer_rate = overall_htc_with_all_fouling * effective_area * lmtd
        
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
        
        # SIMPLE APPROACH: Calculate tube wall temperature as secondary temp + thermal resistance effects
        # This ensures scale always increases tube wall temperature (insulation effect)
        
        # Use actual calculated heat flux (no hardcoded values)
        operating_heat_flux = heat_transfer_rate / self.config.heat_transfer_area_per_sg
        operating_heat_flux = max(operating_heat_flux, 5000.0)  # Minimum for low-power operation
        
        # Get fouling thermal resistances from both sides
        r_scale_primary = self.tube_interior_fouling.scale_thermal_resistance  # Primary side scale
        r_scale_secondary = self._calculate_tsp_scale_thermal_resistance()      # Secondary side deposits
        
        # Calculate cumulative thermal resistance from secondary bulk to tube wall center
        r_secondary_to_tube_wall = (
            1.0 / h_secondary +                    # Secondary boundary layer
            r_scale_secondary +                    # TSP deposits (if any)
            (r_wall / 2.0) +                      # Half tube wall thickness
            r_scale_primary                       # Primary scale (the big effect)
        )
        
        # Tube wall temperature = secondary temperature + temperature rise due to thermal resistance
        # This guarantees that more scale resistance = higher tube wall temperature
        self.tube_wall_temp = sat_temp + (operating_heat_flux * r_secondary_to_tube_wall)
        
        # For debugging: calculate the scale contribution specifically
        scale_temperature_contribution = operating_heat_flux * r_scale_primary
        actual_heat_flux = operating_heat_flux  # For compatibility with existing code
        
        # Physical validation - warn if tube wall temperature is extremely high
        if self.tube_wall_temp > 400.0:
            print(f"WARNING: Very high tube wall temperature: {self.tube_wall_temp:.1f}°C - "
                  f"Scale thickness: {self.tube_interior_fouling.scale_thickness:.1f}mm")
        self.overall_htc = overall_htc
        self.heat_flux = actual_heat_flux
        
        details = {
            'overall_htc': overall_htc,
            'lmtd': lmtd,
            'sat_temp_secondary': sat_temp,
            'tube_wall_temp': self.tube_wall_temp,
            'heat_flux': actual_heat_flux,
            'h_primary': h_primary,
            'h_secondary': h_secondary,
            'delta_t1': delta_t1,
            'delta_t2': delta_t2,
            'flow_factor': flow_factor,
            'pressure_factor': pressure_factor,
            # NEW: Both-side fouling thermal details for debugging and monitoring
            'primary_scale_thermal_resistance': r_scale_primary,
            'tsp_scale_thermal_resistance': r_scale_secondary,
            'scale_temperature_contribution': scale_temperature_contribution,
            'total_thermal_resistance_to_tube_wall': r_secondary_to_tube_wall,
            'operating_heat_flux': operating_heat_flux,
            'overall_htc_with_tsp_fouling': overall_htc_with_tsp_fouling,
            'overall_htc_with_all_fouling': overall_htc_with_all_fouling
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
        
        # IMPROVED PRESSURE DYNAMICS - Based on thermal equilibrium and steam generation capability
        # Pressure should stabilize based on heat input and steam generation, not drift linearly
        
        # Calculate equilibrium pressure based on current heat input and steam demand
        design_heat_input = self.config.design_thermal_power_per_sg / 1000.0  # kJ/s
        heat_input_factor = heat_input_kj / design_heat_input if design_heat_input > 0 else 0.0
        
        # Equilibrium pressure scales with heat input capability
        # Higher heat input -> higher equilibrium pressure
        equilibrium_pressure = self.config.design_pressure_secondary * (0.7 + 0.3 * heat_input_factor)
        equilibrium_pressure = np.clip(equilibrium_pressure, 3.0, 8.5)  # Reasonable operating range
        
        # Steam demand effect on equilibrium pressure
        steam_demand_factor = steam_flow_out / self.config.secondary_design_flow if self.config.secondary_design_flow > 0 else 0.0
        demand_pressure_effect = -steam_demand_factor * 0.5  # Higher demand -> lower equilibrium pressure
        equilibrium_pressure += demand_pressure_effect
        equilibrium_pressure = np.clip(equilibrium_pressure, 3.0, 8.5)
        
        # FIXED PRESSURE DYNAMICS - Using proper exponential decay for timestep stability
        # This eliminates oscillations by using mathematically correct first-order system response
        pressure_time_constant = 60.0  # seconds (realistic for steam generator pressure response)
        
        # Calculate base equilibrium pressure approach using exponential decay
        # This is stable for any timestep size, unlike the previous linear method
        decay_factor = np.exp(-dt / pressure_time_constant)
        base_new_pressure = equilibrium_pressure + (self.secondary_pressure - equilibrium_pressure) * decay_factor
        
        # Additional pressure effects for transient conditions (applied as corrections)
        pressure_corrections = 0.0
        
        # 1. Inventory depletion effect (only for severe conditions)
        if feedwater_flow_in < 0.1 and steam_flow_out > 100.0:
            # Rapid pressure drop when steam is extracted without feedwater replacement
            inventory_depletion_rate = -steam_flow_out / self.config.secondary_water_mass  # 1/s
            pressure_drop_correction = inventory_depletion_rate * self.secondary_pressure * 2.0 * dt
            pressure_corrections += pressure_drop_correction
        
        # 2. Steam generation vs demand imbalance (short-term effect)
        steam_supply_factor = steam_generation_rate / self.config.secondary_design_flow if self.config.secondary_design_flow > 0 else 0.0
        supply_demand_imbalance = steam_supply_factor - steam_demand_factor
        imbalance_correction = supply_demand_imbalance * 0.005 * dt  # Small short-term effect
        pressure_corrections += imbalance_correction
        
        # Apply corrections with reasonable limits
        pressure_corrections = np.clip(pressure_corrections, -0.2, 0.2)  # Limit total corrections
        
        # Calculate final pressure with stability margins to prevent boundary oscillations
        new_pressure = base_new_pressure + pressure_corrections
        new_pressure = np.clip(new_pressure, 1.0, 8.0)  # Avoid extreme bounds that cause oscillations
        
        # Calculate pressure change rate for reporting (backwards compatible)
        pressure_change_rate = (new_pressure - self.secondary_pressure) / dt
        
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
        design_heat_flux = self.config.design_thermal_power_per_sg / self.config.heat_transfer_area_per_sg
        current_heat_flux = heat_input / self.config.heat_transfer_area_per_sg
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
    
    def _apply_tsp_flow_restrictions(self, requested_steam_flow: float, requested_feedwater_flow: float) -> Tuple[float, float, float]:
        """
        Apply TSP fouling flow restrictions to requested flow rates
        
        Physical Basis:
        - TSP fouling reduces effective flow area
        - Flow capacity ∝ 1/√(pressure_drop_ratio) 
        - Cannot exceed physical flow limits imposed by fouled TSPs
        
        Args:
            requested_steam_flow: Requested steam flow rate (kg/s)
            requested_feedwater_flow: Requested feedwater flow rate (kg/s)
            
        Returns:
            Tuple of (actual_steam_flow, actual_feedwater_flow, flow_restriction_factor)
        """
        # Core physics: TSP fouling creates flow restriction
        # Flow capacity ∝ 1/√(pressure_drop_ratio)
        flow_capacity_factor = 1.0 / np.sqrt(self.tsp_fouling.pressure_drop_ratio)
        
        # Calculate max achievable flows for this individual SG
        max_steam_flow = self.config.design_steam_flow_per_sg * flow_capacity_factor
        max_feedwater_flow = self.config.design_feedwater_flow_per_sg * flow_capacity_factor
        
        # Physical reality: can't exceed what TSPs allow
        actual_steam_flow = min(requested_steam_flow, max_steam_flow)
        actual_feedwater_flow = min(requested_feedwater_flow, max_feedwater_flow)
        
        # Track the restriction for reporting
        flow_restriction_factor = actual_steam_flow / requested_steam_flow if requested_steam_flow > 0 else 1.0
        
        return actual_steam_flow, actual_feedwater_flow, flow_restriction_factor

    def _calculate_primary_flow_restriction(self, requested_primary_flow: float) -> Tuple[float, float]:
        """
        Calculate primary flow restriction due to tube interior scale buildup
        
        Physical Basis:
        - Scale buildup reduces effective tube inner diameter
        - Flow area ∝ diameter²
        - Pressure drop ∝ 1/diameter⁴ (Poiseuille flow)
        - Flow capacity limited by increased pressure drop
        
        Args:
            requested_primary_flow: Requested primary flow rate (kg/s)
            
        Returns:
            Tuple of (actual_primary_flow, primary_flow_restriction_factor)
        """
        # Calculate effective tube diameter reduction due to scale
        scale_thickness_m = self.tube_interior_fouling.scale_thickness / 1000.0  # Convert mm to m
        clean_diameter = self.config.tube_inner_diameter  # m
        
        # Effective diameter after scale buildup (scale on tube walls)
        effective_diameter = clean_diameter - 2.0 * scale_thickness_m
        effective_diameter = max(effective_diameter, clean_diameter * 0.5)  # Minimum 50% of original diameter
        
        # Flow area reduction
        clean_area = np.pi * (clean_diameter / 2.0) ** 2
        effective_area = np.pi * (effective_diameter / 2.0) ** 2
        area_ratio = effective_area / clean_area
        
        # Pressure drop ratio using Poiseuille flow relationship
        # ΔP ∝ 1/D⁴ for laminar flow, ∝ 1/D⁵ for turbulent flow
        # Use D⁴ relationship as conservative estimate
        diameter_ratio = effective_diameter / clean_diameter
        pressure_drop_ratio = 1.0 / (diameter_ratio ** 4)
        
        # Flow capacity factor (flow limited by pressure drop capability)
        # Assume pumps can handle up to 3x normal pressure drop
        max_pressure_ratio = 3.0
        if pressure_drop_ratio <= max_pressure_ratio:
            # Flow capacity limited by area reduction only
            flow_capacity_factor = area_ratio
        else:
            # Flow capacity limited by pump pressure capability
            flow_capacity_factor = area_ratio * (max_pressure_ratio / pressure_drop_ratio) ** 0.5
        
        # Calculate actual achievable primary flow
        max_primary_flow = self.config.primary_design_flow * flow_capacity_factor
        actual_primary_flow = min(requested_primary_flow, max_primary_flow)
        
        # Calculate restriction factor for reporting
        primary_flow_restriction_factor = actual_primary_flow / requested_primary_flow if requested_primary_flow > 0 else 1.0
        
        return actual_primary_flow, primary_flow_restriction_factor

    def _calculate_tsp_scale_thermal_resistance(self) -> float:
        """
        Calculate thermal resistance from TSP fouling deposits on tube exterior
        
        Physical Basis:
        - TSP fouling creates deposits in the crevices and on tube surfaces that
          add thermal resistance on the secondary side
        - Deposits have low thermal conductivity compared to metal tubes
        - Partial coverage based on fouling fraction
        
        Returns:
            Thermal resistance from TSP deposits (m²K/W)
        """
        # Get TSP fouling state
        tsp_fouling_fraction = self.tsp_fouling.fouling_fraction
        avg_deposit_thickness = self.tsp_fouling.deposits.get_average_thickness()  # mm
        
        # Convert to thermal resistance
        if avg_deposit_thickness > 0:
            # TSP deposits have realistic thermal conductivity for mixed deposits
            # Magnetite: ~5 W/m/K, Copper oxide: ~20 W/m/K, Silica: ~1.4 W/m/K
            # Mixed TSP deposits typically have conductivity around 2-5 W/m/K
            tsp_deposit_conductivity = 3.0  # W/m/K (realistic for mixed TSP deposits)
            thickness_m = avg_deposit_thickness / 1000.0  # Convert mm to m
            
            # Thermal resistance from TSP deposits
            # Note: This is partial coverage, so scale by fouling fraction
            r_tsp = (thickness_m / tsp_deposit_conductivity) * tsp_fouling_fraction
            
            return r_tsp
        else:
            return 0.0

    def _calculate_pump_energy_consumption(self) -> Dict[str, float]:
        """
        Calculate pump energy consumption based on TSP fouling pressure drop
        
        Physical Basis:
        - Pump power ∝ pressure_drop_ratio (more pressure = more energy)
        - Additional energy needed to overcome TSP fouling resistance
        - Real plants increase pump speed/pressure to maintain flow
        
        Returns:
            Dictionary with pump energy breakdown
        """
        # Base pump energy for clean conditions (typical feedwater pump)
        base_pump_power_mw = 5.0  # MW per SG
        
        # Additional energy needed to overcome TSP fouling pressure drop
        # Pump power ∝ pressure_drop_ratio (more pressure = more energy)
        pressure_penalty_factor = (self.tsp_fouling.pressure_drop_ratio - 1.0)
        fouling_energy_penalty_mw = base_pump_power_mw * pressure_penalty_factor * 0.5  # 50% efficiency
        
        total_pump_power_mw = base_pump_power_mw + fouling_energy_penalty_mw
        
        return {
            'base_pump_power_mw': base_pump_power_mw,
            'fouling_energy_penalty_mw': fouling_energy_penalty_mw,
            'total_pump_power_mw': total_pump_power_mw
        }

    def update_state(self,
                    primary_temp_in: float,
                    primary_temp_out: float,
                    primary_flow: float,
                    steam_flow_out: float,
                    feedwater_flow_in: float,
                    feedwater_temp: float,
                    dt: float,
                    system_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
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
        
        # Update secondary temperature (saturation temperature at current pressure)
        self.secondary_temperature = self._saturation_temperature(self.secondary_pressure)
        
        # Update unified water chemistry system if conditions provided
        if system_conditions is not None and 'water_chemistry_update' in system_conditions:
            self.water_chemistry.update_chemistry(
                system_conditions['water_chemistry_update'],
                dt / 60.0  # Convert minutes to hours
            )
        
        # Calculate average flow velocity in steam generator
        # Simplified calculation based on tube bundle geometry
        tube_cross_section = np.pi * (self.config.tube_inner_diameter / 2.0) ** 2
        total_flow_area = self.config.tube_count_per_sg * tube_cross_section
        avg_velocity = primary_flow / (1000.0 * total_flow_area)  # m/s (assuming water density ~1000 kg/m³)
        
        # Update TSP fouling state using unified water chemistry
        # Note: dt is passed in seconds from the simulation system
        tsp_result = self.tsp_fouling.update_fouling_state(
            temperature=self.secondary_temperature,
            flow_velocity=avg_velocity,
            dt_hours=dt / 3600.0  # Convert seconds to hours
        )
        
        # Update tube interior fouling state using primary side conditions
        primary_conditions = {
            'temperature': (primary_temp_in + primary_temp_out) / 2.0,  # Average primary temperature
            'flow_velocity': avg_velocity,  # Same velocity calculation
            'chemistry': {
                'boric_acid_concentration': 1000.0,  # Typical PWR primary chemistry
                'lithium_concentration': 2.0,
                'primary_ph': 7.2,
                'dissolved_oxygen': 0.005
            }
        }
        
        tube_interior_result = self.tube_interior_fouling.update_fouling_state(
            primary_conditions, dt  # dt is already in seconds
        )
        
        # PHASE 1: Apply TSP flow restrictions AFTER TSP fouling update
        # This ensures we use the current fouling state for flow restrictions
        actual_steam_flow, actual_feedwater_flow, flow_restriction_factor = self._apply_tsp_flow_restrictions(
            steam_flow_out, feedwater_flow_in
        )
        
        # NEW: Apply primary flow restriction due to tube interior scale buildup
        actual_primary_flow, primary_flow_restriction_factor = self._calculate_primary_flow_restriction(primary_flow)
        
        # PHASE 2: Calculate pump energy consumption based on current TSP fouling
        pump_energy = self._calculate_pump_energy_consumption()
        
        # Calculate secondary side dynamics using ACTUAL flows (after fouling restrictions)
        secondary_dynamics = self.calculate_secondary_side_dynamics(
            heat_transfer, actual_steam_flow, actual_feedwater_flow, feedwater_temp, dt
        )
        
        # Update state variables
        self.primary_inlet_temp = primary_temp_in
        self.primary_outlet_temp = primary_temp_out
        self.secondary_pressure = secondary_dynamics['new_pressure']
        self.water_level = secondary_dynamics['new_water_level']
        self.steam_quality = secondary_dynamics['new_steam_quality']
        self.steam_void_fraction = secondary_dynamics['new_void_fraction']
        self.steam_flow_rate = actual_steam_flow  # Use actual flow (after fouling restrictions)
        self.feedwater_flow_rate = actual_feedwater_flow  # Use actual flow (after fouling restrictions)
        self.feedwater_temperature = feedwater_temp
        self.heat_transfer_rate = heat_transfer
        
        # Calculate performance metrics
        thermal_efficiency = heat_transfer / self.config.design_thermal_power_per_sg
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
            
            # PHASE 1: Flow restriction results
            'requested_steam_flow': steam_flow_out,
            'actual_steam_flow': actual_steam_flow,
            'requested_feedwater_flow': feedwater_flow_in,
            'actual_feedwater_flow': actual_feedwater_flow,
            'flow_restriction_factor': flow_restriction_factor,
            
            # NEW: Primary flow restriction results
            'requested_primary_flow': primary_flow,
            'actual_primary_flow': actual_primary_flow,
            'primary_flow_restriction_factor': primary_flow_restriction_factor,
            
            # PHASE 2: Pump energy results
            'base_pump_power_mw': pump_energy['base_pump_power_mw'],
            'fouling_energy_penalty_mw': pump_energy['fouling_energy_penalty_mw'],
            'total_pump_power_mw': pump_energy['total_pump_power_mw'],
            'net_thermal_efficiency': (heat_transfer - pump_energy['total_pump_power_mw'] * 1e6) / self.config.design_thermal_power_per_sg if self.config.design_thermal_power_per_sg > 0 else 0.0,
            
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
            'pressure_factor': ht_details['pressure_factor'],
            
            # TSP fouling results
            'tsp_fouling_fraction': tsp_result['fouling_fraction'],
            'tsp_fouling_stage': tsp_result['fouling_stage'],
            'tsp_heat_transfer_degradation': tsp_result['heat_transfer_degradation'],
            'tsp_pressure_drop_ratio': tsp_result['pressure_drop_ratio'],
            'tsp_operating_years': tsp_result['operating_years'],
            'tsp_shutdown_required': tsp_result['shutdown_required'],
            'tsp_replacement_recommended': tsp_result['replacement_recommended'],
            'tsp_cleaning_cycles': tsp_result['cleaning_cycles'],
            
            # Tube interior fouling results (NEW)
            'tube_scale_thickness_mm': tube_interior_result['scale_thickness_mm'],
            'tube_scale_thermal_resistance': tube_interior_result['scale_thermal_resistance'],
            'tube_scale_formation_rate_mm_per_year': tube_interior_result['scale_formation_rate_mm_per_year'],
            'tube_thermal_efficiency_loss': tube_interior_result['thermal_efficiency_loss'],
            'tube_fouling_fraction': tube_interior_result['fouling_fraction'],
            'tube_operating_years': tube_interior_result['operating_years'],
            'tube_replacement_recommended': tube_interior_result['replacement_recommended']
        }
    
    # Thermodynamic property correlations
    # These are simplified correlations valid for PWR operating conditions
    # For production use, would use NIST REFPROP or similar
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """
        Calculate saturation temperature for given pressure
        
        Using accurate correlation for water, valid 0.1-10 MPa
        Reference: NIST steam tables, simplified polynomial fit
        """
        if pressure_mpa <= 0.001:
            return 10.0  # Very low pressure
        
        # CORRECTED: Use accurate polynomial fit for water saturation temperature
        # Based on NIST data, valid for 0.1-10 MPa
        # For 6.895 MPa, should give ~285°C
        
        # Convert pressure to bar for calculation
        pressure_bar = pressure_mpa * 10.0
        
        # Polynomial fit to NIST saturation data (0.1-10 MPa range)
        # T_sat = a0 + a1*ln(P) + a2*ln(P)^2 + a3*ln(P)^3
        # Where P is in bar, T is in °C
        a0 = 42.6776
        a1 = 34.5194
        a2 = 2.8896
        a3 = 0.1153
        
        if pressure_bar > 0:
            ln_p = np.log(pressure_bar)
            temp_c = a0 + a1*ln_p + a2*ln_p**2 + a3*ln_p**3
        else:
            temp_c = 10.0
        
        # Validate result - for 6.895 MPa (68.95 bar), should give ~285°C
        temp_c = np.clip(temp_c, 10.0, 374.0)  # Physical limits for water
        
        return temp_c
    
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
        # Calculate pump energy for state reporting
        pump_energy = self._calculate_pump_energy_consumption()
        
        # Calculate current flow restrictions for state reporting
        design_primary_flow = self.config.primary_design_flow
        design_steam_flow = self.config.design_steam_flow_per_sg
        design_feedwater_flow = self.config.design_feedwater_flow_per_sg
        
        # Primary flow restriction from scale buildup
        actual_primary_flow, primary_flow_restriction_factor = self._calculate_primary_flow_restriction(design_primary_flow)
        
        # Secondary flow restriction from TSP fouling
        actual_steam_flow, actual_feedwater_flow, secondary_flow_restriction_factor = self._apply_tsp_flow_restrictions(design_steam_flow, design_feedwater_flow)
        
        state_dict = {
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
            'tube_wall_temperature': self.tube_wall_temp,
            'overall_htc': self.overall_htc,
            'heat_flux': self.heat_flux,
            
            # Flow restriction state (NEW)
            'primary_flow_restriction_factor': primary_flow_restriction_factor,
            'secondary_flow_restriction_factor': secondary_flow_restriction_factor,
            'max_primary_flow_capacity': actual_primary_flow,
            'max_steam_flow_capacity': actual_steam_flow,
            'max_feedwater_flow_capacity': actual_feedwater_flow,
            
            # PHASE 2: Pump energy state
            'base_pump_power_mw': pump_energy['base_pump_power_mw'],
            'fouling_energy_penalty_mw': pump_energy['fouling_energy_penalty_mw'],
            'total_pump_power_mw': pump_energy['total_pump_power_mw']
        }
        
        # Add TSP fouling state if available
        if hasattr(self, 'tsp_fouling'):
            tsp_state = self.tsp_fouling.get_state_dict()
            state_dict.update({
                'tsp_fouling_fraction': tsp_state['tsp_fouling_fraction'],
                'tsp_heat_transfer_degradation': tsp_state['tsp_heat_transfer_degradation'],
                'tsp_pressure_drop_ratio': tsp_state['tsp_pressure_drop_ratio'],
                'tsp_fouling_stage_numeric': tsp_state['tsp_fouling_stage_numeric'],
                'tsp_operating_years': tsp_state['tsp_operating_years'],
                'tsp_shutdown_required': tsp_state['tsp_shutdown_required'],
                'tsp_replacement_recommended': tsp_state['tsp_replacement_recommended'],
                'tsp_cleaning_cycles': tsp_state['tsp_cleaning_cycles'],
                'tsp_years_since_cleaning': tsp_state['tsp_years_since_cleaning'],
                'tsp_average_deposit_thickness': tsp_state['tsp_average_deposit_thickness'],
                'tsp_maximum_deposit_thickness': tsp_state['tsp_maximum_deposit_thickness']
            })
        
        # Add tube interior fouling state if available
        if hasattr(self, 'tube_interior_fouling'):
            tube_state = self.tube_interior_fouling.get_state_dict()
            # Add tube interior specific state variables
            for key, value in tube_state.items():
                if key.startswith('tube_'):
                    state_dict[key] = value
        
        return state_dict
    
    def perform_tsp_cleaning(self, cleaning_type: str = "chemical") -> Dict[str, float]:
        """
        Perform TSP cleaning operation
        
        Args:
            cleaning_type: Type of cleaning ("chemical" or "mechanical")
            
        Returns:
            Dictionary with cleaning results
        """
        return self.tsp_fouling.perform_cleaning(cleaning_type)
    
    def check_shutdown_required(self) -> Tuple[bool, List[str]]:
        """
        Check if steam generator shutdown is required due to TSP fouling
        
        Returns:
            Tuple of (shutdown_required, shutdown_reasons)
        """
        shutdown_required, shutdown_reasons = self.tsp_fouling.evaluate_shutdown_conditions()
        return shutdown_required, [reason.value for reason in shutdown_reasons]
    
    def get_tsp_state(self) -> Dict[str, float]:
        """Get current TSP fouling state"""
        return self.tsp_fouling.get_state_dict()
    
    def setup_maintenance_integration(self, maintenance_system, component_id: str):
        """
        Set up maintenance integration for individual steam generator
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
            component_id: Unique identifier for this steam generator
        """
        print(f"STEAM GENERATOR {component_id}: Setting up maintenance integration")
        
        # Define monitoring configuration for steam generator parameters
        monitoring_config = {
            'tsp_fouling_fraction': {
                'attribute': 'tsp_fouling.fouling_fraction',
                'threshold': 0.15,  # 15% fouling triggers cleaning
                'comparison': 'greater_than',
                'action': 'tsp_chemical_cleaning',
                'cooldown_hours': 168.0  # Weekly cooldown
            },
            'heat_transfer_degradation': {
                'attribute': 'tsp_fouling.heat_transfer_degradation',
                'threshold': 0.10,  # 10% degradation triggers maintenance
                'comparison': 'greater_than',
                'action': 'tube_bundle_inspection',
                'cooldown_hours': 72.0  # 3-day cooldown
            },
            'steam_quality': {
                'attribute': 'steam_quality',
                'threshold': 0.99,  # Below 99% quality
                'comparison': 'less_than',
                'action': 'moisture_separator_maintenance',
                'cooldown_hours': 48.0  # 2-day cooldown
            },
            'tube_wall_temperature': {
                'attribute': 'tube_wall_temp',
                'threshold': 350.0,  # High tube wall temperature
                'comparison': 'greater_than',
                'action': 'scale_removal',
                'cooldown_hours': 24.0  # Daily cooldown
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
        Perform maintenance operations on steam generator
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        from systems.maintenance.maintenance_actions import MaintenanceResult
        
        if maintenance_type == "tsp_chemical_cleaning":
            # Perform TSP chemical cleaning
            cleaning_result = self.tsp_fouling.perform_cleaning("chemical")
            
            # Calculate performance improvement
            fouling_reduction = cleaning_result.get('fouling_reduction', 0.0)
            performance_improvement = fouling_reduction * 100.0  # Convert to percentage
            
            return {
                'success': True,
                'duration_hours': 12.0,
                'work_performed': 'TSP chemical cleaning completed',
                'findings': f"Removed {fouling_reduction:.1%} of TSP fouling deposits",
                'performance_improvement': performance_improvement,
                'effectiveness_score': min(1.0, fouling_reduction * 2.0),  # Scale to 0-1
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Chemical cleaning solution', 'Cleaning equipment']
            }
        
        elif maintenance_type == "tsp_mechanical_cleaning":
            # Perform TSP mechanical cleaning
            cleaning_result = self.tsp_fouling.perform_cleaning("mechanical")
            
            fouling_reduction = cleaning_result.get('fouling_reduction', 0.0)
            performance_improvement = fouling_reduction * 100.0
            
            return {
                'success': True,
                'duration_hours': 16.0,
                'work_performed': 'TSP mechanical cleaning completed',
                'findings': f"Mechanically removed {fouling_reduction:.1%} of TSP fouling",
                'performance_improvement': performance_improvement,
                'effectiveness_score': min(1.0, fouling_reduction * 1.5),
                'next_maintenance_due': 17520.0,  # Every 2 years
                'parts_used': ['Mechanical cleaning tools', 'Replacement brushes']
            }
        
        elif maintenance_type == "tube_bundle_inspection":
            # Perform tube bundle inspection
            current_degradation = self.tsp_fouling.heat_transfer_degradation
            
            # Inspection provides information but doesn't restore performance
            findings = f"Heat transfer degradation: {current_degradation:.1%}"
            recommendations = []
            
            if current_degradation > 0.15:
                recommendations.append("Schedule TSP cleaning within 30 days")
            if current_degradation > 0.20:
                recommendations.append("Consider mechanical cleaning for severe fouling")
            if self.steam_quality < 0.98:
                recommendations.append("Inspect moisture separator equipment")
            
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': 'Comprehensive tube bundle inspection',
                'findings': findings,
                'recommendations': recommendations,
                'effectiveness_score': 1.0,  # Inspection always successful
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Inspection equipment', 'Documentation materials']
            }
        
        elif maintenance_type == "moisture_separator_maintenance":
            # Perform moisture separator maintenance
            current_quality = self.steam_quality
            
            # Restore steam quality to design value
            quality_improvement = 0.999 - current_quality
            self.steam_quality = min(0.999, current_quality + quality_improvement * 0.8)
            
            return {
                'success': True,
                'duration_hours': 6.0,
                'work_performed': 'Moisture separator maintenance completed',
                'findings': f"Improved steam quality from {current_quality:.3f} to {self.steam_quality:.3f}",
                'performance_improvement': quality_improvement * 100.0,
                'effectiveness_score': 0.9,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Separator elements', 'Gaskets', 'Cleaning materials']
            }
        
        elif maintenance_type == "scale_removal":
            # Delegate to tube interior fouling model for proper physics-based scale removal
            result = self.tube_interior_fouling.perform_maintenance('primary_scale_cleaning', **kwargs)
            
            # Update tube wall temperature based on actual scale removal
            if result.get('success', False):
                scale_removed = result.get('scale_removed_mm', 0.0)
                if scale_removed > 0:
                    # The tube wall temperature will be automatically recalculated in the next
                    # heat transfer calculation based on the reduced scale thermal resistance
                    print(f"STEAM GENERATOR MAINTENANCE: Scale removal completed - {scale_removed:.3f}mm removed")
                    print(f"  New scale thickness: {self.tube_interior_fouling.scale_thickness:.3f}mm")
                    print(f"  New thermal resistance: {self.tube_interior_fouling.scale_thermal_resistance:.6f} m²K/W")
            
            return result
        
        elif maintenance_type == "water_chemistry_adjustment":
            # Perform water chemistry adjustment
            # Reset water chemistry to optimal conditions
            self.water_chemistry.reset()
            
            return {
                'success': True,
                'duration_hours': 2.0,
                'work_performed': 'Water chemistry adjustment completed',
                'findings': 'Restored optimal water chemistry parameters',
                'effectiveness_score': 0.95,
                'next_maintenance_due': 720.0,  # Monthly
                'parts_used': ['Chemical additives', 'pH adjustment chemicals']
            }
        
        elif maintenance_type == "eddy_current_testing":
            # Perform eddy current testing
            tsp_state = self.tsp_fouling.get_state_dict()
            
            findings = f"Tube integrity assessment completed. "
            findings += f"TSP fouling level: {tsp_state['fouling_fraction']:.1%}, "
            findings += f"Operating years: {tsp_state['operating_years']:.1f}"
            
            recommendations = []
            if tsp_state['fouling_fraction'] > 0.20:
                recommendations.append("Schedule immediate TSP cleaning")
            if tsp_state['operating_years'] > 15:
                recommendations.append("Consider tube replacement program")
            
            return {
                'success': True,
                'duration_hours': 24.0,
                'work_performed': 'Eddy current testing of all tubes',
                'findings': findings,
                'recommendations': recommendations,
                'effectiveness_score': 1.0,
                'next_maintenance_due': 8760.0,  # Annual
                'parts_used': ['Eddy current probes', 'Data recording equipment']
            }
        
        elif maintenance_type == "secondary_side_cleaning":
            # Perform general secondary side cleaning
            # Partial restoration of performance
            current_degradation = self.tsp_fouling.heat_transfer_degradation
            
            # Cleaning provides moderate improvement
            improvement_factor = 0.3  # 30% of fouling removed
            self.tsp_fouling.fouling_fraction *= (1.0 - improvement_factor)
            
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': 'Secondary side cleaning completed',
                'findings': f"Reduced heat transfer degradation by {improvement_factor:.1%}",
                'performance_improvement': current_degradation * improvement_factor * 100.0,
                'effectiveness_score': 0.7,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Cleaning chemicals', 'Brushes', 'Rinse water']
            }
        
        elif maintenance_type == "tsp_inspection":
            # Perform TSP inspection via TSP fouling model
            result = self.tsp_fouling.perform_maintenance('tsp_inspection', **kwargs)
            return result
        
        elif maintenance_type == "tsp_flow_test":
            # Perform TSP flow test via TSP fouling model
            result = self.tsp_fouling.perform_maintenance('tsp_flow_test', **kwargs)
            return result
        
        elif maintenance_type == "tube_interior_inspection":
            # Perform tube interior inspection via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('tube_interior_inspection', **kwargs)
            return result
        
        elif maintenance_type == "tube_interior_scale_cleaning":
            # Perform tube interior scale cleaning via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('primary_scale_cleaning', **kwargs)
            return result
        
        elif maintenance_type == "tube_interior_eddy_current_testing":
            # Perform tube interior eddy current testing via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('tube_eddy_current_testing', **kwargs)
            return result
        
        elif maintenance_type == "primary_chemistry_optimization":
            # Perform primary chemistry optimization via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('primary_chemistry_optimization', **kwargs)
            return result
        
        elif maintenance_type == "primary_scale_cleaning":
            # Perform primary side scale cleaning via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('primary_scale_cleaning', **kwargs)
            return result
        
        elif maintenance_type == "tube_eddy_current_testing":
            # Perform tube eddy current testing via tube interior fouling model
            result = self.tube_interior_fouling.perform_maintenance('tube_eddy_current_testing', **kwargs)
            return result
        
        elif maintenance_type == "routine_maintenance":
            # Perform routine maintenance
            # Minor performance restoration
            self.steam_quality = min(0.999, self.steam_quality + 0.001)
            
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'Routine steam generator maintenance',
                'findings': 'General maintenance activities completed',
                'effectiveness_score': 0.8,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['General maintenance supplies']
            }
        
        else:
            # Unknown maintenance type
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f'Unknown maintenance type: {maintenance_type}',
                'error_message': f'Maintenance type {maintenance_type} not supported',
                'effectiveness_score': 0.0
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
        
        # Reset TSP fouling model
        self.tsp_fouling.reset()
    
    # === CHEMISTRY FLOW PROVIDER INTERFACE METHODS ===
    # These methods enable integration with chemistry_flow_tracker
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data from steam generator perspective
        """
        # Steam generator affects chemistry through steam carryover and blowdown
        return {
            'steam_generator_flows': {
                ChemicalSpecies.PH.value: self.water_chemistry.ph,
                ChemicalSpecies.IRON.value: self.water_chemistry.iron_concentration,
                ChemicalSpecies.COPPER.value: self.water_chemistry.copper_concentration,
                ChemicalSpecies.SILICA.value: self.water_chemistry.silica_concentration,
                'steam_carryover_rate': self._calculate_steam_carryover_rate(),
                'blowdown_chemistry_removal': self._calculate_blowdown_removal_rate()
            },
            'steam_quality_effects': {
                'moisture_carryover': (1.0 - self.steam_quality) * self.steam_flow_rate,
                'steam_purity': self.steam_quality,
                'separator_efficiency': self._calculate_separator_efficiency(),
                'heat_transfer_chemistry_impact': self.tsp_fouling.heat_transfer_degradation
            },
            'tube_chemistry_effects': {
                'tube_wall_temperature': self.tube_wall_temp,
                'corrosion_rate': self._calculate_tube_corrosion_rate(),
                'scale_formation_rate': self._calculate_scale_formation_rate(),
                'chemistry_induced_stress': self._calculate_chemistry_stress_factor()
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state from steam generator perspective
        
        Returns:
            Dictionary with steam generator chemistry state
        """
        return {
            'steam_generator_secondary_pressure': self.secondary_pressure,
            'steam_generator_secondary_temperature': self.secondary_temperature,
            'steam_generator_water_level': self.water_level,
            'steam_generator_steam_quality': self.steam_quality,
            'steam_generator_heat_transfer_rate': self.heat_transfer_rate,
            'steam_generator_tube_wall_temp': self.tube_wall_temp,
            'steam_generator_steam_flow_rate': self.steam_flow_rate,
            'steam_generator_feedwater_flow_rate': self.feedwater_flow_rate,
            'steam_generator_feedwater_temperature': self.feedwater_temperature,
            'steam_generator_tsp_fouling_fraction': self.tsp_fouling.fouling_fraction,
            'steam_generator_chemistry_impact_factor': self._calculate_chemistry_impact_factor()
        }
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update steam generator based on external chemistry effects
        
        This method allows the chemistry flow tracker to influence steam generator
        performance based on system-wide chemistry changes.
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Update water chemistry system with external effects
        if 'water_chemistry_effects' in chemistry_state:
            self.water_chemistry.update_chemistry_effects(chemistry_state['water_chemistry_effects'])
        
        # Update TSP fouling with chemistry effects
        if 'tsp_fouling_effects' in chemistry_state:
            self.tsp_fouling.update_chemistry_effects(chemistry_state['tsp_fouling_effects'])
        
        # Apply pH control effects to steam generator operation
        if 'ph_control_effects' in chemistry_state:
            ph_effects = chemistry_state['ph_control_effects']
            
            # pH control can affect steam quality through chemistry changes
            if 'ph_stability' in ph_effects:
                stability = ph_effects['ph_stability']
                if stability > 0.9:  # Very stable pH
                    # Stable pH improves steam quality by reducing carryover
                    quality_improvement = (stability - 0.9) * 0.01  # Up to 1% improvement
                    target_quality = min(0.999, self.steam_quality + quality_improvement)
                    
                    # Gradual improvement
                    self.steam_quality += (target_quality - self.steam_quality) * 0.1
            
            # Chemical dosing effects on steam generator chemistry
            if 'chemical_dosing_rate' in ph_effects:
                dosing_rate = ph_effects['chemical_dosing_rate']
                if dosing_rate > 0:
                    # Chemical dosing can affect secondary side chemistry
                    # Update water chemistry with dosing effects
                    dosing_effects = {
                        'chemical_additions': {
                            ChemicalSpecies.AMMONIA.value: dosing_rate * 0.1,  # Simplified
                            ChemicalSpecies.MORPHOLINE.value: dosing_rate * 0.05
                        }
                    }
                    self.water_chemistry.update_chemistry_effects(dosing_effects)
        
        # Apply feedwater chemistry effects
        if 'feedwater_chemistry_effects' in chemistry_state:
            fw_effects = chemistry_state['feedwater_chemistry_effects']
            
            # Feedwater chemistry affects steam generator performance
            if 'iron_concentration' in fw_effects:
                iron_level = fw_effects['iron_concentration']
                if iron_level > 0.2:  # High iron concentration
                    # High iron can affect heat transfer through fouling
                    fouling_increase = (iron_level - 0.2) * 0.01
                    # Apply to TSP fouling model
                    tsp_effects = {'iron_fouling_acceleration': fouling_increase}
                    self.tsp_fouling.update_chemistry_effects(tsp_effects)
            
            # Oxygen effects on corrosion
            if 'dissolved_oxygen' in fw_effects:
                oxygen_level = fw_effects['dissolved_oxygen']
                if oxygen_level > 0.01:  # High oxygen
                    # Accelerated corrosion at high oxygen levels
                    corrosion_factor = 1.0 + (oxygen_level - 0.01) * 10.0
                    # This would affect tube integrity over time
                    # For now, just track the effect
                    self._oxygen_corrosion_factor = corrosion_factor
        
        # Apply system-wide chemistry balance effects
        if 'system_chemistry_balance' in chemistry_state:
            balance = chemistry_state['system_chemistry_balance']
            
            # Poor chemistry balance can affect steam generator efficiency
            if 'balance_error' in balance:
                error = abs(balance['balance_error'])
                if error > 5.0:  # More than 5% error
                    # Reduce heat transfer efficiency due to chemistry imbalance
                    efficiency_penalty = min(0.05, error * 0.001)  # Up to 5% penalty
                    # Apply penalty to heat transfer coefficient
                    if hasattr(self, '_chemistry_efficiency_penalty'):
                        self._chemistry_efficiency_penalty = efficiency_penalty
                    else:
                        self._chemistry_efficiency_penalty = 0.0
    
    def _calculate_steam_carryover_rate(self) -> float:
        """Calculate rate of chemical carryover in steam"""
        # Steam carryover depends on steam quality and flow rate
        moisture_fraction = 1.0 - self.steam_quality
        carryover_rate = moisture_fraction * self.steam_flow_rate * 0.001  # kg/s of chemicals
        return carryover_rate
    
    def _calculate_blowdown_removal_rate(self) -> float:
        """Calculate rate of chemistry removal through blowdown"""
        # Simplified blowdown calculation
        blowdown_rate = self.feedwater_flow_rate * 0.02  # 2% blowdown rate
        chemistry_concentration = (self.water_chemistry.iron_concentration + 
                                 self.water_chemistry.copper_concentration) / 1000.0  # kg/kg
        removal_rate = blowdown_rate * chemistry_concentration  # kg/s
        return removal_rate
    
    def _calculate_separator_efficiency(self) -> float:
        """Calculate moisture separator efficiency"""
        # Efficiency depends on water level and flow conditions
        level_factor = min(1.0, self.water_level / 12.5)  # Normalized to normal level
        flow_factor = min(1.0, self.config.secondary_design_flow / self.steam_flow_rate)
        efficiency = 0.95 * level_factor * flow_factor  # Base 95% efficiency
        return max(0.8, efficiency)  # Minimum 80% efficiency
    
    def _calculate_tube_corrosion_rate(self) -> float:
        """Calculate tube corrosion rate based on chemistry"""
        # Corrosion rate depends on temperature, pH, and oxygen
        temp_factor = (self.tube_wall_temp - 250.0) / 100.0  # Normalized temperature effect
        ph_factor = abs(self.water_chemistry.ph - 9.2) * 0.1  # pH deviation effect
        oxygen_factor = self.water_chemistry.dissolved_oxygen * 100.0  # Oxygen effect
        
        base_corrosion_rate = 0.001  # mm/year base rate
        corrosion_rate = base_corrosion_rate * (1.0 + temp_factor + ph_factor + oxygen_factor)
        return max(0.0, corrosion_rate)
    
    def _calculate_scale_formation_rate(self) -> float:
        """Calculate scale formation rate on tubes"""
        # Scale formation depends on hardness, temperature, and pH
        hardness_factor = self.water_chemistry.hardness / 150.0  # Normalized hardness
        temp_factor = (self.tube_wall_temp - 200.0) / 100.0  # Temperature effect
        ph_factor = max(0.0, self.water_chemistry.ph - 8.0) * 0.2  # High pH promotes scaling
        
        base_scale_rate = 0.01  # mm/year base rate
        scale_rate = base_scale_rate * hardness_factor * (1.0 + temp_factor + ph_factor)
        return max(0.0, scale_rate)
    
    def _calculate_chemistry_stress_factor(self) -> float:
        """Calculate chemistry-induced stress factor on tubes"""
        # Chemistry can cause stress through corrosion and thermal effects
        corrosion_stress = self._calculate_tube_corrosion_rate() * 10.0
        thermal_stress = abs(self.tube_wall_temp - 300.0) / 100.0  # Deviation from nominal
        chemistry_stress = (corrosion_stress + thermal_stress) * 0.1
        return min(1.0, chemistry_stress)  # Normalized stress factor
    
    def _calculate_chemistry_impact_factor(self) -> float:
        """Calculate overall chemistry impact factor for steam generator"""
        # Combine various chemistry effects
        tsp_impact = self.tsp_fouling.heat_transfer_degradation
        corrosion_impact = self._calculate_tube_corrosion_rate() * 0.1
        scale_impact = self._calculate_scale_formation_rate() * 0.05
        
        # Overall impact (higher is worse)
        total_impact = tsp_impact + corrosion_impact + scale_impact
        
        # Convert to impact factor (lower is worse performance)
        impact_factor = max(0.5, 1.0 - total_impact)
        return impact_factor


# Example usage and testing
if __name__ == "__main__":
    # Create unified water chemistry system
    water_chemistry = WaterChemistry(WaterChemistryConfig())
    
    # Create steam generator model with unified water chemistry
    sg = SteamGenerator(water_chemistry=water_chemistry)
    
    print("Steam Generator Physics Model - Parameter Validation")
    print("=" * 60)
    print("Based on Westinghouse AP1000 Design with Unified Water Chemistry")
    print()
    
    # Display key parameters and their sources
    config = sg.config
    print("Key Design Parameters:")
    print(f"  Heat Transfer Area: {config.heat_transfer_area_per_sg:.0f} m² (AP1000: ~5100 m²)")
    print(f"  Tube Count: {config.tube_count_per_sg} (AP1000 actual)")
    print(f"  Design Power: {config.design_thermal_power_per_sg/1e6:.0f} MW per SG")
    print(f"  Primary Flow: {config.primary_design_flow:.0f} kg/s per SG")
    print(f"  Secondary Flow: {config.secondary_design_flow:.0f} kg/s per SG")
    print()
    
    # Display water chemistry parameters
    tsp_params = water_chemistry.get_tsp_fouling_parameters()
    print(f"Unified Water Chemistry Parameters:")
    print(f"  Iron: {tsp_params['iron_concentration']:.3f} ppm")
    print(f"  Copper: {tsp_params['copper_concentration']:.3f} ppm")
    print(f"  Silica: {tsp_params['silica_concentration']:.1f} ppm")
    print(f"  pH: {tsp_params['ph']:.2f}")
    print(f"  Dissolved Oxygen: {tsp_params['dissolved_oxygen']:.3f} ppm")
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
