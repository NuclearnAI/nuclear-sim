"""
Tube Support Plate (TSP) Fouling Model

This module implements comprehensive TSP fouling physics for PWR steam generators,
including deposit accumulation, flow restriction, heat transfer degradation, and
shutdown protection systems.

Key Features:
1. Multi-component deposit formation (magnetite, copper, silica, biologics)
2. Flow restriction and pressure drop calculations
3. Heat transfer degradation modeling
4. Cleaning effectiveness simulation
5. Steam generator lifecycle and replacement logic
6. Automatic shutdown protection systems

Physical Basis:
- Deposit formation kinetics based on water chemistry
- Flow restriction using orifice flow equations
- Heat transfer degradation from reduced mixing
- Operational replacement decision modeling

References:
- EPRI Steam Generator Reference Book
- NRC Generic Letter 95-03 (Steam Generator Tube Integrity)
- NUREG-1477: Steam Generator Tube Failures
- Industry experience from Millstone, Indian Point, and other PWR plants
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import warnings

# Import state management interfaces
from simulator.state import auto_register

# Import unified water chemistry system
from ..water_chemistry import WaterChemistry, WaterChemistryConfig

# Import chemistry flow interfaces
from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies

# Import component descriptions
from ..component_descriptions import STEAM_GENERATOR_COMPONENT_DESCRIPTIONS

warnings.filterwarnings("ignore")


class FoulingStage(Enum):
    """Steam generator fouling severity stages"""
    NORMAL = "normal"                    # 0-40% fouling
    SIGNIFICANT = "significant"          # 40-70% fouling  
    SEVERE = "severe"                   # 70-85% fouling
    CRITICAL = "critical"               # 85%+ fouling - shutdown required


class ShutdownReason(Enum):
    """Reasons for steam generator shutdown due to TSP fouling"""
    CRITICAL_FOULING = "critical_tsp_fouling"
    HEAT_TRANSFER_DEGRADATION = "excessive_heat_transfer_loss"
    PRESSURE_DROP_EXCESSIVE = "excessive_pressure_drop"
    FLOW_MALDISTRIBUTION = "severe_flow_maldistribution"
    TUBE_INTEGRITY_CONCERN = "tube_integrity_risk"
    DESIGN_LIFE_EXCEEDED = "design_life_exceeded"


@dataclass
class TSPFoulingConfig:
    """
    Configuration for TSP fouling model based on PWR operating experience
    
    References:
    - EPRI TR-102134: Steam Generator Degradation Specific Management
    - Industry fouling rate data from operating PWRs
    """
    
    # Identification
    fouling_model_id: str = "TSP-FOULING-001"      # Unique identifier for this TSP fouling instance
    
    # Physical TSP parameters
    tsp_count: int = 7                              # Number of TSP elevations (typical PWR)
    tsp_hole_diameter: float = 0.023                # m (23mm typical hole diameter)
    tsp_thickness: float = 0.025                    # m (25mm typical TSP thickness)
    tsp_open_area_fraction: float = 0.06            # 6% open area (typical PWR design)
    
    # Deposit formation rates (mg/cm²/year - based on industry data)
    magnetite_base_rate: float = 2.5               # Base magnetite deposition rate
    copper_base_rate: float = 0.8                  # Base copper deposition rate  
    silica_base_rate: float = 1.2                  # Base silica deposition rate
    biological_base_rate: float = 0.5              # Base biological fouling rate
    
    # Water chemistry effects on fouling rates
    iron_concentration_factor: float = 1.5          # Multiplier per ppm Fe
    copper_concentration_factor: float = 2.0        # Multiplier per ppm Cu
    silica_concentration_factor: float = 1.8        # Multiplier per ppm SiO2
    ph_optimal: float = 9.2                        # Optimal pH for minimal fouling
    temperature_activation_energy: float = 45000.0  # J/mol (Arrhenius activation energy)
    
    # Flow and heat transfer impact parameters
    flow_restriction_exponent: float = 2.0          # Flow restriction vs. fouling relationship
    heat_transfer_degradation_factor: float = 0.6   # HTC reduction factor
    mixing_degradation_exponent: float = 1.5        # Mixing reduction vs. fouling
    
    # Cleaning effectiveness parameters
    chemical_cleaning_effectiveness: float = 0.75    # 75% deposit removal
    mechanical_cleaning_effectiveness: float = 0.85  # 85% deposit removal
    
    # Lifecycle and replacement parameters
    design_life_years: float = 40.0                 # Design life (years)
    fouling_replacement_threshold: float = 0.80     # 80% fouling triggers replacement consideration
    
    # Shutdown protection thresholds
    fouling_trip_threshold: float = 0.85            # 85% fouling triggers automatic trip
    heat_transfer_trip_threshold: float = 0.60      # 60% HTC triggers trip
    pressure_drop_trip_threshold: float = 5.0       # 5x normal ΔP triggers trip
    flow_maldistribution_limit: float = 0.30        # 30% flow imbalance limit


@dataclass
class DepositState:
    """Current deposit state on TSP surfaces"""
    magnetite_thickness: List[float] = field(default_factory=lambda: [0.0] * 7)    # mm per TSP level
    copper_thickness: List[float] = field(default_factory=lambda: [0.0] * 7)       # mm per TSP level
    silica_thickness: List[float] = field(default_factory=lambda: [0.0] * 7)       # mm per TSP level
    biological_thickness: List[float] = field(default_factory=lambda: [0.0] * 7)   # mm per TSP level
    
    def get_total_thickness(self, tsp_level: int) -> float:
        """Get total deposit thickness at specific TSP level"""
        return (self.magnetite_thickness[tsp_level] + 
                self.copper_thickness[tsp_level] + 
                self.silica_thickness[tsp_level] + 
                self.biological_thickness[tsp_level])
    
    def get_average_thickness(self) -> float:
        """Get average deposit thickness across all TSP levels"""
        total_thickness = 0.0
        for i in range(len(self.magnetite_thickness)):
            total_thickness += self.get_total_thickness(i)
        return total_thickness / len(self.magnetite_thickness)
    
    def get_maximum_thickness(self) -> float:
        """Get maximum deposit thickness across all TSP levels"""
        max_thickness = 0.0
        for i in range(len(self.magnetite_thickness)):
            thickness = self.get_total_thickness(i)
            if thickness > max_thickness:
                max_thickness = thickness
        return max_thickness


@auto_register("SECONDARY", "tsp_fouling", id_source="config.fouling_model_id",
               description=STEAM_GENERATOR_COMPONENT_DESCRIPTIONS['tsp_fouling_model'])
class TSPFoulingModel(ChemistryFlowProvider):
    """
    Comprehensive TSP fouling model for PWR steam generators
    
    This model simulates:
    1. Multi-component deposit formation on tube support plates
    2. Flow restriction and pressure drop increases
    3. Heat transfer degradation from reduced mixing
    4. Cleaning operations and effectiveness
    5. Steam generator lifecycle and replacement decisions
    6. Automatic shutdown protection systems
    
    Uses unified water chemistry system for consistent chemistry parameters.
    """
    
    def __init__(self, config: Optional[TSPFoulingConfig] = None, water_chemistry: Optional[WaterChemistry] = None):
        """Initialize TSP fouling model"""
        self.config = config if config is not None else TSPFoulingConfig()
        
        # Initialize or use provided unified water chemistry system
        if water_chemistry is not None:
            self.water_chemistry = water_chemistry
        else:
            # Create own instance if not provided (for standalone use)
            self.water_chemistry = WaterChemistry(WaterChemistryConfig())
        
        # Initialize deposit state
        self.deposits = DepositState()
        
        # Operating parameters
        self.operating_years = 0.0                  # Total operating years
        self.total_cleaning_cycles = 0              # Number of cleaning cycles performed
        self.last_cleaning_time = 0.0               # Years since last cleaning
        
        # Current fouling state
        self.fouling_fraction = 0.0                 # Overall fouling fraction (0-1)
        self.fouling_stage = FoulingStage.NORMAL    # Current fouling stage
        self.heat_transfer_degradation = 0.0        # Heat transfer coefficient reduction (0-1)
        self.pressure_drop_ratio = 1.0              # Pressure drop ratio (current/clean)
        self.flow_maldistribution = 0.0             # Flow maldistribution factor (0-1)
        
        # Performance tracking
        self.cumulative_power_loss = 0.0            # MWh lost due to fouling
        self.replacement_recommended = False        # Replacement recommendation flag
        
        # Shutdown protection state
        self.shutdown_required = False              # Immediate shutdown required
        self.shutdown_reasons = []                  # List of shutdown reasons
        self.protection_system_active = True       # Protection system status
        
    def calculate_deposit_formation_rates(self, 
                                        temperature: float,
                                        flow_velocity: float) -> Dict[str, List[float]]:
        """
        Calculate deposit formation rates for each TSP level using unified water chemistry
        
        Args:
            temperature: Average temperature (°C)
            flow_velocity: Average flow velocity (m/s)
            
        Returns:
            Dictionary with formation rates for each deposit type (mg/cm²/year)
        """
        # Get chemistry parameters from unified water chemistry system
        tsp_params = self.water_chemistry.get_tsp_fouling_parameters()
        iron_ppm = tsp_params['iron_concentration']
        copper_ppm = tsp_params['copper_concentration']
        silica_ppm = tsp_params['silica_concentration']
        ph = tsp_params['ph']
        dissolved_oxygen = tsp_params['dissolved_oxygen']
        
        # Temperature effect (Arrhenius relationship)
        temp_kelvin = temperature + 273.15
        temp_factor = np.exp(-self.config.temperature_activation_energy / (8.314 * temp_kelvin))
        temp_factor = temp_factor / np.exp(-self.config.temperature_activation_energy / (8.314 * 573.15))  # Normalize to 300°C
        
        # pH effect (optimal at pH 9.2 for PWR secondary chemistry)
        ph_factor = 1.0 + 0.5 * abs(ph - self.config.ph_optimal)
        
        # Flow velocity effect (higher velocity increases mass transfer)
        velocity_factor = (flow_velocity / 3.0) ** 0.5  # Normalize to 3 m/s typical velocity
        velocity_factor = np.clip(velocity_factor, 0.5, 2.0)
        
        # Calculate base formation rates with chemistry effects
        magnetite_rate = (self.config.magnetite_base_rate * 
                         (1.0 + iron_ppm * self.config.iron_concentration_factor) *
                         temp_factor * ph_factor * velocity_factor)
        
        copper_rate = (self.config.copper_base_rate * 
                      (1.0 + copper_ppm * self.config.copper_concentration_factor) *
                      temp_factor * velocity_factor)
        
        silica_rate = (self.config.silica_base_rate * 
                      (1.0 + silica_ppm / 100.0 * self.config.silica_concentration_factor) *
                      temp_factor * ph_factor)
        
        # Biological fouling (depends on dissolved oxygen and temperature)
        bio_temp_factor = 1.0 if temperature < 60 else np.exp(-(temperature - 60) / 20)  # Decreases above 60°C
        biological_rate = (self.config.biological_base_rate * 
                          (1.0 + dissolved_oxygen * 10.0) *  # Higher DO promotes biological growth
                          bio_temp_factor * velocity_factor)
        
        # TSP level distribution (higher fouling at lower elevations due to higher temperature)
        level_factors = []
        for level in range(self.config.tsp_count):
            # Higher fouling at bottom (hot end) of steam generator
            level_factor = 1.0 + 0.3 * (self.config.tsp_count - level - 1) / (self.config.tsp_count - 1)
            level_factors.append(level_factor)
        
        # Apply level distribution to formation rates
        formation_rates = {
            'magnetite': [magnetite_rate * factor for factor in level_factors],
            'copper': [copper_rate * factor for factor in level_factors],
            'silica': [silica_rate * factor for factor in level_factors],
            'biological': [biological_rate * factor for factor in level_factors]
        }
        
        return formation_rates
    
    def update_deposit_accumulation(self,
                                  formation_rates: Dict[str, List[float]],
                                  dt_years: float) -> None:
        """
        Update deposit accumulation on TSP surfaces
        
        Args:
            formation_rates: Formation rates for each deposit type (mg/cm²/year)
            dt_years: Time step (years)
        """
        # Convert formation rates to thickness increase (assuming deposit density)
        # Typical deposit densities: magnetite ~5.2 g/cm³, copper ~8.9 g/cm³, silica ~2.2 g/cm³, bio ~1.2 g/cm³
        magnetite_density = 5.2  # g/cm³
        copper_density = 8.9     # g/cm³
        silica_density = 2.2     # g/cm³
        bio_density = 1.2        # g/cm³
        
        for level in range(self.config.tsp_count):
            # Calculate thickness increase (mg/cm²/year → mm/year)
            magnetite_increase = (formation_rates['magnetite'][level] / 1000.0) / magnetite_density * 10.0  # mm/year
            copper_increase = (formation_rates['copper'][level] / 1000.0) / copper_density * 10.0          # mm/year
            silica_increase = (formation_rates['silica'][level] / 1000.0) / silica_density * 10.0          # mm/year
            bio_increase = (formation_rates['biological'][level] / 1000.0) / bio_density * 10.0            # mm/year
            
            # Update deposit thicknesses
            self.deposits.magnetite_thickness[level] += magnetite_increase * dt_years
            self.deposits.copper_thickness[level] += copper_increase * dt_years
            self.deposits.silica_thickness[level] += silica_increase * dt_years
            self.deposits.biological_thickness[level] += bio_increase * dt_years
            
            # Apply physical limits (deposits can't exceed TSP hole radius)
            max_thickness = self.config.tsp_hole_diameter / 2.0 * 1000.0 * 0.9  # 90% of hole radius in mm
            
            self.deposits.magnetite_thickness[level] = min(self.deposits.magnetite_thickness[level], max_thickness * 0.4)
            self.deposits.copper_thickness[level] = min(self.deposits.copper_thickness[level], max_thickness * 0.2)
            self.deposits.silica_thickness[level] = min(self.deposits.silica_thickness[level], max_thickness * 0.3)
            self.deposits.biological_thickness[level] = min(self.deposits.biological_thickness[level], max_thickness * 0.1)
    
    def calculate_flow_restriction(self) -> Tuple[float, float, List[float]]:
        """
        Calculate flow restriction and pressure drop from TSP fouling
        
        Returns:
            Tuple of (fouling_fraction, pressure_drop_ratio, level_restrictions)
        """
        level_restrictions = []
        total_restriction = 0.0
        
        for level in range(self.config.tsp_count):
            # Calculate effective hole diameter reduction
            total_thickness = self.deposits.get_total_thickness(level)  # mm
            hole_diameter_mm = self.config.tsp_hole_diameter * 1000.0   # Convert to mm
            
            # Effective diameter reduction (deposits on hole walls)
            effective_diameter = hole_diameter_mm - 2.0 * total_thickness
            effective_diameter = max(effective_diameter, hole_diameter_mm * 0.1)  # Minimum 10% open
            
            # Flow area reduction
            original_area = np.pi * (hole_diameter_mm / 2.0) ** 2
            effective_area = np.pi * (effective_diameter / 2.0) ** 2
            area_ratio = effective_area / original_area
            
            # Flow restriction (1 - area_ratio)
            restriction = 1.0 - area_ratio
            level_restrictions.append(restriction)
            total_restriction += restriction
        
        # Average fouling fraction across all TSP levels
        fouling_fraction = total_restriction / self.config.tsp_count
        
        # Pressure drop ratio using orifice flow equation
        # ΔP ∝ 1/A² for constant flow, so ΔP_ratio = (A_original/A_effective)²
        avg_area_ratio = 1.0 - fouling_fraction
        avg_area_ratio = max(avg_area_ratio, 0.1)  # Prevent division by zero
        pressure_drop_ratio = (1.0 / avg_area_ratio) ** self.config.flow_restriction_exponent
        
        return fouling_fraction, pressure_drop_ratio, level_restrictions
    
    def calculate_heat_transfer_degradation(self, fouling_fraction: float) -> float:
        """
        Calculate heat transfer coefficient degradation from TSP fouling
        
        Args:
            fouling_fraction: Overall fouling fraction (0-1)
            
        Returns:
            Heat transfer degradation factor (0-1, where 1 = complete loss)
        """
        # Heat transfer degradation due to reduced mixing and flow maldistribution
        # Based on industry correlations and test data
        
        # Primary mechanism: reduced cross-flow mixing
        mixing_degradation = fouling_fraction ** self.config.mixing_degradation_exponent
        
        # Secondary mechanism: flow maldistribution creating hot spots
        maldistribution_effect = fouling_fraction * 0.3  # 30% additional degradation from maldistribution
        
        # Combined heat transfer degradation
        total_degradation = (mixing_degradation + maldistribution_effect) * self.config.heat_transfer_degradation_factor
        
        # Physical limit: cannot exceed 90% degradation (some heat transfer always occurs)
        total_degradation = min(total_degradation, 0.9)
        
        return total_degradation
    
    def calculate_flow_maldistribution(self, level_restrictions: List[float]) -> float:
        """
        Calculate flow maldistribution between tube lanes
        
        Args:
            level_restrictions: Flow restrictions at each TSP level
            
        Returns:
            Flow maldistribution factor (0-1)
        """
        if not level_restrictions:
            return 0.0
        
        # Calculate standard deviation of restrictions across levels
        mean_restriction = np.mean(level_restrictions)
        std_restriction = np.std(level_restrictions)
        
        # Maldistribution factor based on variation in restrictions
        maldistribution = std_restriction / (mean_restriction + 0.01)  # Avoid division by zero
        
        # Normalize to 0-1 range
        maldistribution = min(maldistribution, 1.0)
        
        return maldistribution
    
    def determine_fouling_stage(self, fouling_fraction: float) -> FoulingStage:
        """
        Determine current fouling stage based on fouling fraction
        
        Args:
            fouling_fraction: Overall fouling fraction (0-1)
            
        Returns:
            Current fouling stage
        """
        if fouling_fraction < 0.4:
            return FoulingStage.NORMAL
        elif fouling_fraction < 0.7:
            return FoulingStage.SIGNIFICANT
        elif fouling_fraction < 0.85:
            return FoulingStage.SEVERE
        else:
            return FoulingStage.CRITICAL
    
    def evaluate_shutdown_conditions(self) -> Tuple[bool, List[ShutdownReason]]:
        """
        Evaluate if steam generator shutdown is required
        
        Returns:
            Tuple of (shutdown_required, shutdown_reasons)
        """
        shutdown_reasons = []
        
        # Critical fouling level
        if self.fouling_fraction >= self.config.fouling_trip_threshold:
            shutdown_reasons.append(ShutdownReason.CRITICAL_FOULING)
        
        # Excessive heat transfer degradation
        if self.heat_transfer_degradation >= (1.0 - self.config.heat_transfer_trip_threshold):
            shutdown_reasons.append(ShutdownReason.HEAT_TRANSFER_DEGRADATION)
        
        # Excessive pressure drop
        if self.pressure_drop_ratio >= self.config.pressure_drop_trip_threshold:
            shutdown_reasons.append(ShutdownReason.PRESSURE_DROP_EXCESSIVE)
        
        # Severe flow maldistribution
        if self.flow_maldistribution >= self.config.flow_maldistribution_limit:
            shutdown_reasons.append(ShutdownReason.FLOW_MALDISTRIBUTION)
        
        # Design life exceeded with significant fouling
        if (self.operating_years > self.config.design_life_years and 
            self.fouling_fraction > 0.5):
            shutdown_reasons.append(ShutdownReason.DESIGN_LIFE_EXCEEDED)
        
        shutdown_required = len(shutdown_reasons) > 0
        
        return shutdown_required, shutdown_reasons
    
    def perform_cleaning(self, cleaning_type: str = "chemical") -> Dict[str, float]:
        """
        Perform TSP cleaning operation
        
        Args:
            cleaning_type: Type of cleaning ("chemical" or "mechanical")
            
        Returns:
            Dictionary with cleaning results
        """
        if cleaning_type == "chemical":
            effectiveness = self.config.chemical_cleaning_effectiveness
        elif cleaning_type == "mechanical":
            effectiveness = self.config.mechanical_cleaning_effectiveness
        else:
            effectiveness = 0.5  # Default effectiveness
        
        # Remove deposits based on effectiveness
        for level in range(self.config.tsp_count):
            self.deposits.magnetite_thickness[level] *= (1.0 - effectiveness)
            self.deposits.copper_thickness[level] *= (1.0 - effectiveness * 0.8)  # Copper harder to remove
            self.deposits.silica_thickness[level] *= (1.0 - effectiveness * 0.9)   # Silica moderately hard to remove
            self.deposits.biological_thickness[level] *= (1.0 - effectiveness)     # Biological deposits easily removed
        
        # Update tracking
        self.total_cleaning_cycles += 1
        self.last_cleaning_time = 0.0
        
        # Recalculate fouling state after cleaning
        self.fouling_fraction, self.pressure_drop_ratio, level_restrictions = self.calculate_flow_restriction()
        self.heat_transfer_degradation = self.calculate_heat_transfer_degradation(self.fouling_fraction)
        self.flow_maldistribution = self.calculate_flow_maldistribution(level_restrictions)
        self.fouling_stage = self.determine_fouling_stage(self.fouling_fraction)
        
        return {
            'cleaning_type': cleaning_type,
            'effectiveness': effectiveness,
            'fouling_fraction_after': self.fouling_fraction,
            'heat_transfer_recovery': effectiveness * self.heat_transfer_degradation,
            'total_cleaning_cycles': self.total_cleaning_cycles
        }
    
    def update_fouling_state(self,
                           temperature: float,
                           flow_velocity: float,
                           dt_hours: float) -> Dict[str, float]:
        """
        Update TSP fouling state for one time step using unified water chemistry
        
        Args:
            temperature: Average temperature (°C)
            flow_velocity: Average flow velocity (m/s)
            dt_hours: Time step (hours)
            
        Returns:
            Dictionary with updated fouling state and performance impacts
        """
        dt_years = dt_hours / (365.25 * 24.0)  # Convert hours to years
        
        # Update operating time
        self.operating_years += dt_years
        self.last_cleaning_time += dt_years
        
        # Calculate deposit formation rates using unified water chemistry
        formation_rates = self.calculate_deposit_formation_rates(
            temperature, flow_velocity
        )
        
        # Update deposit accumulation
        self.update_deposit_accumulation(formation_rates, dt_years)
        
        # Calculate flow restriction and pressure drop
        self.fouling_fraction, self.pressure_drop_ratio, level_restrictions = self.calculate_flow_restriction()
        
        # Calculate heat transfer degradation
        self.heat_transfer_degradation = self.calculate_heat_transfer_degradation(self.fouling_fraction)
        
        # Calculate flow maldistribution
        self.flow_maldistribution = self.calculate_flow_maldistribution(level_restrictions)
        
        # Determine fouling stage
        self.fouling_stage = self.determine_fouling_stage(self.fouling_fraction)
        
        # Evaluate shutdown conditions
        if self.protection_system_active:
            self.shutdown_required, self.shutdown_reasons = self.evaluate_shutdown_conditions()
        
        # Update replacement recommendation
        self.replacement_recommended = (
            self.fouling_fraction >= self.config.fouling_replacement_threshold or
            self.operating_years > self.config.design_life_years
        )
        
        # Calculate cumulative power loss
        power_loss_mw = 100.0 * self.heat_transfer_degradation  # Simplified power loss calculation
        self.cumulative_power_loss += power_loss_mw * dt_hours / 1000.0  # MWh
        
        return {
            'fouling_fraction': self.fouling_fraction,
            'fouling_stage': self.fouling_stage.value,
            'heat_transfer_degradation': self.heat_transfer_degradation,
            'pressure_drop_ratio': self.pressure_drop_ratio,
            'flow_maldistribution': self.flow_maldistribution,
            'operating_years': self.operating_years,
            'shutdown_required': self.shutdown_required,
            'shutdown_reasons': [reason.value for reason in self.shutdown_reasons],
            'replacement_recommended': self.replacement_recommended,
            'cumulative_power_loss_mwh': self.cumulative_power_loss,
            'cleaning_cycles': self.total_cleaning_cycles,
            'years_since_cleaning': self.last_cleaning_time,
            'average_deposit_thickness_mm': self.deposits.get_average_thickness(),
            'maximum_deposit_thickness_mm': self.deposits.get_maximum_thickness()
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'tsp_fouling_fraction': self.fouling_fraction,
            'tsp_fouling_stage_numeric': list(FoulingStage).index(self.fouling_stage),
            'tsp_heat_transfer_degradation': self.heat_transfer_degradation,
            'tsp_pressure_drop_ratio': self.pressure_drop_ratio,
            'tsp_flow_maldistribution': self.flow_maldistribution,
            'tsp_operating_years': self.operating_years,
            'tsp_shutdown_required': float(self.shutdown_required),
            'tsp_replacement_recommended': float(self.replacement_recommended),
            'tsp_cumulative_power_loss_mwh': self.cumulative_power_loss,
            'tsp_cleaning_cycles': float(self.total_cleaning_cycles),
            'tsp_years_since_cleaning': self.last_cleaning_time,
            'tsp_average_deposit_thickness': self.deposits.get_average_thickness(),
            'tsp_maximum_deposit_thickness': self.deposits.get_maximum_thickness()
        }
        
        # Add individual TSP level data
        for level in range(min(self.config.tsp_count, 7)):  # Limit to 7 levels for state dict
            state_dict[f'tsp_level_{level}_total_thickness'] = self.deposits.get_total_thickness(level)
            state_dict[f'tsp_level_{level}_magnetite'] = self.deposits.magnetite_thickness[level]
            state_dict[f'tsp_level_{level}_copper'] = self.deposits.copper_thickness[level]
            state_dict[f'tsp_level_{level}_silica'] = self.deposits.silica_thickness[level]
            state_dict[f'tsp_level_{level}_biological'] = self.deposits.biological_thickness[level]
        
        return state_dict
    
    def reset(self) -> None:
        """Reset TSP fouling model to initial conditions"""
        # Reset deposit state
        self.deposits = DepositState()
        
        # Reset operating parameters
        self.operating_years = 0.0
        self.total_cleaning_cycles = 0
        self.last_cleaning_time = 0.0
        
        # Reset fouling state
        self.fouling_fraction = 0.0
        self.fouling_stage = FoulingStage.NORMAL
        self.heat_transfer_degradation = 0.0
        self.pressure_drop_ratio = 1.0
        self.flow_maldistribution = 0.0
        
        # Reset performance tracking
        self.cumulative_power_loss = 0.0
        self.replacement_recommended = False
        
        # Reset shutdown protection state
        self.shutdown_required = False
        self.shutdown_reasons = []
        self.protection_system_active = True
    
    # === CHEMISTRY FLOW PROVIDER INTERFACE METHODS ===
    # These methods enable integration with chemistry_flow_tracker
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data from TSP fouling perspective
        """
        # TSP fouling affects chemistry through deposit formation and release
        return {
            'steam_generator_fouling': {
                ChemicalSpecies.IRON.value: self.deposits.get_average_thickness() * 0.1,  # Iron release from deposits
                ChemicalSpecies.COPPER.value: self.deposits.get_average_thickness() * 0.05,  # Copper release
                ChemicalSpecies.SILICA.value: self.deposits.get_average_thickness() * 0.02,  # Silica release
                'fouling_factor': self.fouling_fraction,
                'heat_transfer_impact': self.heat_transfer_degradation
            },
            'deposit_formation': {
                'magnetite_rate': sum(self.deposits.magnetite_thickness) / len(self.deposits.magnetite_thickness),
                'copper_rate': sum(self.deposits.copper_thickness) / len(self.deposits.copper_thickness),
                'silica_rate': sum(self.deposits.silica_thickness) / len(self.deposits.silica_thickness),
                'biological_rate': sum(self.deposits.biological_thickness) / len(self.deposits.biological_thickness)
            }
        }
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state from TSP fouling perspective
        
        Returns:
            Dictionary with TSP fouling chemistry state
        """
        return {
            'tsp_fouling_fraction': self.fouling_fraction,
            'tsp_heat_transfer_degradation': self.heat_transfer_degradation,
            'tsp_pressure_drop_ratio': self.pressure_drop_ratio,
            'tsp_average_deposit_thickness': self.deposits.get_average_thickness(),
            'tsp_maximum_deposit_thickness': self.deposits.get_maximum_thickness(),
            'tsp_operating_years': self.operating_years,
            'tsp_cleaning_cycles': float(self.total_cleaning_cycles),
            'tsp_shutdown_required': float(self.shutdown_required)
        }
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update TSP fouling based on external chemistry effects
        
        This method allows the chemistry flow tracker to influence TSP fouling
        based on system-wide chemistry changes.
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Update water chemistry system if chemistry feedback is provided
        if hasattr(self, 'water_chemistry') and self.water_chemistry:
            # Apply chemistry effects to the water chemistry system
            if 'system_chemistry_feedback' in chemistry_state:
                self.water_chemistry.update_chemistry_effects(chemistry_state)
            
            # Update from pH control effects
            if 'ph_control_effects' in chemistry_state:
                ph_effects = chemistry_state['ph_control_effects']
                
                # pH control can affect fouling rates
                if 'ph_setpoint' in ph_effects:
                    target_ph = ph_effects['ph_setpoint']
                    current_ph = self.water_chemistry.ph
                    
                    # Gradual pH adjustment affects fouling
                    if abs(current_ph - target_ph) > 0.1:
                        # pH changes can affect deposit stability
                        ph_change_factor = abs(current_ph - target_ph) * 0.1
                        
                        # Adjust deposit thicknesses based on pH changes
                        for level in range(self.config.tsp_count):
                            # pH changes can cause deposit dissolution or precipitation
                            if target_ph > current_ph:  # pH increasing (more basic)
                                # Some deposits may dissolve
                                self.deposits.magnetite_thickness[level] *= (1.0 - ph_change_factor * 0.05)
                                self.deposits.copper_thickness[level] *= (1.0 - ph_change_factor * 0.03)
                            else:  # pH decreasing (more acidic)
                                # May accelerate some deposit formation
                                self.deposits.silica_thickness[level] *= (1.0 + ph_change_factor * 0.02)
        
        # Update from chemical cleaning effects
        if 'cleaning_effectiveness' in chemistry_state:
            cleaning_eff = chemistry_state['cleaning_effectiveness']
            if cleaning_eff > 0.1:  # Significant cleaning effect
                # Apply cleaning effect to deposits
                for level in range(self.config.tsp_count):
                    self.deposits.magnetite_thickness[level] *= (1.0 - cleaning_eff * 0.5)
                    self.deposits.copper_thickness[level] *= (1.0 - cleaning_eff * 0.3)
                    self.deposits.silica_thickness[level] *= (1.0 - cleaning_eff * 0.4)
                    self.deposits.biological_thickness[level] *= (1.0 - cleaning_eff * 0.8)
                
                # Recalculate fouling state after cleaning effects
                self.fouling_fraction, self.pressure_drop_ratio, level_restrictions = self.calculate_flow_restriction()
                self.heat_transfer_degradation = self.calculate_heat_transfer_degradation(self.fouling_fraction)
                self.flow_maldistribution = self.calculate_flow_maldistribution(level_restrictions)
                self.fouling_stage = self.determine_fouling_stage(self.fouling_fraction)


# Example usage and testing
if __name__ == "__main__":
    print("TSP Fouling Model - Test with Unified Water Chemistry")
    print("=" * 55)
    
    # Create unified water chemistry system
    water_chemistry = WaterChemistry(WaterChemistryConfig())
    
    # Create TSP fouling model with unified water chemistry
    tsp_model = TSPFoulingModel(water_chemistry=water_chemistry)
    
    print(f"TSP Configuration:")
    print(f"  TSP Count: {tsp_model.config.tsp_count}")
    print(f"  Hole Diameter: {tsp_model.config.tsp_hole_diameter*1000:.1f} mm")
    print(f"  Design Life: {tsp_model.config.design_life_years} years")
    print(f"  Fouling Trip Threshold: {tsp_model.config.fouling_trip_threshold*100:.0f}%")
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
    
    # Test fouling progression over time
    print("TSP Fouling Progression Test:")
    print(f"{'Year':<6} {'Fouling%':<10} {'Stage':<12} {'HT Deg%':<10} {'ΔP Ratio':<10} {'Shutdown':<10}")
    print("-" * 70)
    
    # Simulate 45 years of operation
    for year in range(0, 46, 2):  # Every 2 years
        # Simulate one year of operation
        for _ in range(365):  # Daily updates
            # Update water chemistry (simulates gradual changes)
            water_chemistry.update_chemistry({
                'makeup_water_quality': {
                    'ph': 7.2,
                    'hardness': 100.0,
                    'tds': 300.0,
                    'chloride': 30.0,
                    'dissolved_oxygen': 8.0
                },
                'blowdown_rate': 0.02
            }, dt=24.0)
            
            result = tsp_model.update_fouling_state(
                temperature=285.0,  # °C
                flow_velocity=3.0,  # m/s
                dt_hours=24.0  # 24 hours per day
            )
        
        # Print results every 2 years
        shutdown_status = "YES" if result['shutdown_required'] else "No"
        print(f"{year:<6} {result['fouling_fraction']*100:<10.1f} "
              f"{result['fouling_stage']:<12} {result['heat_transfer_degradation']*100:<10.1f} "
              f"{result['pressure_drop_ratio']:<10.2f} {shutdown_status:<10}")
        
        # Perform cleaning if fouling gets significant
        if result['fouling_fraction'] > 0.6 and result['years_since_cleaning'] > 5:
            cleaning_result = tsp_model.perform_cleaning("chemical")
            print(f"      -> Chemical cleaning performed, fouling reduced to {cleaning_result['fouling_fraction_after']*100:.1f}%")
        
        # Break if shutdown is required
        if result['shutdown_required']:
            print(f"      -> SHUTDOWN REQUIRED: {', '.join(result['shutdown_reasons'])}")
            break
    
    print()
    print("TSP fouling model with unified water chemistry ready for integration!")
