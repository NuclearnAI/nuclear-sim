"""
Unified Water Chemistry Analysis Module

This module provides a centralized water chemistry analysis system that serves
both TSP fouling models and feedwater pump degradation systems, eliminating
modeling overlap and ensuring consistent water quality parameters across
all secondary system components.

Key Features:
1. Unified water chemistry parameter tracking
2. Consistent chemistry effects calculations
3. Shared degradation rate modeling
4. Integrated chemical treatment system
5. Auto-registered state management
6. Centralized monitoring and diagnostics

Design Philosophy:
- Single source of truth for water chemistry
- Consistent parameter definitions across systems
- Shared calculation methods for temperature and chemistry effects
- Unified maintenance and cleaning effectiveness models
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import warnings

# Handle imports that may not be available during standalone testing
try:
    from simulator.state import auto_register
    from .component_descriptions import SECONDARY_SYSTEM_DESCRIPTIONS
    SIMULATOR_AVAILABLE = True
except ImportError:
    # Fallback for standalone operation
    SIMULATOR_AVAILABLE = False
    
    def auto_register(*args, **kwargs):
        def decorator(cls):
            return cls
        return decorator
    
    SECONDARY_SYSTEM_DESCRIPTIONS = {"water_chemistry": "Water Chemistry System"}

# Import chemistry flow interfaces for integration
try:
    from .chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies
    CHEMISTRY_INTEGRATION_AVAILABLE = True
except ImportError:
    # Fallback for standalone operation
    CHEMISTRY_INTEGRATION_AVAILABLE = False
    
    class ChemistryFlowProvider:
        def get_chemistry_flows(self): return {}
        def get_chemistry_state(self): return {}
        def update_chemistry_effects(self, chemistry_state): pass
    
    class ChemicalSpecies:
        PH = "ph"
        IRON = "iron"
        COPPER = "copper"
        SILICA = "silica"
        AMMONIA = "ammonia"
        MORPHOLINE = "morpholine"

warnings.filterwarnings("ignore")


@dataclass
class WaterChemistryConfig:
    """
    Configuration for unified water chemistry analysis
    
    This configuration provides parameters for all secondary system
    water chemistry modeling needs.
    """
    
    # === PRIMARY CHEMISTRY PARAMETERS ===
    # Core parameters tracked across all systems
    
    # pH and alkalinity
    design_ph: float = 9.2                          # Design pH (PWR secondary optimal)
    ph_min: float = 8.8                             # Minimum allowable pH
    ph_max: float = 9.6                             # Maximum allowable pH
    ph_optimal: float = 9.2                         # Optimal pH for minimal fouling
    
    # Dissolved species (ppm) - TSP fouling parameters
    design_iron_concentration: float = 0.1          # ppm Fe (typical PWR secondary)
    design_copper_concentration: float = 0.05       # ppm Cu (typical PWR secondary)
    design_silica_concentration: float = 20.0       # ppm SiO2 (typical PWR secondary)
    design_dissolved_oxygen: float = 0.005          # ppm O2 (PWR secondary - very low)
    
    # Traditional water quality parameters - feedwater pump parameters
    design_hardness: float = 150.0                  # mg/L as CaCO3
    design_tds: float = 500.0                       # mg/L total dissolved solids
    design_chloride: float = 50.0                   # mg/L chloride
    design_alkalinity: float = 120.0                # mg/L as CaCO3
    
    # === CHEMISTRY EFFECT FACTORS ===
    # Unified factors for degradation calculations
    
    # TSP fouling factors (from original TSP model)
    iron_fouling_factor: float = 1.5                # Multiplier per ppm Fe for magnetite
    copper_fouling_factor: float = 2.0              # Multiplier per ppm Cu for copper deposits
    silica_fouling_factor: float = 1.8              # Multiplier per ppm SiO2 for silica deposits
    
    # Pump degradation factors
    iron_wear_factor: float = 1.2                   # Iron effect on impeller wear
    copper_corrosion_factor: float = 1.8            # Copper effect on corrosion rates
    chloride_aggressiveness_factor: float = 2.0     # Chloride effect on corrosion
    hardness_scaling_factor: float = 1.5            # Hardness effect on scaling
    
    # Shared temperature effects
    temperature_activation_energy: float = 45000.0  # J/mol (Arrhenius activation energy)
    reference_temperature: float = 300.0            # °C reference temperature
    
    # === CHEMICAL TREATMENT PARAMETERS ===
    # Unified treatment system configuration
    
    # Chemical dose rates
    chlorine_dose_rate: float = 1.0                 # mg/L target free chlorine
    antiscalant_dose_rate: float = 5.0              # mg/L antiscalant
    corrosion_inhibitor_dose: float = 10.0          # mg/L corrosion inhibitor
    biocide_dose_rate: float = 0.0                  # mg/L biocide (intermittent)
    
    # Treatment effectiveness
    treatment_efficiency: float = 0.95              # Overall treatment system efficiency
    chemical_decay_rate: float = 0.1                # 1/hour chlorine decay rate
    
    # System operation parameters
    blowdown_rate: float = 0.02                     # Fraction of flow as blowdown
    makeup_rate: float = 0.05                       # Fraction of flow as makeup
    concentration_factor_max: float = 5.0           # Maximum concentration factor


class DegradationCalculator:
    """
    Unified degradation rate calculations shared by both TSP fouling and pump wear models
    
    This class provides common physics calculations to ensure consistency
    between different degradation models.
    """
    
    @staticmethod
    def calculate_temperature_factor(temperature: float, 
                                   activation_energy: float = 45000.0,
                                   reference_temp: float = 300.0) -> float:
        """
        Calculate Arrhenius temperature relationship (shared by both systems)
        
        Args:
            temperature: Current temperature (°C)
            activation_energy: Activation energy (J/mol)
            reference_temp: Reference temperature (°C)
            
        Returns:
            Temperature factor relative to reference
        """
        temp_kelvin = temperature + 273.15
        ref_temp_kelvin = reference_temp + 273.15
        
        factor = np.exp(-activation_energy / (8.314 * temp_kelvin))
        ref_factor = np.exp(-activation_energy / (8.314 * ref_temp_kelvin))
        
        return factor / ref_factor
    
    @staticmethod
    def calculate_ph_factor(ph: float, optimal_ph: float = 9.2) -> float:
        """
        Calculate pH effect on degradation (shared calculation)
        
        Args:
            ph: Current pH
            optimal_ph: Optimal pH for minimal degradation
            
        Returns:
            pH factor (1.0 = optimal, >1.0 = increased degradation)
        """
        return 1.0 + 0.5 * abs(ph - optimal_ph)
    
    @staticmethod
    def calculate_chemistry_multiplier(species_concentration: float, 
                                     base_factor: float) -> float:
        """
        Generic chemistry concentration effect
        
        Args:
            species_concentration: Concentration of chemical species
            base_factor: Base multiplication factor per unit concentration
            
        Returns:
            Chemistry multiplier
        """
        return 1.0 + species_concentration * base_factor
    
    @staticmethod
    def calculate_flow_velocity_factor(velocity: float, 
                                     reference_velocity: float = 3.0,
                                     exponent: float = 0.5) -> float:
        """
        Calculate flow velocity effect on mass transfer and degradation
        
        Args:
            velocity: Current flow velocity (m/s)
            reference_velocity: Reference velocity (m/s)
            exponent: Velocity exponent
            
        Returns:
            Velocity factor
        """
        velocity_ratio = velocity / reference_velocity
        return np.clip(velocity_ratio ** exponent, 0.5, 2.0)


@auto_register("SECONDARY", "water_chemistry", allow_no_id=True,
               description=SECONDARY_SYSTEM_DESCRIPTIONS["water_chemistry"])
class WaterChemistry(ChemistryFlowProvider):
    """
    Unified water chemistry analysis system
    
    This system provides a single source of truth for all water chemistry
    parameters used by TSP fouling models, feedwater pump degradation,
    and other secondary system components.
    """
    
    def __init__(self, config: Optional[WaterChemistryConfig] = None):
        """Initialize unified water chemistry system"""
        self.config = config if config is not None else WaterChemistryConfig()
        
        # === CORE MEASURED PARAMETERS ===
        # Primary chemistry parameters (directly measured or calculated)
        self.ph = self.config.design_ph
        self.iron_concentration = self.config.design_iron_concentration      # ppm Fe
        self.copper_concentration = self.config.design_copper_concentration  # ppm Cu
        self.silica_concentration = self.config.design_silica_concentration  # ppm SiO2
        self.dissolved_oxygen = self.config.design_dissolved_oxygen          # ppm O2
        
        # Traditional water quality parameters
        self.hardness = self.config.design_hardness                          # mg/L CaCO3
        self.total_dissolved_solids = self.config.design_tds                 # mg/L
        self.chloride = self.config.design_chloride                          # mg/L
        self.alkalinity = self.config.design_alkalinity                      # mg/L CaCO3
        
        # === CHEMICAL TREATMENT PARAMETERS ===
        # Treatment chemical concentrations
        self.chlorine_residual = 0.5                                         # mg/L free chlorine
        self.antiscalant_concentration = self.config.antiscalant_dose_rate   # mg/L
        self.corrosion_inhibitor_level = self.config.corrosion_inhibitor_dose # mg/L
        self.biocide_concentration = 0.0                                     # mg/L (intermittent)
        
        # === CALCULATED COMPOSITE PARAMETERS ===
        # Derived parameters for system-specific use
        self.water_aggressiveness = 1.0                                      # Composite aggressiveness factor
        self.particle_content = 1.0                                          # Derived particle content factor
        self.scaling_tendency = 0.0                                          # Langelier Saturation Index
        self.corrosion_tendency = 7.0                                        # Ryznar Stability Index
        
        # === SYSTEM OPERATION PARAMETERS ===
        # System-level parameters
        self.concentration_factor = 1.0                                      # Concentration due to evaporation
        self.treatment_efficiency = self.config.treatment_efficiency         # Overall treatment effectiveness
        self.blowdown_rate = self.config.blowdown_rate                      # Current blowdown rate
        
        # === PERFORMANCE TRACKING ===
        # System performance and history
        self.operating_hours = 0.0                                           # Total operating time
        self.last_treatment_time = 0.0                                       # Time since last treatment
        self.chemistry_stability_factor = 1.0                               # Chemistry stability indicator
        
        # Initialize degradation calculator
        self.degradation_calc = DegradationCalculator()
        
        # Calculate initial composite parameters
        self._calculate_composite_parameters()
    
    def _calculate_composite_parameters(self):
        """Calculate derived and composite chemistry parameters"""
        
        # === WATER AGGRESSIVENESS CALCULATION ===
        # Composite factor for pump degradation modeling
        iron_effect = self.iron_concentration * 0.5
        chloride_effect = self.chloride / 100.0
        ph_effect = abs(self.ph - 7.0) * 0.2
        hardness_effect = max(0.0, (self.hardness - 150.0) / 150.0) * 0.3
        
        self.water_aggressiveness = 1.0 + iron_effect + chloride_effect + ph_effect + hardness_effect
        self.water_aggressiveness = np.clip(self.water_aggressiveness, 0.5, 3.0)
        
        # === PARTICLE CONTENT CALCULATION ===
        # Derived from TDS and chemistry for abrasive wear
        tds_factor = self.total_dissolved_solids / 500.0
        iron_particle_factor = self.iron_concentration * 2.0  # Iron forms particles
        silica_particle_factor = self.silica_concentration / 20.0  # Silica particles
        
        self.particle_content = 1.0 + (tds_factor + iron_particle_factor + silica_particle_factor) * 0.1
        self.particle_content = np.clip(self.particle_content, 0.5, 2.0)
        
        # === SCALING AND CORROSION INDICES ===
        # Langelier Saturation Index (simplified calculation)
        temp_factor = 25.0  # Assume 25°C average for calculation
        A = (np.log10(self.total_dissolved_solids) - 1) / 10
        B = -13.12 * np.log10(temp_factor + 273) + 34.55
        C = np.log10(self.hardness) - 0.4
        D = np.log10(self.alkalinity)
        
        ph_saturation = (9.3 + A + B) - (C + D)
        self.scaling_tendency = self.ph - ph_saturation  # LSI
        
        # Ryznar Stability Index
        self.corrosion_tendency = 2 * ph_saturation - self.ph  # RSI
        
        # === CHEMISTRY STABILITY FACTOR ===
        # Overall indicator of chemistry stability
        ph_stability = 1.0 - abs(self.ph - self.config.ph_optimal) / 2.0
        treatment_stability = self.treatment_efficiency
        concentration_stability = 1.0 - abs(self.concentration_factor - 2.0) / 3.0
        
        self.chemistry_stability_factor = (ph_stability + treatment_stability + concentration_stability) / 3.0
        self.chemistry_stability_factor = np.clip(self.chemistry_stability_factor, 0.1, 1.0)
    
    def update_chemistry(self, 
                        system_conditions: Dict[str, Any],
                        dt: float) -> Dict[str, float]:
        """
        Update unified water chemistry state
        
        Args:
            system_conditions: System operating conditions
            dt: Time step (hours)
            
        Returns:
            Dictionary with chemistry update results
        """
        # Convert dt to hours based on the magnitude
        if dt > 100:
            # dt is in seconds
            dt_hours = dt / 3600.0
        elif dt > 1:
            # dt is likely in minutes (typical range 1-60)
            dt_hours = dt / 60.0
        else:
            # dt is already in hours
            dt_hours = dt
        
        # Update operating time
        self.operating_hours += dt_hours
        self.last_treatment_time += dt_hours
        
        # === APPLY EXTERNAL CHEMISTRY EFFECTS FIRST ===
        # This ensures pH control effects are applied before makeup water dilution
        if hasattr(self, '_pending_chemistry_effects'):
            for effect_name, effect_data in self._pending_chemistry_effects.items():
                if effect_name == 'ph_control':
                    self._apply_ph_control_effects(effect_data)
                elif effect_name == 'chemical_additions':
                    self._apply_chemical_additions(effect_data)
                elif effect_name == 'system_feedback':
                    self._apply_system_feedback(effect_data)
            # Clear pending effects
            self._pending_chemistry_effects = {}
        
        # === UPDATE FROM MAKEUP WATER ===
        makeup_water_quality = system_conditions.get('makeup_water_quality', {})
        if makeup_water_quality:
            self._update_from_makeup_water(makeup_water_quality, dt_hours)
        
        # === UPDATE FROM SYSTEM CONDITIONS ===
        # Concentration effects from evaporation and blowdown
        current_blowdown = system_conditions.get('blowdown_rate', self.config.blowdown_rate)
        evaporation_rate = 0.01  # Typical evaporation rate
        
        self.concentration_factor = 1.0 / (current_blowdown + evaporation_rate)
        self.concentration_factor = min(self.concentration_factor, self.config.concentration_factor_max)
        
        # Update concentrated species
        if self.concentration_factor > 1.1:  # Only if significant concentration
            concentration_increase = (self.concentration_factor - 1.0) * 0.1 * dt_hours
            self.total_dissolved_solids += concentration_increase * 50.0
            self.hardness += concentration_increase * 10.0
            self.chloride += concentration_increase * 5.0
        
        # === UPDATE CHEMICAL TREATMENT ===
        self._update_chemical_treatment(system_conditions, dt_hours)
        
        # === CALCULATE COMPOSITE PARAMETERS ===
        self._calculate_composite_parameters()
        
        return self.get_state_dict()
    
    def _update_from_makeup_water(self, makeup_water: Dict[str, float], dt_hours: float):
        """Update chemistry from makeup water addition"""
        makeup_rate = self.config.makeup_rate
        
        # Blend with makeup water (simplified mixing)
        blend_factor = makeup_rate * dt_hours * 0.1  # Gradual blending
        blend_factor = min(blend_factor, 0.5)  # Limit blending rate
        
        # Update parameters toward makeup water values
        makeup_ph = makeup_water.get('ph', 8.8)  # More realistic for treated PWR makeup water
        makeup_hardness = makeup_water.get('hardness', 100.0)
        makeup_tds = makeup_water.get('tds', 300.0)
        makeup_chloride = makeup_water.get('chloride', 30.0)
        
        self.ph += (makeup_ph - self.ph) * blend_factor
        self.hardness += (makeup_hardness - self.hardness) * blend_factor
        self.total_dissolved_solids += (makeup_tds - self.total_dissolved_solids) * blend_factor
        self.chloride += (makeup_chloride - self.chloride) * blend_factor
        
        # Dissolved oxygen from makeup
        makeup_do = makeup_water.get('dissolved_oxygen', 8.0)
        self.dissolved_oxygen = makeup_do * 0.8  # Some loss due to heating
    
    def _update_chemical_treatment(self, system_conditions: Dict[str, float], dt_hours: float):
        """Update chemical treatment effectiveness and concentrations"""
        
        # Chemical dosing (simplified - assume continuous dosing)
        target_chlorine = self.config.chlorine_dose_rate
        target_antiscalant = self.config.antiscalant_dose_rate
        target_corrosion_inhibitor = self.config.corrosion_inhibitor_dose
        
        # Update toward target concentrations
        dose_rate = 0.5 * dt_hours  # Dosing response rate
        self.antiscalant_concentration += (target_antiscalant - self.antiscalant_concentration) * dose_rate
        self.corrosion_inhibitor_level += (target_corrosion_inhibitor - self.corrosion_inhibitor_level) * dose_rate
        
        # Chlorine decay and dosing
        chlorine_decay = self.config.chemical_decay_rate * dt_hours
        self.chlorine_residual *= np.exp(-chlorine_decay)
        self.chlorine_residual += (target_chlorine - self.chlorine_residual) * dose_rate
        
        # Update treatment efficiency based on chemical levels
        chlorine_effectiveness = 1.0 if self.chlorine_residual > 0.2 else 0.5
        antiscalant_effectiveness = 1.0 if self.antiscalant_concentration > 2.0 else 0.7
        corrosion_effectiveness = 1.0 if self.corrosion_inhibitor_level > 5.0 else 0.8
        
        self.treatment_efficiency = (chlorine_effectiveness * antiscalant_effectiveness * 
                                   corrosion_effectiveness * self.config.treatment_efficiency)
    
    def get_tsp_fouling_parameters(self) -> Dict[str, float]:
        """
        Get chemistry parameters formatted for TSP fouling model
        
        Returns:
            Dictionary with TSP fouling chemistry parameters
        """
        return {
            'iron_concentration': self.iron_concentration,
            'copper_concentration': self.copper_concentration,
            'silica_concentration': self.silica_concentration,
            'ph': self.ph,
            'dissolved_oxygen': self.dissolved_oxygen
        }
    
    def get_pump_degradation_parameters(self) -> Dict[str, float]:
        """
        Get chemistry parameters formatted for pump degradation models
        
        Returns:
            Dictionary with pump degradation chemistry parameters
        """
        return {
            'water_aggressiveness': self.water_aggressiveness,
            'ph': self.ph,
            'hardness': self.hardness,
            'chloride': self.chloride,
            'particle_content': self.particle_content,
            'scaling_tendency': self.scaling_tendency,
            'corrosion_tendency': self.corrosion_tendency
        }
    
    def perform_chemical_treatment(self, treatment_type: str = "standard", **kwargs) -> Dict[str, float]:
        """
        Perform chemical treatment or system cleaning
        
        Args:
            treatment_type: Type of treatment to perform
            **kwargs: Additional treatment parameters
            
        Returns:
            Dictionary with treatment results
        """
        results = {}
        
        if treatment_type == "chemical_cleaning":
            # Reset chemical concentrations to optimal levels
            self.chlorine_residual = self.config.chlorine_dose_rate
            self.antiscalant_concentration = self.config.antiscalant_dose_rate
            self.corrosion_inhibitor_level = self.config.corrosion_inhibitor_dose
            self.treatment_efficiency = self.config.treatment_efficiency
            results['chemical_cleaning'] = True
            
        elif treatment_type == "ph_adjustment":
            # Adjust pH toward optimal
            target_ph = kwargs.get('target_ph', self.config.ph_optimal)
            self.ph += (target_ph - self.ph) * 0.5
            results['ph_adjustment'] = True
            
        elif treatment_type == "blowdown_increase":
            # Reduce concentration through increased blowdown
            blowdown_factor = kwargs.get('blowdown_factor', 2.0)
            self.total_dissolved_solids /= blowdown_factor
            self.hardness /= blowdown_factor
            self.chloride /= blowdown_factor
            self.concentration_factor = 1.0
            results['blowdown_increase'] = True
            
        else:
            # Standard treatment - improve all parameters
            self.ph += (self.config.ph_optimal - self.ph) * 0.3
            self.chlorine_residual = self.config.chlorine_dose_rate
            self.antiscalant_concentration = self.config.antiscalant_dose_rate
            self.corrosion_inhibitor_level = self.config.corrosion_inhibitor_dose
            self.treatment_efficiency = self.config.treatment_efficiency
            results['standard_treatment'] = True
        
        # Reset treatment time
        self.last_treatment_time = 0.0
        
        # Recalculate composite parameters
        self._calculate_composite_parameters()
        
        return results
    
    def get_state_dict(self) -> Dict[str, float]:
        """
        Get current state as dictionary for logging/monitoring
        Consistent with other component naming patterns
        
        Returns:
            Dictionary with all chemistry parameters using water_chemistry_ prefix
        """
        return {
            # Raw measured parameters (for TSP fouling)
            'water_chemistry_iron_concentration': self.iron_concentration,
            'water_chemistry_copper_concentration': self.copper_concentration,
            'water_chemistry_silica_concentration': self.silica_concentration,
            'water_chemistry_ph': self.ph,
            'water_chemistry_dissolved_oxygen': self.dissolved_oxygen,
            
            # Traditional water quality (for feedwater pumps)
            'water_chemistry_hardness': self.hardness,
            'water_chemistry_chloride': self.chloride,
            'water_chemistry_tds': self.total_dissolved_solids,
            'water_chemistry_alkalinity': self.alkalinity,
            
            # Calculated composites (for pump degradation)
            'water_chemistry_aggressiveness': self.water_aggressiveness,
            'water_chemistry_particle_content': self.particle_content,
            
            # Scaling/corrosion indices
            'water_chemistry_scaling_tendency': self.scaling_tendency,
            'water_chemistry_corrosion_tendency': self.corrosion_tendency,
            
            # Treatment effectiveness
            'water_chemistry_treatment_efficiency': self.treatment_efficiency,
            'water_chemistry_chlorine_residual': self.chlorine_residual,
            'water_chemistry_antiscalant': self.antiscalant_concentration,
            'water_chemistry_corrosion_inhibitor': self.corrosion_inhibitor_level,
            
            # System operation
            'water_chemistry_concentration_factor': self.concentration_factor,
            'water_chemistry_blowdown_rate': self.blowdown_rate,
            'water_chemistry_stability_factor': self.chemistry_stability_factor,
            
            # Performance tracking
            'water_chemistry_operating_hours': self.operating_hours,
            'water_chemistry_time_since_treatment': self.last_treatment_time
        }
    
    def reset(self) -> None:
        """Reset water chemistry to initial design conditions"""
        # Reset core parameters to design values
        self.ph = self.config.design_ph
        self.iron_concentration = self.config.design_iron_concentration
        self.copper_concentration = self.config.design_copper_concentration
        self.silica_concentration = self.config.design_silica_concentration
        self.dissolved_oxygen = self.config.design_dissolved_oxygen
        
        # Reset traditional water quality parameters
        self.hardness = self.config.design_hardness
        self.total_dissolved_solids = self.config.design_tds
        self.chloride = self.config.design_chloride
        self.alkalinity = self.config.design_alkalinity
        
        # Reset chemical treatment parameters
        self.chlorine_residual = 0.5
        self.antiscalant_concentration = self.config.antiscalant_dose_rate
        self.corrosion_inhibitor_level = self.config.corrosion_inhibitor_dose
        self.biocide_concentration = 0.0
        
        # Reset calculated parameters
        self.water_aggressiveness = 1.0
        self.particle_content = 1.0
        self.scaling_tendency = 0.0
        self.corrosion_tendency = 7.0
        
        # Reset system operation parameters
        self.concentration_factor = 1.0
        self.treatment_efficiency = self.config.treatment_efficiency
        self.blowdown_rate = self.config.blowdown_rate
        
        # Reset performance tracking
        self.operating_hours = 0.0
        self.last_treatment_time = 0.0
        self.chemistry_stability_factor = 1.0
        
        # Recalculate composite parameters
        self._calculate_composite_parameters()
    
    # === CHEMISTRY FLOW PROVIDER INTERFACE METHODS ===
    # These methods enable integration with chemistry_flow_tracker
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data
        """
        # Handle both real ChemicalSpecies enum and fallback string version
        if CHEMISTRY_INTEGRATION_AVAILABLE:
            ph_key = ChemicalSpecies.PH.value
            iron_key = ChemicalSpecies.IRON.value
            copper_key = ChemicalSpecies.COPPER.value
            silica_key = ChemicalSpecies.SILICA.value
        else:
            ph_key = ChemicalSpecies.PH
            iron_key = ChemicalSpecies.IRON
            copper_key = ChemicalSpecies.COPPER
            silica_key = ChemicalSpecies.SILICA
        
        return {
            'system_chemistry': {
                ph_key: self.ph,
                iron_key: self.iron_concentration,
                copper_key: self.copper_concentration,
                silica_key: self.silica_concentration,
                'hardness': self.hardness,
                'chloride': self.chloride,
                'tds': self.total_dissolved_solids
            },
            'treatment_chemistry': {
                'chlorine_residual': self.chlorine_residual,
                'antiscalant': self.antiscalant_concentration,
                'corrosion_inhibitor': self.corrosion_inhibitor_level
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state for chemistry flow tracker
        
        Returns:
            Dictionary with current chemistry concentrations
        """
        return self.get_state_dict()
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update water chemistry based on external chemistry effects
        
        This method stores effects to be applied during the next update_chemistry call
        to ensure proper order of operations (pH control before makeup water dilution).
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Initialize pending effects storage if not exists
        if not hasattr(self, '_pending_chemistry_effects'):
            self._pending_chemistry_effects = {}
        
        # Store effects for later application during update_chemistry
        if any(key in chemistry_state for key in ['ph_setpoint', 'ammonia_dose_rate', 'morpholine_dose_rate']):
            self._pending_chemistry_effects['ph_control'] = chemistry_state.copy()
        
        if 'chemical_additions' in chemistry_state:
            self._pending_chemistry_effects['chemical_additions'] = chemistry_state['chemical_additions']
        
        if 'system_chemistry_feedback' in chemistry_state:
            self._pending_chemistry_effects['system_feedback'] = chemistry_state['system_chemistry_feedback']
    
    def _apply_ph_control_effects(self, chemistry_state: Dict[str, float]) -> None:
        """Apply effects from pH control system"""
        # Get pH control outputs
        ph_setpoint = chemistry_state.get('ph_setpoint', self.ph)
        ammonia_dose = chemistry_state.get('ammonia_dose_rate', 0.0)  # kg/hr
        morpholine_dose = chemistry_state.get('morpholine_dose_rate', 0.0)  # kg/hr
        
        # Calculate realistic pH response based on system volume and chemistry
        # Typical PWR secondary system volume: ~1000 m³
        system_volume_m3 = 1000.0  # m³
        water_density = 1000.0  # kg/m³
        
        # Apply chemical dosing effects on pH with realistic response
        if ammonia_dose > 0:
            # Ammonia raises pH - calculate concentration increase
            # Convert kg/hr to ppm concentration increase
            concentration_increase_ppm = (ammonia_dose / 3600.0) / (system_volume_m3 * water_density) * 1e6
            
            # Ammonia is very effective at raising pH (strong base)
            # pH increase = log10(base_concentration / acid_concentration)
            # Simplified: each ppm of ammonia raises pH by ~0.1 units
            ph_increase = concentration_increase_ppm * 0.1
            self.ph = min(self.ph + ph_increase, self.config.ph_max)
        
        if morpholine_dose > 0:
            # Morpholine raises pH (less effective than ammonia)
            concentration_increase_ppm = (morpholine_dose / 3600.0) / (system_volume_m3 * water_density) * 1e6
            # Morpholine is less effective than ammonia
            ph_increase = concentration_increase_ppm * 0.05
            self.ph = min(self.ph + ph_increase, self.config.ph_max)
        
        # Enhanced approach to setpoint (control system effect)
        if abs(self.ph - ph_setpoint) > 0.01:
            # More responsive approach rate for active control
            approach_rate = 0.3  # 30% approach per update for better control response
            self.ph += (ph_setpoint - self.ph) * approach_rate
    
    def _apply_chemical_additions(self, chemical_additions: Dict[str, float]) -> None:
        """Apply chemical additions from external systems"""
        # Handle both enum and string keys
        if CHEMISTRY_INTEGRATION_AVAILABLE:
            ammonia_key = ChemicalSpecies.AMMONIA.value
            morpholine_key = ChemicalSpecies.MORPHOLINE.value
        else:
            ammonia_key = ChemicalSpecies.AMMONIA
            morpholine_key = ChemicalSpecies.MORPHOLINE
        
        # Update chemical concentrations
        if ammonia_key in chemical_additions:
            # Convert kg/s to ppm concentration increase
            ammonia_rate = chemical_additions[ammonia_key]  # kg/s
            concentration_increase = ammonia_rate * 3600.0 * 0.1  # Simplified conversion
            self.antiscalant_concentration += concentration_increase
        
        if morpholine_key in chemical_additions:
            morpholine_rate = chemical_additions[morpholine_key]  # kg/s
            concentration_increase = morpholine_rate * 3600.0 * 0.05
            self.corrosion_inhibitor_level += concentration_increase
    
    def _apply_system_feedback(self, feedback: Dict[str, float]) -> None:
        """Apply system-wide chemistry feedback"""
        # Update from system-wide chemistry balance
        if 'concentration_factor' in feedback:
            self.concentration_factor = feedback['concentration_factor']
        
        if 'blowdown_rate' in feedback:
            self.blowdown_rate = feedback['blowdown_rate']
        
        # Update treatment efficiency based on system performance
        if 'treatment_effectiveness' in feedback:
            self.treatment_efficiency = feedback['treatment_effectiveness']


# Example usage and testing
if __name__ == "__main__":
    print("Unified Water Chemistry System - Test")
    print("=" * 50)
    
    # Create water chemistry system
    config = WaterChemistryConfig()
    water_chemistry = WaterChemistry(config)
    
    print(f"Water Chemistry System Configuration:")
    print(f"  Design pH: {config.design_ph}")
    print(f"  Design pH: {config.design_ph}")
    print(f"  Design Iron: {config.design_iron_concentration} ppm")
    print(f"  Design Copper: {config.design_copper_concentration} ppm")
    print(f"  Design Silica: {config.design_silica_concentration} ppm")
    print(f"  Design Hardness: {config.design_hardness} mg/L")
    print()
    
    # Test chemistry parameter provision
    print("Chemistry Parameter Provision Test:")
    
    # Test TSP fouling parameters
    tsp_params = water_chemistry.get_tsp_fouling_parameters()
    print("TSP Fouling Parameters:")
    for key, value in tsp_params.items():
        print(f"  {key}: {value}")
    print()
    
    # Test pump degradation parameters
    pump_params = water_chemistry.get_pump_degradation_parameters()
    print("Pump Degradation Parameters:")
    for key, value in pump_params.items():
        print(f"  {key}: {value}")
    print()
    
    # Test state dictionary
    state_dict = water_chemistry.get_state_dict()
    print("State Dictionary (first 10 parameters):")
    for i, (key, value) in enumerate(state_dict.items()):
        if i < 10:
            print(f"  {key}: {value}")
        else:
            break
    print(f"  ... and {len(state_dict) - 10} more parameters")
    print()
    
    # Test chemistry update
    print("Chemistry Update Test:")
    print(f"{'Time':<6} {'pH':<6} {'Iron':<8} {'Aggressiveness':<14} {'Treatment Eff':<12}")
    print("-" * 50)
    
    system_conditions = {
        'makeup_water_quality': {
            'ph': 7.2,
            'hardness': 100.0,
            'tds': 300.0,
            'chloride': 30.0,
            'dissolved_oxygen': 8.0
        },
        'blowdown_rate': 0.02
    }
    
    for hour in range(0, 25, 4):  # Every 4 hours for 24 hours
        result = water_chemistry.update_chemistry(system_conditions, 1.0)
        
        print(f"{hour:<6} {result['water_chemistry_ph']:<6.2f} "
              f"{result['water_chemistry_iron_concentration']:<8.3f} "
              f"{result['water_chemistry_aggressiveness']:<14.3f} "
              f"{result['water_chemistry_treatment_efficiency']:<12.3f}")
    
    print()
    print("Unified water chemistry system ready for integration!")
