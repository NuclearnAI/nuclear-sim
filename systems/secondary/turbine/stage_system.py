"""
Turbine Stage System Model for PWR Steam Turbine

This module implements a comprehensive multi-stage turbine system that manages
individual turbine stages, extraction flows, and stage-level control logic.

Parameter Sources:
- Steam Turbine Theory and Practice (Kearton)
- Power Plant Engineering (Black & Veatch)
- GE Steam Turbine Design Manual
- Multi-stage turbine design specifications

Physical Basis:
- Individual stage steam expansion
- Stage-by-stage pressure and temperature tracking
- Extraction flow management
- Stage performance optimization
- Control logic for stage coordination
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from simulator.state import auto_register

warnings.filterwarnings("ignore")


@dataclass
class TurbineStageConfig:
    """
    Configuration parameters for individual turbine stage
    
    References:
    - Typical PWR turbine stage designs
    - Steam expansion optimization
    - Extraction point specifications
    """
    
    # Stage identification
    stage_id: str = "HP-1"                    # Stage identifier (HP-1, HP-2, LP-1, etc.)
    stage_type: str = "impulse"               # "impulse", "reaction", "mixed"
    turbine_section: str = "HP"               # "HP", "IP", "LP"
    
    # Design parameters
    design_inlet_pressure: float = 6.895     # MPa design inlet pressure
    design_outlet_pressure: float = 4.5      # MPa design outlet pressure
    design_steam_flow: float = 555.0         # kg/s design steam flow
    design_efficiency: float = 0.88          # Design isentropic efficiency
    
    # Physical geometry
    blade_height: float = 0.05               # m blade height
    blade_chord: float = 0.03                # m blade chord length
    blade_count: int = 120                   # Number of blades
    nozzle_area: float = 0.1                 # m² nozzle throat area
    
    # Performance parameters
    reaction_ratio: float = 0.5              # Reaction ratio (0=impulse, 1=reaction)
    velocity_coefficient: float = 0.95       # Velocity coefficient
    blade_speed_ratio: float = 0.47          # Optimal blade speed ratio
    
    # Extraction parameters (if applicable)
    has_extraction: bool = False             # Stage has extraction point
    extraction_pressure: float = 2.0         # MPa extraction pressure
    max_extraction_flow: float = 50.0        # kg/s maximum extraction flow
    min_extraction_flow: float = 5.0         # kg/s minimum extraction flow
    
    # Degradation parameters
    fouling_rate: float = 0.00001            # Efficiency loss per hour
    erosion_rate: float = 0.000001           # Blade wear rate
    deposit_buildup_rate: float = 0.00005    # Deposit accumulation rate


@dataclass
class TurbineStageSystemConfig:
    """
    Configuration for complete multi-stage turbine system
    
    References:
    - PWR turbine arrangements
    - Stage coordination strategies
    - Extraction system design
    """
    
    # System configuration
    system_id: str = "TSS-001"               # Turbine stage system identifier
    stage_configs: List[TurbineStageConfig] = field(default_factory=list)
    
    # HP turbine configuration
    hp_stage_count: int = 8                  # Number of HP stages
    hp_inlet_pressure: float = 6.895         # MPa HP inlet pressure
    hp_outlet_pressure: float = 1.2          # MPa HP outlet pressure
    
    # LP turbine configuration
    lp_stage_count: int = 6                  # Number of LP stages per flow
    lp_flow_count: int = 2                   # Number of LP flows (double flow)
    lp_inlet_pressure: float = 1.15          # MPa LP inlet pressure
    lp_outlet_pressure: float = 0.007        # MPa LP outlet pressure
    
    # Extraction system
    extraction_point_count: int = 6          # Number of extraction points
    extraction_pressures: List[float] = field(default_factory=lambda: [4.0, 2.5, 1.5, 0.8, 0.4, 0.15])
    
    # Control parameters
    stage_loading_strategy: str = "optimal"   # "optimal", "uniform", "custom"
    extraction_control_mode: str = "pressure" # "pressure", "flow", "enthalpy"
    performance_optimization: bool = True     # Enable performance optimization
    
    # Operating limits
    max_stage_loading: float = 1.2           # Maximum stage loading factor
    min_stage_efficiency: float = 0.7        # Minimum allowable stage efficiency
    max_extraction_variation: float = 0.1    # Maximum extraction flow variation


@auto_register("SECONDARY", "turbine", id_source="config.stage_id")
class TurbineStage:
    """
    Individual turbine stage model - analogous to individual SteamJetEjector
    
    This model implements:
    1. Stage-specific steam expansion
    2. Blade performance and degradation
    3. Extraction flow management
    4. Stage efficiency tracking
    5. Performance optimization
    """
    
    def __init__(self, config: TurbineStageConfig):
        """Initialize individual turbine stage"""
        self.config = config
        
        # Stage thermodynamic state
        self.inlet_pressure = config.design_inlet_pressure      # MPa
        self.inlet_temperature = 285.8                          # °C
        self.inlet_enthalpy = 0.0                              # kJ/kg
        self.inlet_entropy = 0.0                               # kJ/kg/K
        self.inlet_flow = config.design_steam_flow             # kg/s
        
        self.outlet_pressure = config.design_outlet_pressure    # MPa
        self.outlet_temperature = 245.0                        # °C
        self.outlet_enthalpy = 0.0                             # kJ/kg
        self.outlet_entropy = 0.0                              # kJ/kg/K
        self.outlet_flow = config.design_steam_flow            # kg/s
        
        # Stage performance
        self.actual_efficiency = config.design_efficiency      # Current efficiency
        self.power_output = 0.0                                # MW stage power
        self.enthalpy_drop = 0.0                               # kJ/kg enthalpy drop
        
        # Extraction state (if applicable)
        self.extraction_flow = 0.0                             # kg/s current extraction
        self.extraction_pressure = config.extraction_pressure  # MPa extraction pressure
        self.extraction_enthalpy = 0.0                        # kJ/kg extraction enthalpy
        
        # Blade and mechanical state
        self.blade_condition_factor = 1.0                     # Blade condition (1.0 = new)
        self.fouling_factor = 1.0                             # Fouling effect (1.0 = clean)
        self.deposit_thickness = 0.0                          # mm deposit thickness
        self.blade_wear_factor = 1.0                          # Wear effect (1.0 = no wear)
        
        # Performance tracking
        self.operating_hours = 0.0                             # Stage operating hours
        self.load_cycles = 0                                   # Number of load cycles
        self.efficiency_degradation = 0.0                     # Cumulative efficiency loss
        
        # Stage loading and optimization
        self.loading_factor = 1.0                              # Current loading (1.0 = design)
        self.optimal_loading = 1.0                             # Optimal loading for efficiency
        
    def calculate_stage_expansion(self,
                                inlet_pressure: float,
                                inlet_temperature: float,
                                inlet_flow: float,
                                outlet_pressure: float,
                                extraction_demand: float = 0.0) -> Dict[str, float]:
        """
        Calculate steam expansion through individual stage
        
        Args:
            inlet_pressure: Stage inlet pressure (MPa)
            inlet_temperature: Stage inlet temperature (°C)
            inlet_flow: Stage inlet flow (kg/s)
            outlet_pressure: Stage outlet pressure (MPa)
            extraction_demand: Requested extraction flow (kg/s)
            
        Returns:
            Dictionary with stage expansion results
        """
        # Update inlet conditions
        self.inlet_pressure = inlet_pressure
        self.inlet_temperature = inlet_temperature
        self.inlet_flow = inlet_flow
        
        # OPTION A: SMART PRESSURE MANAGEMENT WITH OPERATING CONDITION RESPONSIVENESS
        # Calculate design pressure ratio for this stage
        design_pressure_ratio = self.config.design_outlet_pressure / self.config.design_inlet_pressure
        
        # Calculate operating condition factors
        load_factor = self.inlet_flow / self.config.design_steam_flow if self.config.design_steam_flow > 0 else 1.0
        load_factor = np.clip(load_factor, 0.3, 1.5)  # Reasonable operating range
        
        # Calculate steam condition factors
        design_temp = 285.8  # °C typical PWR steam temperature
        temp_factor = (inlet_temperature + 273.15) / (design_temp + 273.15)
        temp_factor = np.clip(temp_factor, 0.8, 1.2)  # Reasonable temperature range
        
        # Adjust pressure ratio based on operating conditions
        # Higher load = more pressure drop (more work extraction)
        # Higher temperature = more efficient expansion (more pressure drop)
        load_adjustment = 0.9 + 0.2 * load_factor  # Range: 0.96 to 1.2
        temp_adjustment = 0.95 + 0.1 * (temp_factor - 1.0)  # Range: 0.93 to 1.07
        
        # Calculate adjusted pressure ratio (more expansion at higher loads/temps)
        adjusted_pressure_ratio = design_pressure_ratio * load_adjustment * temp_adjustment
        adjusted_pressure_ratio = np.clip(adjusted_pressure_ratio, 
                                        design_pressure_ratio * 0.85,  # Minimum: 15% more expansion
                                        design_pressure_ratio * 1.15)  # Maximum: 15% less expansion
        
        # Calculate physics-based outlet pressure
        physics_based_outlet_pressure = inlet_pressure * adjusted_pressure_ratio
        
        # CRITICAL VALIDATION: Ensure outlet pressure is always less than inlet pressure
        if outlet_pressure >= inlet_pressure:
            print(f"WARNING: Stage {self.config.stage_id} - Invalid pressure ratio detected!")
            print(f"  Requested: Inlet {inlet_pressure:.3f} MPa → Outlet {outlet_pressure:.3f} MPa (ratio: {outlet_pressure/inlet_pressure:.4f})")
            print(f"  Using physics-based: Inlet {inlet_pressure:.3f} MPa → Outlet {physics_based_outlet_pressure:.3f} MPa (ratio: {adjusted_pressure_ratio:.4f})")
            print(f"  Operating conditions: Load factor {load_factor:.3f}, Temp factor {temp_factor:.3f}")
            
            # Use physics-based pressure
            self.outlet_pressure = physics_based_outlet_pressure
        else:
            # Requested outlet pressure is valid, but ensure it's within reasonable bounds
            # Allow some flexibility but prevent extreme deviations from design
            
            # Special handling for final LP stage (LP-6) which must reach condenser vacuum
            if self.config.stage_id == "LP-6":
                # LP-6 must be able to reach condenser pressure (0.007 MPa target)
                # Based on condenser/vacuum system design: alarm at 0.010 MPa, trip at 0.012 MPa
                min_allowed_pressure = 0.002  # Deep vacuum capability
                max_allowed_pressure = 0.009  # Below condenser alarm threshold
            else:
                # Normal pressure validation for other stages
                min_allowed_pressure = inlet_pressure * (design_pressure_ratio * 0.7)  # 30% more expansion than design
                max_allowed_pressure = inlet_pressure * (design_pressure_ratio * 1.3)  # 30% less expansion than design
            
            if outlet_pressure < min_allowed_pressure:
                print(f"INFO: Stage {self.config.stage_id} - Outlet pressure too low, limiting to reasonable range")
                print(f"  Requested: {outlet_pressure:.3f} MPa, Limited to: {min_allowed_pressure:.3f} MPa")
                self.outlet_pressure = min_allowed_pressure
            elif outlet_pressure > max_allowed_pressure:
                print(f"INFO: Stage {self.config.stage_id} - Outlet pressure too high, limiting to reasonable range")
                print(f"  Requested: {outlet_pressure:.3f} MPa, Limited to: {max_allowed_pressure:.3f} MPa")
                self.outlet_pressure = max_allowed_pressure
            else:
                # Requested pressure is reasonable, use it
                self.outlet_pressure = outlet_pressure
        
        # Calculate inlet properties
        self.inlet_enthalpy = self._steam_enthalpy(inlet_temperature, inlet_pressure)
        self.inlet_entropy = self._steam_entropy(inlet_temperature, inlet_pressure)
        
        # Handle extraction flow
        if self.config.has_extraction and extraction_demand > 0:
            # Limit extraction to allowable range
            self.extraction_flow = np.clip(extraction_demand, 
                                         self.config.min_extraction_flow,
                                         min(self.config.max_extraction_flow, inlet_flow * 0.3))
            
            # Extraction occurs at intermediate pressure
            extraction_pressure_ratio = 0.7  # Extraction at 70% of expansion
            self.extraction_pressure = inlet_pressure * extraction_pressure_ratio + outlet_pressure * (1 - extraction_pressure_ratio)
            
            # Calculate extraction enthalpy (isentropic expansion to extraction pressure)
            extraction_temp = self._saturation_temperature(self.extraction_pressure)
            self.extraction_enthalpy = self._steam_enthalpy(extraction_temp, self.extraction_pressure)
        else:
            self.extraction_flow = 0.0
        
        # Flow through stage after extraction
        self.outlet_flow = self.inlet_flow - self.extraction_flow
        
        # Isentropic expansion calculation using the CORRECTED outlet pressure
        outlet_temp_isentropic = self._isentropic_expansion_temperature(
            inlet_temperature, inlet_pressure, self.outlet_pressure
        )
        outlet_enthalpy_isentropic = self._steam_enthalpy(outlet_temp_isentropic, self.outlet_pressure)
        
        # Actual expansion with efficiency losses and degradation effects
        total_efficiency = (self.actual_efficiency * 
                          self.blade_condition_factor * 
                          self.fouling_factor * 
                          self.blade_wear_factor)
        
        # Enthalpy drop calculation with validation
        isentropic_enthalpy_drop = self.inlet_enthalpy - outlet_enthalpy_isentropic
        
        # Since we've already corrected the pressure, enthalpy drop should be positive
        # But add a safety check just in case
        if isentropic_enthalpy_drop <= 0:
            # This should rarely happen now that pressure is corrected
            print(f"INFO: Stage {self.config.stage_id} - Enthalpy drop still negative after pressure correction: {isentropic_enthalpy_drop:.2f} kJ/kg")
            print(f"  Using corrected pressures: Inlet {inlet_pressure:.3f} MPa → Outlet {self.outlet_pressure:.3f} MPa")
            
            # Force a minimum positive enthalpy drop based on corrected pressure ratio
            pressure_ratio = self.outlet_pressure / inlet_pressure
            min_enthalpy_drop = 50.0 * (1.0 - pressure_ratio)  # Approximate 50 kJ/kg per unit pressure ratio
            isentropic_enthalpy_drop = max(min_enthalpy_drop, 10.0)  # Minimum 10 kJ/kg
            
            print(f"  Corrected enthalpy drop to: {isentropic_enthalpy_drop:.2f} kJ/kg")
        
        actual_enthalpy_drop = total_efficiency * isentropic_enthalpy_drop
        
        # Ensure actual enthalpy drop is also positive
        if actual_enthalpy_drop <= 0:
            print(f"WARNING: Stage {self.config.stage_id} - Negative actual enthalpy drop: {actual_enthalpy_drop:.2f} kJ/kg")
            actual_enthalpy_drop = max(1.0, isentropic_enthalpy_drop * 0.5)  # At least 50% of isentropic
            print(f"  Corrected to: {actual_enthalpy_drop:.2f} kJ/kg")
        
        self.enthalpy_drop = actual_enthalpy_drop
        
        # Actual outlet conditions
        self.outlet_enthalpy = self.inlet_enthalpy - actual_enthalpy_drop
        self.outlet_temperature = self._enthalpy_to_temperature(self.outlet_enthalpy, outlet_pressure)
        
        # Power calculation with validation
        # Power from main steam flow
        main_power = self.outlet_flow * actual_enthalpy_drop / 1000.0  # MW
        
        # Ensure power is positive
        if main_power < 0:
            print(f"WARNING: Stage {self.config.stage_id} - Negative main power: {main_power:.2f} MW")
            main_power = 0.0
        
        # Power from extraction flow (partial expansion)
        if self.extraction_flow > 0:
            extraction_enthalpy_drop = self.inlet_enthalpy - self.extraction_enthalpy
            extraction_power = self.extraction_flow * extraction_enthalpy_drop / 1000.0  # MW
        else:
            extraction_power = 0.0
        
        self.power_output = main_power + extraction_power
        
        # Update loading factor
        design_enthalpy_drop = self.config.design_efficiency * isentropic_enthalpy_drop
        self.loading_factor = actual_enthalpy_drop / max(1.0, design_enthalpy_drop)
        
        return {
            'power_output': self.power_output,
            'outlet_pressure': self.outlet_pressure,
            'outlet_temperature': self.outlet_temperature,
            'outlet_enthalpy': self.outlet_enthalpy,
            'outlet_flow': self.outlet_flow,
            'extraction_flow': self.extraction_flow,
            'extraction_pressure': self.extraction_pressure,
            'extraction_enthalpy': self.extraction_enthalpy,
            'enthalpy_drop': self.enthalpy_drop,
            'stage_efficiency': total_efficiency,
            'loading_factor': self.loading_factor
        }
    
    def update_degradation(self, dt: float) -> Dict[str, float]:
        """
        Update stage degradation mechanisms
        
        Args:
            dt: Time step (hours)
            
        Returns:
            Dictionary with degradation results
        """
        # Fouling degradation (deposit buildup)
        fouling_increase = self.config.fouling_rate * dt
        self.efficiency_degradation += fouling_increase
        
        # Deposit thickness increase
        deposit_increase = self.config.deposit_buildup_rate * dt
        self.deposit_thickness += deposit_increase
        
        # Fouling factor based on deposit thickness
        self.fouling_factor = 1.0 / (1.0 + self.deposit_thickness / 0.5)  # 0.5mm reference
        
        # Blade wear (erosion)
        wear_increase = self.config.erosion_rate * dt
        blade_wear = wear_increase * (self.loading_factor ** 2)  # Wear increases with loading
        self.blade_wear_factor = max(0.7, self.blade_wear_factor - blade_wear)
        
        # Overall blade condition
        self.blade_condition_factor = min(self.fouling_factor, self.blade_wear_factor)
        
        # Update actual efficiency
        min_efficiency = getattr(self.config, 'min_stage_efficiency', 0.7)
        self.actual_efficiency = max(min_efficiency,
                                   self.config.design_efficiency - self.efficiency_degradation)
        
        # Update operating hours
        self.operating_hours += dt
        
        return {
            'efficiency_degradation': self.efficiency_degradation,
            'deposit_thickness': self.deposit_thickness,
            'fouling_factor': self.fouling_factor,
            'blade_wear_factor': self.blade_wear_factor,
            'blade_condition_factor': self.blade_condition_factor,
            'actual_efficiency': self.actual_efficiency,
            'operating_hours': self.operating_hours
        }
    
    def perform_maintenance(self, maintenance_type: str) -> Dict[str, float]:
        """
        Perform maintenance on stage
        
        Args:
            maintenance_type: Type of maintenance
            
        Returns:
            Dictionary with maintenance results
        """
        results = {}
        
        if maintenance_type == "cleaning":
            # Remove deposits and fouling
            removed_deposits = self.deposit_thickness
            self.deposit_thickness = 0.0
            self.fouling_factor = 1.0
            self.efficiency_degradation *= 0.3  # Partial efficiency recovery
            results['deposits_removed'] = removed_deposits
            
        elif maintenance_type == "blade_replacement":
            # Replace worn blades
            self.blade_wear_factor = 1.0
            self.blade_condition_factor = self.fouling_factor
            results['blades_replaced'] = True
            
        elif maintenance_type == "overhaul":
            # Complete overhaul
            self.deposit_thickness = 0.0
            self.fouling_factor = 1.0
            self.blade_wear_factor = 1.0
            self.blade_condition_factor = 1.0
            self.efficiency_degradation = 0.0
            self.actual_efficiency = self.config.design_efficiency
            results['complete_overhaul'] = True
        
        return results
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get stage state for monitoring"""
        return {
            f'inlet_pressure': self.inlet_pressure,
            f'outlet_pressure': self.outlet_pressure,
            f'inlet_temperature': self.inlet_temperature,
            f'outlet_temperature': self.outlet_temperature,
            f'power_output': self.power_output,
            f'efficiency': self.actual_efficiency,
            f'extraction_flow': self.extraction_flow,
            f'loading_factor': self.loading_factor,
            f'blade_condition': self.blade_condition_factor,
            f'deposit_thickness': self.deposit_thickness,
            f'operating_hours': self.operating_hours
        }
    
    def reset(self) -> None:
        """Reset stage to initial conditions"""
        self.inlet_pressure = self.config.design_inlet_pressure
        self.outlet_pressure = self.config.design_outlet_pressure
        self.inlet_temperature = 285.8
        self.outlet_temperature = 245.0
        self.inlet_flow = self.config.design_steam_flow
        self.outlet_flow = self.config.design_steam_flow
        self.actual_efficiency = self.config.design_efficiency
        self.power_output = 0.0
        self.enthalpy_drop = 0.0
        self.extraction_flow = 0.0
        self.blade_condition_factor = 1.0
        self.fouling_factor = 1.0
        self.deposit_thickness = 0.0
        self.blade_wear_factor = 1.0
        self.operating_hours = 0.0
        self.load_cycles = 0
        self.efficiency_degradation = 0.0
        self.loading_factor = 1.0
        self.optimal_loading = 1.0
    
    # Thermodynamic property methods (simplified)
    def _steam_enthalpy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate steam enthalpy (kJ/kg) with improved accuracy"""
        # Validate inputs
        pressure_mpa = max(0.001, min(pressure_mpa, 22.0))  # Limit to reasonable range
        temp_c = max(0.0, min(temp_c, 800.0))  # Limit to reasonable range
        
        sat_temp = self._saturation_temperature(pressure_mpa)
        
        if temp_c <= sat_temp:
            # Saturated steam
            return self._saturation_enthalpy_vapor(pressure_mpa)
        else:
            # Superheated steam - improved calculation
            h_g = self._saturation_enthalpy_vapor(pressure_mpa)
            superheat = temp_c - sat_temp
            
            # More accurate specific heat for superheated steam
            # Varies with pressure and temperature
            if pressure_mpa > 10.0:
                cp_superheat = 2.5  # kJ/kg/K at high pressure
            elif pressure_mpa > 1.0:
                cp_superheat = 2.2  # kJ/kg/K at medium pressure
            else:
                cp_superheat = 2.0  # kJ/kg/K at low pressure
            
            return h_g + cp_superheat * superheat
    
    def _steam_entropy(self, temp_c: float, pressure_mpa: float) -> float:
        """Calculate steam entropy (kJ/kg/K)"""
        sat_temp = self._saturation_temperature(pressure_mpa)
        s_f = 4.18 * np.log((sat_temp + 273.15) / 273.15)
        s_fg = 2257.0 / (sat_temp + 273.15)
        s_g = s_f + s_fg
        
        if temp_c > sat_temp:
            superheat_entropy = 2.1 * np.log((temp_c + 273.15) / (sat_temp + 273.15))
            return s_g + superheat_entropy
        else:
            return s_g
    
    def _saturation_temperature(self, pressure_mpa: float) -> float:
        """Calculate saturation temperature"""
        if pressure_mpa <= 0.001:
            return 10.0
        A, B, C = 8.07131, 1730.63, 233.426
        pressure_bar = pressure_mpa * 10.0
        pressure_bar = np.clip(pressure_bar, 0.01, 100.0)
        temp_c = B / (A - np.log10(pressure_bar)) - C
        return np.clip(temp_c, 10.0, 374.0)
    
    def _saturation_enthalpy_vapor(self, pressure_mpa: float) -> float:
        """Calculate saturation enthalpy of steam"""
        temp = self._saturation_temperature(pressure_mpa)
        h_f = 4.18 * temp
        h_fg = 2257.0 * (1.0 - temp / 374.0) ** 0.38
        return h_f + h_fg
    
    def _isentropic_expansion_temperature(self, inlet_temp: float, inlet_pressure: float, outlet_pressure: float) -> float:
        """Calculate isentropic expansion temperature"""
        # Simplified isentropic relation for steam
        pressure_ratio = outlet_pressure / inlet_pressure
        temp_ratio = pressure_ratio ** 0.25  # Approximate for steam
        return (inlet_temp + 273.15) * temp_ratio - 273.15
    
    def _enthalpy_to_temperature(self, enthalpy: float, pressure: float) -> float:
        """Convert enthalpy to temperature at given pressure"""
        sat_temp = self._saturation_temperature(pressure)
        h_g = self._saturation_enthalpy_vapor(pressure)
        
        if enthalpy <= h_g:
            return sat_temp
        else:
            superheat = (enthalpy - h_g) / 2.1
            return sat_temp + superheat


class TurbineStageControlLogic:
    """
    Stage control logic - analogous to VacuumControlLogic
    
    Handles:
    - Stage loading optimization
    - Extraction flow control
    - Performance balancing
    - Stage coordination
    """
    
    def __init__(self, config: TurbineStageSystemConfig):
        self.config = config
        self.optimization_enabled = config.performance_optimization
        self.control_mode = config.extraction_control_mode
        
        # Control state
        self.total_load_demand = 1.0          # Total turbine load demand
        self.extraction_demands = {}          # Extraction flow demands by stage
        self.stage_loading_targets = {}       # Optimal loading for each stage
        
    def update_control_logic(self,
                           stages: Dict[str, TurbineStage],
                           total_steam_flow: float,
                           load_demand: float,
                           extraction_demands: Dict[str, float],
                           dt: float) -> Dict[str, Dict]:
        """
        Update stage control logic
        
        Args:
            stages: Dictionary of stage objects
            total_steam_flow: Total steam flow to turbine (kg/s)
            load_demand: Total load demand (0-1)
            extraction_demands: Extraction flow demands by stage ID
            dt: Time step (hours)
            
        Returns:
            Dictionary with stage control commands
        """
        commands = {}
        
        self.total_load_demand = load_demand
        self.extraction_demands = extraction_demands
        
        if self.config.stage_loading_strategy == "optimal":
            commands.update(self._optimal_loading_control(stages, total_steam_flow, load_demand))
        elif self.config.stage_loading_strategy == "uniform":
            commands.update(self._uniform_loading_control(stages, load_demand))
        
        # Extraction flow control
        commands.update(self._extraction_flow_control(stages, extraction_demands))
        
        return commands
    
    def _optimal_loading_control(self,
                               stages: Dict[str, TurbineStage],
                               steam_flow: float,
                               load_demand: float) -> Dict[str, Dict]:
        """Optimize stage loading for maximum efficiency"""
        commands = {}
        
        # Calculate optimal loading distribution
        for stage_id, stage in stages.items():
            # Optimal loading based on stage characteristics
            if stage.config.turbine_section == "HP":
                # HP stages prefer higher loading
                optimal_loading = 0.9 + 0.2 * load_demand
            elif stage.config.turbine_section == "LP":
                # LP stages prefer moderate loading
                optimal_loading = 0.8 + 0.3 * load_demand
            else:
                optimal_loading = 0.85 + 0.25 * load_demand
            
            # Limit to maximum allowable loading
            optimal_loading = min(optimal_loading, self.config.max_stage_loading)
            
            self.stage_loading_targets[stage_id] = optimal_loading
            
            commands[stage_id] = {
                'target_loading': optimal_loading,
                'steam_flow_fraction': optimal_loading * load_demand
            }
        
        return commands
    
    def _uniform_loading_control(self,
                               stages: Dict[str, TurbineStage],
                               load_demand: float) -> Dict[str, Dict]:
        """Uniform loading across all stages"""
        commands = {}
        
        for stage_id in stages.keys():
            commands[stage_id] = {
                'target_loading': load_demand,
                'steam_flow_fraction': load_demand
            }
        
        return commands
    
    def _extraction_flow_control(self,
                               stages: Dict[str, TurbineStage],
                               extraction_demands: Dict[str, float]) -> Dict[str, Dict]:
        """Control extraction flows"""
        commands = {}
        
        for stage_id, stage in stages.items():
            if stage.config.has_extraction:
                demanded_flow = extraction_demands.get(stage_id, 0.0)
                
                # Limit extraction flow variation
                current_flow = stage.extraction_flow
                max_change = self.config.max_extraction_variation * stage.config.max_extraction_flow
                
                if abs(demanded_flow - current_flow) > max_change:
                    if demanded_flow > current_flow:
                        target_flow = current_flow + max_change
                    else:
                        target_flow = current_flow - max_change
                else:
                    target_flow = demanded_flow
                
                if stage_id not in commands:
                    commands[stage_id] = {}
                commands[stage_id]['extraction_flow_target'] = target_flow
        
        return commands


@auto_register("SECONDARY", "turbine", id_source="config.system_id")
class TurbineStageSystem:
    """
    Multi-stage turbine system - analogous to VacuumSystem
    
    This model implements:
    1. Multiple turbine stage coordination
    2. Stage-by-stage steam expansion
    3. Extraction flow management
    4. Performance optimization
    5. Stage control logic
    6. System-level monitoring
    """
    
    def __init__(self, config: Optional[TurbineStageSystemConfig] = None):
        """Initialize turbine stage system"""
        if config is None:
            config = TurbineStageSystemConfig()
        
        self.config = config
        
        # Create stage objects
        self.stages = {}
        if config.stage_configs:
            for stage_config in config.stage_configs:
                self.stages[stage_config.stage_id] = TurbineStage(stage_config)
        else:
            # Create default stage configuration
            self._create_default_stages()
        
        # Control system
        self.control_logic = TurbineStageControlLogic(config)
        
        # System state
        self.total_power_output = 0.0         # MW total power
        self.total_steam_flow = 0.0           # kg/s total steam flow
        self.overall_efficiency = 0.0         # Overall system efficiency
        self.total_extraction_flow = 0.0      # kg/s total extraction
        
        # Performance tracking
        self.system_efficiency = 1.0          # System efficiency factor
        self.operating_hours = 0.0            # Total operating hours
        
    def _create_default_stages(self):
        """Create default stage configuration"""
        # HP stages
        hp_pressures = np.linspace(6.895, 1.2, self.config.hp_stage_count + 1)
        for i in range(self.config.hp_stage_count):
            stage_config = TurbineStageConfig(
                stage_id=f"HP-{i+1}",
                stage_type="impulse" if i < 2 else "reaction",
                turbine_section="HP",
                design_inlet_pressure=hp_pressures[i],
                design_outlet_pressure=hp_pressures[i+1],
                has_extraction=(i >= 2 and i < 6),  # Extraction on stages 3-6
                extraction_pressure=hp_pressures[i] * 0.8
            )
            self.stages[stage_config.stage_id] = TurbineStage(stage_config)
        
        # LP stages
        lp_pressures = np.linspace(1.15, 0.007, self.config.lp_stage_count + 1)
        for i in range(self.config.lp_stage_count):
            stage_config = TurbineStageConfig(
                stage_id=f"LP-{i+1}",
                stage_type="reaction",
                turbine_section="LP",
                design_inlet_pressure=lp_pressures[i],
                design_outlet_pressure=lp_pressures[i+1],
                design_steam_flow=555.0 * self.config.lp_flow_count,  # Double flow
                has_extraction=(i < 3),  # Extraction on first 3 LP stages
                extraction_pressure=lp_pressures[i] * 0.7
            )
            self.stages[stage_config.stage_id] = TurbineStage(stage_config)
    
    def calculate_stage_by_stage_expansion(self,
                                         inlet_pressure: float,
                                         inlet_temperature: float,
                                         inlet_flow: float,
                                         extraction_demands: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate steam expansion through all stages using realistic turbine design principles
        
        Args:
            inlet_pressure: Turbine inlet pressure (MPa)
            inlet_temperature: Turbine inlet temperature (°C)
            inlet_flow: Turbine inlet flow (kg/s)
            extraction_demands: Extraction flow demands
            
        Returns:
            Dictionary with expansion results
        """
        results = {
            'stages': {},
            'total_power': 0.0,
            'total_extraction': 0.0,
            'outlet_conditions': {}
        }
        
        # Sort stages by pressure (high to low)
        sorted_stages = sorted(self.stages.items(), 
                             key=lambda x: x[1].config.design_inlet_pressure, 
                             reverse=True)
        
        current_pressure = inlet_pressure
        current_temperature = inlet_temperature
        current_flow = inlet_flow
        
        # Calculate dynamic pressure ratios based on actual steam conditions
        def get_dynamic_pressure_ratio(stage_id: str, stage_position: int, total_stages: int, 
                                     current_pressure: float, inlet_pressure: float, 
                                     inlet_flow: float) -> float:
            """
            Calculate dynamic pressure ratio that responds to actual steam conditions:
            - Higher steam flow = more pressure drop (more work extraction)
            - Maintains proper pressure progression through turbine
            - Responds to changes in inlet conditions from steam generators
            - Ensures realistic pressure ratios that don't trigger validation warnings
            """
            # Get the stage object to access design parameters
            stage = self.stages[stage_id]
            design_pressure_ratio = stage.config.design_outlet_pressure / stage.config.design_inlet_pressure
            
            # Calculate load factor based on actual vs design steam flow
            design_flow = stage.config.design_steam_flow
            load_factor = inlet_flow / design_flow if design_flow > 0 else 1.0
            load_factor = np.clip(load_factor, 0.3, 1.5)  # Reasonable operating range
            
            # Calculate pressure factor based on actual vs design inlet pressure
            design_inlet_pressure = stage.config.design_inlet_pressure
            pressure_factor = current_pressure / design_inlet_pressure if design_inlet_pressure > 0 else 1.0
            pressure_factor = np.clip(pressure_factor, 0.5, 1.5)  # Reasonable pressure range
            
            # Adjust pressure ratio based on operating conditions
            # More conservative adjustments to prevent validation warnings
            load_adjustment = 0.90 + 0.2 * (load_factor - 1.0)  # Range: 0.84 to 1.10
            pressure_adjustment = 0.95 + 0.1 * (pressure_factor - 1.0)  # Range: 0.90 to 1.05
            
            # Calculate dynamic pressure ratio
            dynamic_ratio = design_pressure_ratio * load_adjustment * pressure_adjustment
            
            # Apply stage-specific limits based on turbine design - more conservative
            if stage_id.startswith('HP'):
                # HP stages: conservative pressure ratio range
                min_ratio = 0.70  # Less aggressive expansion
                max_ratio = 0.95  # Minimum expansion
            elif stage_id.startswith('LP'):
                # LP stages: moderate expansion to avoid validation warnings
                min_ratio = 0.50  # More conservative than before (was 0.35)
                max_ratio = 0.85  # Moderate expansion
            else:
                min_ratio = 0.65
                max_ratio = 0.90
            
            # Special handling for LP stages to ensure smooth pressure progression
            if stage_id.startswith('LP'):
                # Calculate remaining pressure drop needed to reach condenser
                remaining_stages = total_stages - stage_position - 1
                if remaining_stages > 0:
                    # Ensure we leave enough pressure drop for remaining stages
                    target_final_pressure = 0.007  # MPa condenser pressure
                    min_pressure_per_remaining_stage = 0.85  # Minimum ratio per stage
                    min_outlet_pressure = target_final_pressure / (min_pressure_per_remaining_stage ** remaining_stages)
                    max_allowable_ratio = min_outlet_pressure / current_pressure
                    
                    # Don't go below this ratio to ensure we can reach condenser
                    min_ratio = max(min_ratio, max_allowable_ratio)
            
            # Ensure final stage reaches condenser pressure
            if stage_id == "LP-6":
                # LP-6 must reach condenser vacuum regardless of other factors
                target_outlet = 0.007  # MPa condenser pressure
                calculated_ratio = target_outlet / current_pressure
                # Ensure ratio is reasonable (not too aggressive)
                dynamic_ratio = max(calculated_ratio, 0.05)  # Minimum 5% of inlet pressure
            else:
                dynamic_ratio = np.clip(dynamic_ratio, min_ratio, max_ratio)
            
            return dynamic_ratio
        
        final_pressure = 0.007  # MPa - typical condenser pressure
        
        for i, (stage_id, stage) in enumerate(sorted_stages):
            # Get dynamic pressure ratio that responds to steam conditions
            pressure_ratio = get_dynamic_pressure_ratio(stage_id, i, len(sorted_stages), 
                                                      current_pressure, inlet_pressure, inlet_flow)
            
            # Calculate outlet pressure
            outlet_pressure = current_pressure * pressure_ratio
            
            # Ensure we don't go below condenser pressure
            outlet_pressure = max(outlet_pressure, final_pressure)
            
            # For final stages, ensure we actually reach condenser pressure
            remaining_stages = len(sorted_stages) - i - 1
            if remaining_stages == 0:
                # Last stage must reach condenser pressure
                outlet_pressure = final_pressure
            elif remaining_stages == 1:
                # Second to last stage: leave room for final stage
                min_final_ratio = 0.5  # Minimum ratio for final stage
                max_pressure_for_next = final_pressure / min_final_ratio
                outlet_pressure = max(outlet_pressure, max_pressure_for_next)
            
            # Validate pressure drop
            if outlet_pressure >= current_pressure:
                print(f"WARNING: Stage {stage_id} - No pressure drop! Inlet: {current_pressure:.3f} MPa, Calculated outlet: {outlet_pressure:.3f} MPa")
                # Force a minimum 5% pressure drop
                outlet_pressure = current_pressure * 0.95
                outlet_pressure = max(outlet_pressure, final_pressure)
            
            # Get extraction demand for this stage
            extraction_demand = extraction_demands.get(stage_id, 0.0)
            
            # Calculate stage expansion
            stage_result = stage.calculate_stage_expansion(
                current_pressure, current_temperature, current_flow,
                outlet_pressure, extraction_demand
            )
            
            results['stages'][stage_id] = stage_result
            
            # Accumulate power and extraction
            stage_power = stage_result['power_output']
            stage_extraction = stage_result['extraction_flow']
            
            results['total_power'] += stage_power
            results['total_extraction'] += stage_extraction
            
            # Update conditions for next stage
            current_pressure = stage_result['outlet_pressure']
            current_temperature = stage_result['outlet_temperature']
            current_flow = stage_result['outlet_flow']
         
        # Final outlet conditions
        results['outlet_conditions'] = {
            'pressure': current_pressure,
            'temperature': current_temperature,
            'flow': current_flow
        }
        
        return results
    
    def update_state(self,
                    inlet_pressure: float,
                    inlet_temperature: float,
                    inlet_flow: float,
                    load_demand: float,
                    extraction_demands: Dict[str, float],
                    dt: float) -> Dict[str, float]:
        """
        Update turbine stage system state
        
        Args:
            inlet_pressure: Turbine inlet pressure (MPa)
            inlet_temperature: Turbine inlet temperature (°C)
            inlet_flow: Turbine inlet flow (kg/s)
            load_demand: Load demand (0-1)
            extraction_demands: Extraction flow demands
            dt: Time step (hours)
            
        Returns:
            Dictionary with system performance results
        """
        # Update control logic
        control_commands = self.control_logic.update_control_logic(
            self.stages, inlet_flow, load_demand, extraction_demands, dt
        )
        
        # Calculate stage-by-stage expansion
        expansion_results = self.calculate_stage_by_stage_expansion(
            inlet_pressure, inlet_temperature, inlet_flow, extraction_demands
        )
        
        # Update individual stages with degradation
        for stage_id, stage in self.stages.items():
            stage.update_degradation(dt)
        
        # Update system state
        self.total_power_output = expansion_results['total_power']
        self.total_steam_flow = inlet_flow
        self.total_extraction_flow = expansion_results['total_extraction']
        
        # Calculate overall efficiency
        if inlet_flow > 0:
            steam_enthalpy_in = self.stages[list(self.stages.keys())[0]]._steam_enthalpy(inlet_temperature, inlet_pressure)
            outlet_conditions = expansion_results['outlet_conditions']
            outlet_enthalpy = self.stages[list(self.stages.keys())[-1]]._steam_enthalpy(
                outlet_conditions['temperature'], outlet_conditions['pressure']
            )
            cycle_efficiency = (steam_enthalpy_in - outlet_enthalpy) / steam_enthalpy_in
            self.overall_efficiency = cycle_efficiency
        else:
            self.overall_efficiency = 0.0
        
        # Update operating hours
        self.operating_hours += dt
        
        return {
            # System performance
            'total_power_output': self.total_power_output,
            'total_steam_flow': self.total_steam_flow,
            'total_extraction_flow': self.total_extraction_flow,
            'overall_efficiency': self.overall_efficiency,
            'system_efficiency': self.system_efficiency,
            
            # Stage results
            'stage_results': expansion_results['stages'],
            'outlet_conditions': expansion_results['outlet_conditions'],
            
            # Control system
            'control_commands': control_commands,
            'load_demand': load_demand,
            
            # Operating time
            'operating_hours': self.operating_hours
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'stage_system_total_power': self.total_power_output,
            'stage_system_steam_flow': self.total_steam_flow,
            'stage_system_extraction_flow': self.total_extraction_flow,
            'stage_system_efficiency': self.overall_efficiency,
            'stage_system_operating_hours': self.operating_hours
        }
        
        # Add individual stage states
        for stage in self.stages.values():
            state_dict.update(stage.get_state_dict())
        
        return state_dict
    
    def reset(self) -> None:
        """Reset stage system to initial conditions"""
        self.total_power_output = 0.0
        self.total_steam_flow = 0.0
        self.overall_efficiency = 0.0
        self.total_extraction_flow = 0.0
        self.system_efficiency = 1.0
        self.operating_hours = 0.0
        
        # Reset individual stages
        for stage in self.stages.values():
            stage.reset()
        
        # Reset control logic
        self.control_logic.total_load_demand = 1.0
        self.control_logic.extraction_demands = {}
        self.control_logic.stage_loading_targets = {}


# Example usage and testing
if __name__ == "__main__":
    # Create stage system with default configuration
    stage_system = TurbineStageSystem()
    
    print("Turbine Stage System Model - Parameter Validation")
    print("=" * 55)
    print(f"System ID: {stage_system.config.system_id}")
    print(f"Number of Stages: {len(stage_system.stages)}")
    print(f"HP Stages: {stage_system.config.hp_stage_count}")
    print(f"LP Stages: {stage_system.config.lp_stage_count}")
    print(f"Control Strategy: {stage_system.config.stage_loading_strategy}")
    print()
    
    # Test stage system operation
    extraction_demands = {
        'HP-3': 25.0,  # kg/s extraction from HP-3
        'HP-4': 30.0,  # kg/s extraction from HP-4
        'LP-1': 20.0,  # kg/s extraction from LP-1
    }
    
    for hour in range(24):  # 24 hours
        result = stage_system.update_state(
            inlet_pressure=6.895,       # MPa inlet pressure
            inlet_temperature=285.8,    # °C inlet temperature
            inlet_flow=1665.0,          # kg/s inlet flow
            load_demand=1.0,            # 100% load
            extraction_demands=extraction_demands,
            dt=1.0                      # 1 hour time step
        )
        
        if hour % 6 == 0:  # Print every 6 hours
            print(f"Hour {hour}:")
            print(f"  Total Power: {result['total_power_output']:.1f} MW")
            print(f"  Overall Efficiency: {result['overall_efficiency']:.3f}")
            print(f"  Total Extraction: {result['total_extraction_flow']:.1f} kg/s")
            
            # Show some individual stage results
            for stage_id in ['HP-1', 'HP-4', 'LP-1', 'LP-6']:
                if stage_id in result['stage_results']:
                    stage_result = result['stage_results'][stage_id]
                    print(f"    {stage_id}: {stage_result['power_output']:.1f} MW, "
                          f"Eff: {stage_result['stage_efficiency']:.3f}, "
                          f"Ext: {stage_result['extraction_flow']:.1f} kg/s")
            print()
