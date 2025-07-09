"""
Chemistry Flow Tracking System for Nuclear Plant Secondary Side

This module provides comprehensive chemistry flow tracking throughout the secondary
system to ensure proper mass balance and chemistry-based calculations.

Key Features:
1. Chemical species mass flow calculations
2. Component-level chemistry flow interfaces
3. System-wide mass balance validation
4. Chemistry transport modeling
5. Fouling and corrosion rate calculations

Design Philosophy:
- Mirror the heat_flow_tracker.py architecture exactly
- Track chemical species through the entire Rankine cycle
- Provide mass balance validation like energy balance validation
- Enable chemistry-based fouling and performance modeling
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum


class ChemicalSpecies(Enum):
    """Chemical species tracked in the secondary system"""
    # Primary chemistry parameters
    PH = "ph"
    IRON = "iron"
    COPPER = "copper"
    SILICA = "silica"
    DISSOLVED_OXYGEN = "dissolved_oxygen"
    
    # Traditional water quality
    HARDNESS = "hardness"
    CHLORIDE = "chloride"
    TDS = "total_dissolved_solids"
    ALKALINITY = "alkalinity"
    
    # Treatment chemicals
    AMMONIA = "ammonia"
    MORPHOLINE = "morpholine"
    HYDRAZINE = "hydrazine"
    CHLORINE = "chlorine"
    ANTISCALANT = "antiscalant"
    CORROSION_INHIBITOR = "corrosion_inhibitor"
    
    # Derived parameters
    AGGRESSIVENESS = "water_aggressiveness"
    PARTICLE_CONTENT = "particle_content"
    SCALING_TENDENCY = "scaling_tendency"
    CORROSION_TENDENCY = "corrosion_tendency"


@dataclass
class ChemistryFlowState:
    """
    Complete chemistry flow state for the secondary system
    
    All concentrations in ppm unless otherwise noted
    All flow rates in kg/s
    """
    
    # === PRIMARY CHEMISTRY INPUTS ===
    makeup_water_chemistry: Dict[str, float] = field(default_factory=dict)
    chemical_addition_rates: Dict[str, float] = field(default_factory=dict)  # kg/s
    blowdown_chemistry_losses: Dict[str, float] = field(default_factory=dict)  # kg/s
    
    # === STEAM GENERATOR CHEMISTRY ===
    sg_liquid_chemistry: Dict[str, float] = field(default_factory=dict)  # ppm
    sg_steam_carryover: Dict[str, float] = field(default_factory=dict)  # kg/s
    sg_blowdown_chemistry: Dict[str, float] = field(default_factory=dict)  # ppm
    sg_concentration_factor: float = 1.0
    
    # === STEAM SYSTEM CHEMISTRY ===
    steam_chemistry: Dict[str, float] = field(default_factory=dict)  # ppm
    turbine_deposit_rates: Dict[str, float] = field(default_factory=dict)  # kg/s
    steam_purity_factor: float = 1.0
    
    # === CONDENSATE CHEMISTRY ===
    condensate_chemistry: Dict[str, float] = field(default_factory=dict)  # ppm
    condenser_chemistry_effects: Dict[str, float] = field(default_factory=dict)
    cooling_water_interaction: Dict[str, float] = field(default_factory=dict)
    
    # === FEEDWATER CHEMISTRY ===
    feedwater_chemistry: Dict[str, float] = field(default_factory=dict)  # ppm
    feedwater_treatment_effectiveness: float = 1.0
    
    # === CONTROL SYSTEM STATUS ===
    ph_control_status: str = "AUTO"  # AUTO, MANUAL, FAILED
    oxygen_control_status: str = "AUTO"
    biocide_control_status: str = "AUTO"
    chemical_supply_levels: Dict[str, float] = field(default_factory=dict)  # % full
    
    # === FOULING AND DEGRADATION RATES ===
    tsp_fouling_rate: float = 0.0  # kg/m²/year
    condenser_fouling_rate: float = 0.0  # fouling factor increase/year
    turbine_fouling_rate: float = 0.0  # efficiency loss %/year
    corrosion_rates: Dict[str, float] = field(default_factory=dict)  # mm/year
    
    # === MASS BALANCE VALIDATION ===
    total_chemistry_input: Dict[str, float] = field(default_factory=dict)  # kg/s
    total_chemistry_output: Dict[str, float] = field(default_factory=dict)  # kg/s
    chemistry_balance_error: Dict[str, float] = field(default_factory=dict)  # kg/s
    chemistry_balance_percent_error: Dict[str, float] = field(default_factory=dict)  # %
    
    # === PERFORMANCE METRICS ===
    overall_chemistry_stability: float = 1.0  # 0-1 stability factor
    treatment_cost_rate: float = 0.0  # $/hour
    fouling_impact_on_efficiency: float = 0.0  # % efficiency loss
    maintenance_urgency_factor: float = 0.0  # 0-1 urgency


class ChemistryFlowProvider(ABC):
    """
    Abstract interface for components that provide chemistry flow information
    
    All components in the secondary system should implement this interface
    to enable comprehensive chemistry flow tracking.
    """
    
    @abstractmethod
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get current chemistry flows for this component
        
        Returns:
            Dictionary with chemistry flow values in kg/s for each species
        """
        pass
    
    @abstractmethod
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry concentrations for this component
        
        Returns:
            Dictionary with chemistry concentrations in ppm
        """
        pass
    
    @abstractmethod
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update component behavior based on chemistry state
        
        Args:
            chemistry_state: Current chemistry concentrations
        """
        pass


class ChemistryProperties:
    """
    Chemical property calculations for chemistry flow analysis
    
    Provides consistent property calculations across all components
    """
    
    # Chemical species properties database
    SPECIES_PROPERTIES = {
        ChemicalSpecies.AMMONIA: {
            'molecular_weight': 17.03,  # g/mol
            'volatility': 0.8,  # Steam carryover fraction at SG conditions
            'solubility_factor': 1.0,  # Relative solubility
            'corrosion_factor': -0.5,  # Negative = inhibits corrosion
            'fouling_factor': 0.1,  # Positive = promotes fouling
            'biological_impact': -0.8  # Negative = biocide effect
        },
        ChemicalSpecies.IRON: {
            'molecular_weight': 55.85,
            'volatility': 0.0,  # Non-volatile
            'solubility_factor': 0.5,
            'corrosion_factor': 1.5,  # Promotes corrosion
            'fouling_factor': 2.0,  # Strong fouling promoter
            'biological_impact': 0.2
        },
        ChemicalSpecies.COPPER: {
            'molecular_weight': 63.55,
            'volatility': 0.0,
            'solubility_factor': 0.3,
            'corrosion_factor': 1.8,
            'fouling_factor': 2.5,
            'biological_impact': -0.3  # Some biocide effect
        },
        ChemicalSpecies.SILICA: {
            'molecular_weight': 60.08,
            'volatility': 0.02,  # Very low volatility
            'solubility_factor': 0.8,
            'corrosion_factor': 0.1,
            'fouling_factor': 1.8,  # Forms hard scale
            'biological_impact': 0.0
        },
        ChemicalSpecies.CHLORIDE: {
            'molecular_weight': 35.45,
            'volatility': 0.0,
            'solubility_factor': 1.0,
            'corrosion_factor': 3.0,  # Very aggressive
            'fouling_factor': 0.5,
            'biological_impact': -0.5
        },
        ChemicalSpecies.MORPHOLINE: {
            'molecular_weight': 87.12,
            'volatility': 0.6,  # Moderate volatility
            'solubility_factor': 1.0,
            'corrosion_factor': -0.8,
            'fouling_factor': 0.0,
            'biological_impact': -0.4
        },
        ChemicalSpecies.HYDRAZINE: {
            'molecular_weight': 32.05,
            'volatility': 0.3,
            'solubility_factor': 1.0,
            'corrosion_factor': -1.0,  # Strong oxygen scavenger
            'fouling_factor': 0.0,
            'biological_impact': -0.6
        }
    }
    
    @staticmethod
    def calculate_carryover_fraction(species: ChemicalSpecies, 
                                   pressure: float, 
                                   temperature: float,
                                   steam_quality: float = 1.0) -> float:
        """
        Calculate steam carryover fraction for chemical species
        
        Args:
            species: Chemical species
            pressure: Steam pressure (MPa)
            temperature: Steam temperature (°C)
            steam_quality: Steam quality (0-1)
            
        Returns:
            Carryover fraction (0-1)
        """
        if species not in ChemistryProperties.SPECIES_PROPERTIES:
            return 0.0
        
        base_volatility = ChemistryProperties.SPECIES_PROPERTIES[species]['volatility']
        
        # Pressure effect (higher pressure = more carryover)
        pressure_factor = 1.0 + (pressure - 6.895) * 0.1  # Normalized around 6.895 MPa
        pressure_factor = np.clip(pressure_factor, 0.5, 2.0)
        
        # Temperature effect (higher temperature = more carryover for volatiles)
        temp_factor = 1.0 + (temperature - 280.0) * 0.01  # Normalized around 280°C
        temp_factor = np.clip(temp_factor, 0.8, 1.5)
        
        # Steam quality effect (wet steam carries more impurities)
        quality_factor = steam_quality * 0.8 + 0.2  # Range 0.2-1.0
        
        carryover = base_volatility * pressure_factor * temp_factor * quality_factor
        return np.clip(carryover, 0.0, 1.0)
    
    @staticmethod
    def calculate_solubility_limit(species: ChemicalSpecies, 
                                 temperature: float, 
                                 ph: float) -> float:
        """
        Calculate species solubility limit under conditions
        
        Args:
            species: Chemical species
            temperature: Temperature (°C)
            ph: pH value
            
        Returns:
            Solubility limit (ppm)
        """
        if species not in ChemistryProperties.SPECIES_PROPERTIES:
            return 1000.0  # Default high solubility
        
        base_solubility = {
            ChemicalSpecies.IRON: 0.1,      # Very low at high pH
            ChemicalSpecies.COPPER: 0.05,   # Very low at high pH
            ChemicalSpecies.SILICA: 150.0,  # Moderate solubility
            ChemicalSpecies.CHLORIDE: 10000.0,  # Very high solubility
            ChemicalSpecies.AMMONIA: 1000.0,    # High solubility
            ChemicalSpecies.MORPHOLINE: 1000.0  # High solubility
        }.get(species, 100.0)
        
        # Temperature effect (generally decreases solubility for most species)
        temp_factor = 1.0 - (temperature - 25.0) * 0.001
        temp_factor = np.clip(temp_factor, 0.1, 2.0)
        
        # pH effect (varies by species)
        if species in [ChemicalSpecies.IRON, ChemicalSpecies.COPPER]:
            # Metal solubility decreases with higher pH
            ph_factor = np.exp(-(ph - 7.0) * 0.5)
        else:
            # Most other species relatively pH independent
            ph_factor = 1.0
        
        return base_solubility * temp_factor * ph_factor
    
    @staticmethod
    def calculate_fouling_rate(species_concentrations: Dict[str, float],
                             temperature: float,
                             flow_velocity: float) -> float:
        """
        Calculate fouling rate based on chemistry
        
        Args:
            species_concentrations: Dictionary of species concentrations (ppm)
            temperature: Temperature (°C)
            flow_velocity: Flow velocity (m/s)
            
        Returns:
            Fouling rate (kg/m²/year)
        """
        base_fouling_rate = 0.0
        
        for species_name, concentration in species_concentrations.items():
            try:
                species = ChemicalSpecies(species_name)
                if species in ChemistryProperties.SPECIES_PROPERTIES:
                    fouling_factor = ChemistryProperties.SPECIES_PROPERTIES[species]['fouling_factor']
                    base_fouling_rate += concentration * fouling_factor * 0.001  # Convert ppm to rate
            except ValueError:
                continue  # Skip unknown species
        
        # Temperature effect (Arrhenius relationship)
        temp_factor = np.exp((temperature - 25.0) / 50.0)
        
        # Flow velocity effect (higher velocity reduces fouling)
        velocity_factor = 1.0 / (1.0 + flow_velocity * 0.1)
        
        return base_fouling_rate * temp_factor * velocity_factor
    
    @staticmethod
    def calculate_corrosion_rate(species_concentrations: Dict[str, float],
                               temperature: float,
                               ph: float,
                               material: str = "carbon_steel") -> float:
        """
        Calculate corrosion rate based on chemistry
        
        Args:
            species_concentrations: Dictionary of species concentrations (ppm)
            temperature: Temperature (°C)
            ph: pH value
            material: Material type
            
        Returns:
            Corrosion rate (mm/year)
        """
        base_corrosion_rate = 0.1  # Base corrosion rate
        
        # Chemistry effects
        chemistry_factor = 1.0
        for species_name, concentration in species_concentrations.items():
            try:
                species = ChemicalSpecies(species_name)
                if species in ChemistryProperties.SPECIES_PROPERTIES:
                    corr_factor = ChemistryProperties.SPECIES_PROPERTIES[species]['corrosion_factor']
                    chemistry_factor += concentration * corr_factor * 0.0001  # Convert ppm to factor
            except ValueError:
                continue
        
        # Temperature effect (doubles every 25°C)
        temp_factor = 2.0 ** ((temperature - 25.0) / 25.0)
        
        # pH effect (optimal around pH 9.2 for PWR)
        ph_factor = 1.0 + abs(ph - 9.2) * 0.5
        
        # Material factor
        material_factors = {
            "carbon_steel": 1.0,
            "stainless_steel": 0.1,
            "inconel": 0.05,
            "copper_alloy": 1.5
        }
        material_factor = material_factors.get(material, 1.0)
        
        return base_corrosion_rate * chemistry_factor * temp_factor * ph_factor * material_factor


class ChemistryFlowTracker:
    """
    Main chemistry flow tracking system for the secondary side
    
    This class coordinates chemistry flow tracking across all components
    and provides comprehensive mass balance analysis.
    """
    
    def __init__(self, chemistry_flow_providers: Optional[Dict[str, ChemistryFlowProvider]] = None):
        """
        Initialize chemistry flow tracker
        
        Args:
            chemistry_flow_providers: Dictionary of component name -> ChemistryFlowProvider instances
        """
        self.chemistry_flow_state = ChemistryFlowState()
        self.component_chemistry = {}  # Store individual component chemistry
        self.chemistry_history = []    # Store historical chemistry data
        self.validation_tolerance = 0.05  # 5% tolerance for mass balance
        
        # Store chemistry flow providers for automatic updates
        self.chemistry_flow_providers = chemistry_flow_providers or {}
        
        # Initialize default chemistry values
        self._initialize_default_chemistry()
    
    def _initialize_default_chemistry(self) -> None:
        """Initialize default chemistry values for all tracked species"""
        default_chemistry = {
            ChemicalSpecies.PH.value: 9.2,
            ChemicalSpecies.IRON.value: 0.1,
            ChemicalSpecies.COPPER.value: 0.05,
            ChemicalSpecies.SILICA.value: 20.0,
            ChemicalSpecies.DISSOLVED_OXYGEN.value: 0.005,
            ChemicalSpecies.HARDNESS.value: 150.0,
            ChemicalSpecies.CHLORIDE.value: 50.0,
            ChemicalSpecies.TDS.value: 500.0,
            ChemicalSpecies.ALKALINITY.value: 120.0,
            ChemicalSpecies.AMMONIA.value: 0.0,
            ChemicalSpecies.MORPHOLINE.value: 0.0,
            ChemicalSpecies.HYDRAZINE.value: 0.0,
            ChemicalSpecies.CHLORINE.value: 0.5,
            ChemicalSpecies.ANTISCALANT.value: 5.0,
            ChemicalSpecies.CORROSION_INHIBITOR.value: 10.0
        }
        
        # Initialize all chemistry dictionaries
        self.chemistry_flow_state.makeup_water_chemistry = default_chemistry.copy()
        self.chemistry_flow_state.sg_liquid_chemistry = default_chemistry.copy()
        self.chemistry_flow_state.steam_chemistry = {}
        self.chemistry_flow_state.condensate_chemistry = default_chemistry.copy()
        self.chemistry_flow_state.feedwater_chemistry = default_chemistry.copy()
        
        # Initialize chemical supply levels
        self.chemistry_flow_state.chemical_supply_levels = {
            ChemicalSpecies.AMMONIA.value: 80.0,
            ChemicalSpecies.MORPHOLINE.value: 80.0,
            ChemicalSpecies.HYDRAZINE.value: 80.0,
            ChemicalSpecies.CHLORINE.value: 80.0,
            ChemicalSpecies.ANTISCALANT.value: 80.0,
            ChemicalSpecies.CORROSION_INHIBITOR.value: 80.0
        }
    
    def update_from_providers(self) -> None:
        """Update component chemistry from all registered chemistry flow providers"""
        for component_name, provider in self.chemistry_flow_providers.items():
            try:
                chemistry_flows = provider.get_chemistry_flows()
                chemistry_state = provider.get_chemistry_state()
                self.update_component_chemistry(component_name, chemistry_state, chemistry_flows)
            except Exception as e:
                print(f"Warning: Failed to get chemistry flows from {component_name}: {e}")
    
    def update_component_chemistry(self, 
                                 component_name: str, 
                                 chemistry_state: Dict[str, float],
                                 chemistry_flows: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """
        Update chemistry for a specific component
        
        Args:
            component_name: Name of the component
            chemistry_state: Dictionary of chemistry concentrations (ppm)
            chemistry_flows: Optional dictionary of chemistry flows (kg/s)
        """
        self.component_chemistry[component_name] = {
            'state': chemistry_state.copy(),
            'flows': chemistry_flows.copy() if chemistry_flows else {}
        }
    
    def calculate_system_chemistry_flows(self) -> ChemistryFlowState:
        """
        Calculate complete system chemistry flows from component data
        
        Returns:
            Complete chemistry flow state
        """
        state = ChemistryFlowState()
        
        # Extract steam generator chemistry
        if 'steam_generator' in self.component_chemistry:
            sg_data = self.component_chemistry['steam_generator']
            state.sg_liquid_chemistry = sg_data['state'].copy()
            
            # Calculate steam carryover for each species
            for species_name, concentration in state.sg_liquid_chemistry.items():
                try:
                    species = ChemicalSpecies(species_name)
                    carryover_fraction = ChemistryProperties.calculate_carryover_fraction(
                        species, 6.895, 280.0  # Typical SG conditions
                    )
                    state.sg_steam_carryover[species_name] = concentration * carryover_fraction
                except ValueError:
                    continue  # Skip unknown species
        
        # Extract turbine chemistry
        if 'turbine' in self.component_chemistry:
            turbine_data = self.component_chemistry['turbine']
            state.steam_chemistry = turbine_data['state'].copy()
            
            # Calculate deposit rates
            for species_name, concentration in state.steam_chemistry.items():
                deposit_rate = concentration * 0.001  # Simplified deposit calculation
                state.turbine_deposit_rates[species_name] = deposit_rate
        
        # Extract condenser chemistry
        if 'condenser' in self.component_chemistry:
            condenser_data = self.component_chemistry['condenser']
            state.condensate_chemistry = condenser_data['state'].copy()
            
            # Calculate condenser fouling effects
            state.condenser_chemistry_effects = self._calculate_condenser_effects(
                state.condensate_chemistry
            )
        
        # Extract feedwater chemistry
        if 'feedwater' in self.component_chemistry:
            fw_data = self.component_chemistry['feedwater']
            state.feedwater_chemistry = fw_data['state'].copy()
        
        # Calculate fouling and corrosion rates
        state.tsp_fouling_rate = ChemistryProperties.calculate_fouling_rate(
            state.sg_liquid_chemistry, 280.0, 3.0
        )
        
        state.condenser_fouling_rate = ChemistryProperties.calculate_fouling_rate(
            state.condensate_chemistry, 35.0, 2.0
        )
        
        # Calculate corrosion rates for different materials
        state.corrosion_rates = {
            'carbon_steel': ChemistryProperties.calculate_corrosion_rate(
                state.feedwater_chemistry, 200.0, 
                state.feedwater_chemistry.get(ChemicalSpecies.PH.value, 9.2)
            ),
            'stainless_steel': ChemistryProperties.calculate_corrosion_rate(
                state.steam_chemistry, 300.0,
                state.steam_chemistry.get(ChemicalSpecies.PH.value, 9.2),
                'stainless_steel'
            )
        }
        
        # Calculate mass balance
        self._calculate_mass_balance(state)
        
        # Calculate performance metrics
        self._calculate_performance_metrics(state)
        
        self.chemistry_flow_state = state
        return state
    
    def _calculate_condenser_effects(self, condensate_chemistry: Dict[str, float]) -> Dict[str, float]:
        """Calculate condenser-specific chemistry effects"""
        effects = {}
        
        # Biological fouling potential
        chlorine_level = condensate_chemistry.get(ChemicalSpecies.CHLORINE.value, 0.0)
        effects['biological_fouling_rate'] = max(0.0, 1.0 - chlorine_level * 2.0)
        
        # Scale formation potential
        hardness = condensate_chemistry.get(ChemicalSpecies.HARDNESS.value, 0.0)
        effects['scale_formation_rate'] = hardness * 0.001
        
        # Corrosion potential
        chloride = condensate_chemistry.get(ChemicalSpecies.CHLORIDE.value, 0.0)
        effects['corrosion_acceleration'] = chloride * 0.01
        
        return effects
    
    def _calculate_mass_balance(self, state: ChemistryFlowState) -> None:
        """Calculate mass balance for each chemical species"""
        # Simplified mass balance calculation
        # In a real implementation, this would track actual mass flows
        
        for species in ChemicalSpecies:
            species_name = species.value
            
            # Input sources
            makeup_input = state.makeup_water_chemistry.get(species_name, 0.0) * 0.1  # kg/s
            chemical_addition = state.chemical_addition_rates.get(species_name, 0.0)
            total_input = makeup_input + chemical_addition
            
            # Output sinks
            blowdown_loss = state.sg_liquid_chemistry.get(species_name, 0.0) * 0.02  # kg/s
            steam_carryover = state.sg_steam_carryover.get(species_name, 0.0) * 0.001
            total_output = blowdown_loss + steam_carryover
            
            # Balance calculation
            balance_error = total_input - total_output
            balance_percent = (balance_error / total_input * 100.0) if total_input > 0 else 0.0
            
            state.total_chemistry_input[species_name] = total_input
            state.total_chemistry_output[species_name] = total_output
            state.chemistry_balance_error[species_name] = balance_error
            state.chemistry_balance_percent_error[species_name] = balance_percent
    
    def _calculate_performance_metrics(self, state: ChemistryFlowState) -> None:
        """Calculate overall performance metrics"""
        # Chemistry stability (based on pH control and other factors)
        ph = state.feedwater_chemistry.get(ChemicalSpecies.PH.value, 9.2)
        ph_stability = 1.0 - abs(ph - 9.2) / 2.0
        
        # Treatment effectiveness
        chlorine_effectiveness = min(1.0, state.feedwater_chemistry.get(ChemicalSpecies.CHLORINE.value, 0.0) / 0.5)
        
        state.overall_chemistry_stability = (ph_stability + chlorine_effectiveness) / 2.0
        state.overall_chemistry_stability = np.clip(state.overall_chemistry_stability, 0.0, 1.0)
        
        # Fouling impact on efficiency
        total_fouling = state.tsp_fouling_rate + state.condenser_fouling_rate
        state.fouling_impact_on_efficiency = min(5.0, total_fouling * 100.0)  # % efficiency loss
        
        # Treatment cost (simplified)
        chemical_consumption = sum(state.chemical_addition_rates.values())
        state.treatment_cost_rate = chemical_consumption * 10.0  # $/hour
    
    def validate_chemistry_balance(self) -> Dict[str, Any]:
        """
        Validate chemistry mass balance and identify discrepancies with alarms and corrections
        
        Returns:
            Dictionary with validation results including alarms and correction actions
        """
        state = self.chemistry_flow_state
        
        # Overall balance validation
        total_errors = sum(abs(error) for error in state.chemistry_balance_error.values())
        total_inputs = sum(state.total_chemistry_input.values())
        
        overall_error_percent = (total_errors / total_inputs * 100.0) if total_inputs > 0 else 0.0
        
        # Find species with largest imbalances
        largest_error_species = max(
            state.chemistry_balance_percent_error.items(),
            key=lambda x: abs(x[1])
        ) if state.chemistry_balance_percent_error else ("none", 0.0)
        
        # ENHANCED: Check chemistry balance alarms and generate corrections
        alarms = self._check_chemistry_alarms(state, overall_error_percent)
        corrections = self._generate_chemistry_corrections(state, overall_error_percent)
        
        validation = {
            'overall_balance_error_percent': overall_error_percent,
            'balance_acceptable': overall_error_percent < (self.validation_tolerance * 100),
            'total_input_kg_per_s': total_inputs,
            'total_error_kg_per_s': total_errors,
            'largest_error_species': largest_error_species[0],
            'largest_error_percent': largest_error_species[1],
            'species_balances': state.chemistry_balance_percent_error.copy(),
            'ph_control_status': state.ph_control_status,
            'chemistry_stability': state.overall_chemistry_stability,
            'fouling_rates': {
                'tsp_fouling': state.tsp_fouling_rate,
                'condenser_fouling': state.condenser_fouling_rate,
                'turbine_fouling': state.turbine_fouling_rate
            },
            # ENHANCED: Add alarm and correction information
            'chemistry_alarms': alarms,
            'chemistry_corrections': corrections,
            'alarm_count': len([alarm for alarm in alarms.values() if alarm]),
            'correction_count': len([corr for corr in corrections.values() if corr['action_required']]),
            'system_health_status': self._calculate_system_health_status(overall_error_percent, alarms)
        }
        
        return validation
    
    def _check_chemistry_alarms(self, state: ChemistryFlowState, overall_error_percent: float) -> Dict[str, bool]:
        """
        Check for chemistry balance alarms and operational limits
        
        Args:
            state: Current chemistry flow state
            overall_error_percent: Overall balance error percentage
            
        Returns:
            Dictionary with alarm status for each monitored parameter
        """
        alarms = {}
        
        # === MASS BALANCE ALARMS ===
        # High overall balance error
        alarms['chemistry_balance_high'] = overall_error_percent > 5.0
        alarms['chemistry_balance_critical'] = overall_error_percent > 10.0
        
        # Individual species imbalance alarms
        for species, error_percent in state.chemistry_balance_percent_error.items():
            abs_error = abs(error_percent)
            alarms[f'{species}_imbalance_high'] = abs_error > 10.0
            alarms[f'{species}_imbalance_critical'] = abs_error > 20.0
        
        # === CHEMISTRY PARAMETER ALARMS ===
        # pH alarms (critical for plant operation)
        sg_ph = state.sg_liquid_chemistry.get(ChemicalSpecies.PH.value, 9.2)
        alarms['ph_low'] = sg_ph < 8.8
        alarms['ph_high'] = sg_ph > 9.6
        alarms['ph_critical_low'] = sg_ph < 8.5
        alarms['ph_critical_high'] = sg_ph > 10.0
        
        # Iron concentration alarms (fouling concern)
        iron_conc = state.sg_liquid_chemistry.get(ChemicalSpecies.IRON.value, 0.1)
        alarms['iron_high'] = iron_conc > 0.2  # ppm
        alarms['iron_critical'] = iron_conc > 0.5  # ppm
        
        # Copper concentration alarms (fouling concern)
        copper_conc = state.sg_liquid_chemistry.get(ChemicalSpecies.COPPER.value, 0.05)
        alarms['copper_high'] = copper_conc > 0.1  # ppm
        alarms['copper_critical'] = copper_conc > 0.2  # ppm
        
        # === FOULING RATE ALARMS ===
        # TSP fouling rate alarm
        alarms['tsp_fouling_high'] = state.tsp_fouling_rate > 0.01  # kg/m²/year
        alarms['tsp_fouling_critical'] = state.tsp_fouling_rate > 0.02  # kg/m²/year
        
        # Condenser fouling alarm
        alarms['condenser_fouling_high'] = state.condenser_fouling_rate > 0.005
        alarms['condenser_fouling_critical'] = state.condenser_fouling_rate > 0.01
        
        # === CHEMISTRY STABILITY ALARMS ===
        # Overall chemistry stability
        alarms['chemistry_stability_low'] = state.overall_chemistry_stability < 0.8
        alarms['chemistry_stability_critical'] = state.overall_chemistry_stability < 0.6
        
        # Treatment effectiveness alarms
        treatment_eff = state.feedwater_treatment_effectiveness
        alarms['treatment_effectiveness_low'] = treatment_eff < 0.8
        alarms['treatment_effectiveness_critical'] = treatment_eff < 0.6
        
        # === CONTROL SYSTEM ALARMS ===
        # pH control system status
        alarms['ph_control_failed'] = state.ph_control_status == "FAILED"
        alarms['ph_control_manual'] = state.ph_control_status == "MANUAL"
        
        return alarms
    
    def _generate_chemistry_corrections(self, state: ChemistryFlowState, overall_error_percent: float) -> Dict[str, Dict[str, Any]]:
        """
        Generate automatic chemistry corrections for detected imbalances
        
        Args:
            state: Current chemistry flow state
            overall_error_percent: Overall balance error percentage
            
        Returns:
            Dictionary with correction actions for each detected issue
        """
        corrections = {}
        
        # === MASS BALANCE CORRECTIONS ===
        if overall_error_percent > 5.0:
            corrections['mass_balance'] = {
                'action_required': True,
                'correction_type': 'chemical_dosing_adjustment',
                'description': f'Adjust chemical dosing rates to reduce {overall_error_percent:.1f}% mass balance error',
                'target_adjustment': min(0.2, overall_error_percent * 0.02),  # Proportional adjustment
                'priority': 'high' if overall_error_percent > 10.0 else 'medium'
            }
        else:
            corrections['mass_balance'] = {'action_required': False}
        
        # === pH CORRECTIONS ===
        sg_ph = state.sg_liquid_chemistry.get(ChemicalSpecies.PH.value, 9.2)
        if abs(sg_ph - 9.2) > 0.1:  # Outside normal operating band
            ph_error = sg_ph - 9.2
            corrections['ph_control'] = {
                'action_required': True,
                'correction_type': 'ph_adjustment',
                'description': f'Adjust pH from {sg_ph:.2f} to target 9.2',
                'ph_error': ph_error,
                'recommended_action': 'increase_ammonia_dose' if ph_error < 0 else 'decrease_ammonia_dose',
                'dose_adjustment': abs(ph_error) * 0.5,  # kg/hr adjustment
                'priority': 'critical' if abs(ph_error) > 0.3 else 'high'
            }
        else:
            corrections['ph_control'] = {'action_required': False}
        
        # === FOULING CORRECTIONS ===
        if state.tsp_fouling_rate > 0.01:  # High TSP fouling rate
            corrections['tsp_fouling'] = {
                'action_required': True,
                'correction_type': 'fouling_mitigation',
                'description': f'Reduce TSP fouling rate from {state.tsp_fouling_rate:.4f} kg/m²/year',
                'recommended_actions': [
                    'increase_blowdown_rate',
                    'optimize_ph_control',
                    'schedule_chemical_cleaning'
                ],
                'blowdown_increase': min(0.01, state.tsp_fouling_rate * 0.5),  # Increase blowdown
                'priority': 'high'
            }
        else:
            corrections['tsp_fouling'] = {'action_required': False}
        
        # === IRON/COPPER CORRECTIONS ===
        iron_conc = state.sg_liquid_chemistry.get(ChemicalSpecies.IRON.value, 0.1)
        if iron_conc > 0.2:  # High iron concentration
            corrections['iron_control'] = {
                'action_required': True,
                'correction_type': 'iron_reduction',
                'description': f'Reduce iron concentration from {iron_conc:.3f} ppm',
                'recommended_actions': [
                    'increase_blowdown_rate',
                    'improve_feedwater_quality',
                    'check_pump_wear'
                ],
                'target_concentration': 0.1,  # ppm
                'priority': 'medium'
            }
        else:
            corrections['iron_control'] = {'action_required': False}
        
        copper_conc = state.sg_liquid_chemistry.get(ChemicalSpecies.COPPER.value, 0.05)
        if copper_conc > 0.1:  # High copper concentration
            corrections['copper_control'] = {
                'action_required': True,
                'correction_type': 'copper_reduction',
                'description': f'Reduce copper concentration from {copper_conc:.3f} ppm',
                'recommended_actions': [
                    'increase_blowdown_rate',
                    'check_condenser_tubes',
                    'optimize_water_treatment'
                ],
                'target_concentration': 0.05,  # ppm
                'priority': 'medium'
            }
        else:
            corrections['copper_control'] = {'action_required': False}
        
        # === TREATMENT EFFECTIVENESS CORRECTIONS ===
        treatment_eff = state.feedwater_treatment_effectiveness
        if treatment_eff < 0.8:  # Low treatment effectiveness
            corrections['treatment_system'] = {
                'action_required': True,
                'correction_type': 'treatment_optimization',
                'description': f'Improve treatment effectiveness from {treatment_eff:.1%}',
                'recommended_actions': [
                    'check_chemical_supply_levels',
                    'calibrate_dosing_systems',
                    'perform_system_maintenance'
                ],
                'target_effectiveness': 0.95,
                'priority': 'high'
            }
        else:
            corrections['treatment_system'] = {'action_required': False}
        
        # === AUTOMATIC CORRECTION IMPLEMENTATION ===
        # Generate automatic correction commands for critical issues
        auto_corrections = self._generate_automatic_corrections(corrections)
        if auto_corrections:
            corrections['automatic_actions'] = {
                'action_required': True,
                'correction_type': 'automatic_implementation',
                'description': 'Automatic corrections implemented',
                'actions_taken': auto_corrections,
                'priority': 'system'
            }
        
        return corrections
    
    def _generate_automatic_corrections(self, corrections: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Generate automatic correction commands for critical chemistry issues
        
        Args:
            corrections: Dictionary of correction recommendations
            
        Returns:
            List of automatic actions taken
        """
        auto_actions = []
        
        # Automatic pH correction for critical deviations
        if corrections.get('ph_control', {}).get('priority') == 'critical':
            ph_correction = corrections['ph_control']
            if ph_correction['ph_error'] < -0.3:  # Very low pH
                auto_actions.append('emergency_ammonia_dose_increase')
            elif ph_correction['ph_error'] > 0.3:  # Very high pH
                auto_actions.append('emergency_ammonia_dose_decrease')
        
        # Automatic blowdown increase for high fouling rates
        if corrections.get('tsp_fouling', {}).get('priority') == 'high':
            auto_actions.append('automatic_blowdown_increase')
        
        # Automatic treatment system reset for critical effectiveness loss
        if corrections.get('treatment_system', {}).get('priority') == 'high':
            auto_actions.append('treatment_system_reset')
        
        return auto_actions
    
    def _calculate_system_health_status(self, overall_error_percent: float, alarms: Dict[str, bool]) -> str:
        """
        Calculate overall system health status based on chemistry parameters
        
        Args:
            overall_error_percent: Overall balance error percentage
            alarms: Dictionary of active alarms
            
        Returns:
            System health status string
        """
        # Count critical and high priority alarms
        critical_alarms = sum(1 for key, active in alarms.items() if active and 'critical' in key)
        high_alarms = sum(1 for key, active in alarms.items() if active and ('high' in key or key in ['ph_low', 'ph_high']))
        
        # Determine health status
        if critical_alarms > 0:
            return 'CRITICAL'
        elif high_alarms > 2 or overall_error_percent > 10.0:
            return 'DEGRADED'
        elif high_alarms > 0 or overall_error_percent > 5.0:
            return 'CAUTION'
        else:
            return 'NORMAL'
    
    def get_chemistry_flow_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive chemistry flow summary
        
        Returns:
            Dictionary with all chemistry flow data
        """
        state = self.chemistry_flow_state
        validation = self.validate_chemistry_balance()
        
        return {
            # Primary chemistry parameters
            'sg_ph': state.sg_liquid_chemistry.get(ChemicalSpecies.PH.value, 9.2),
            'sg_iron_concentration': state.sg_liquid_chemistry.get(ChemicalSpecies.IRON.value, 0.1),
            'sg_copper_concentration': state.sg_liquid_chemistry.get(ChemicalSpecies.COPPER.value, 0.05),
            'feedwater_ph': state.feedwater_chemistry.get(ChemicalSpecies.PH.value, 9.2),
            
            # Control system status
            'ph_control_status': state.ph_control_status,
            'oxygen_control_status': state.oxygen_control_status,
            'biocide_control_status': state.biocide_control_status,
            
            # Fouling and degradation
            'tsp_fouling_rate': state.tsp_fouling_rate,
            'condenser_fouling_rate': state.condenser_fouling_rate,
            'turbine_fouling_rate': state.turbine_fouling_rate,
            'carbon_steel_corrosion_rate': state.corrosion_rates.get('carbon_steel', 0.0),
            
            # Performance metrics
            'chemistry_stability': state.overall_chemistry_stability,
            'treatment_cost_rate': state.treatment_cost_rate,
            'fouling_efficiency_impact': state.fouling_impact_on_efficiency,
            
            # Mass balance validation
            'chemistry_balance_error_percent': validation['overall_balance_error_percent'],
            'chemistry_balance_ok': validation['balance_acceptable'],
            'largest_imbalance_species': validation['largest_error_species'],
            
            # Chemical supply levels
            'ammonia_supply_level': state.chemical_supply_levels.get(ChemicalSpecies.AMMONIA.value, 80.0),
            'morpholine_supply_level': state.chemical_supply_levels.get(ChemicalSpecies.MORPHOLINE.value, 80.0),
            'chlorine_supply_level': state.chemical_supply_levels.get(ChemicalSpecies.CHLORINE.value, 80.0),
            
            # Steam carryover
            'steam_iron_carryover': state.sg_steam_carryover.get(ChemicalSpecies.IRON.value, 0.0),
            'steam_copper_carryover': state.sg_steam_carryover.get(ChemicalSpecies.COPPER.value, 0.0),
            'steam_ammonia_carryover': state.sg_steam_carryover.get(ChemicalSpecies.AMMONIA.value, 0.0)
        }
    
    def add_to_history(self, timestamp: float) -> None:
        """Add current state to historical data"""
        history_entry = {
            'timestamp': timestamp,
            'chemistry_flows': self.get_chemistry_flow_summary(),
            'component_chemistry': self.component_chemistry.copy()
        }
        self.chemistry_history.append(history_entry)
        
        # Limit history size
        if len(self.chemistry_history) > 1000:
            self.chemistry_history = self.chemistry_history[-1000:]
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state = self.chemistry_flow_state
        
        return {
            # Mass balance tracking
            'chemistry_flow_total_input': sum(state.total_chemistry_input.values()),
            'chemistry_flow_total_output': sum(state.total_chemistry_output.values()),
            'chemistry_flow_balance_error': sum(abs(e) for e in state.chemistry_balance_error.values()),
            
            # Major chemistry parameters
            'chemistry_flow_sg_ph': state.sg_liquid_chemistry.get(ChemicalSpecies.PH.value, 9.2),
            'chemistry_flow_sg_iron': state.sg_liquid_chemistry.get(ChemicalSpecies.IRON.value, 0.1),
            'chemistry_flow_sg_copper': state.sg_liquid_chemistry.get(ChemicalSpecies.COPPER.value, 0.05),
            'chemistry_flow_feedwater_ph': state.feedwater_chemistry.get(ChemicalSpecies.PH.value, 9.2),
            
            # Control system status (encoded as numbers for state tracking)
            'chemistry_flow_ph_control_auto': 1.0 if state.ph_control_status == "AUTO" else 0.0,
            'chemistry_flow_oxygen_control_auto': 1.0 if state.oxygen_control_status == "AUTO" else 0.0,
            
            # Fouling rates
            'chemistry_flow_tsp_fouling_rate': state.tsp_fouling_rate,
            'chemistry_flow_condenser_fouling_rate': state.condenser_fouling_rate,
            'chemistry_flow_turbine_fouling_rate': state.turbine_fouling_rate,
            
            # Performance metrics
            'chemistry_flow_stability': state.overall_chemistry_stability,
            'chemistry_flow_treatment_cost': state.treatment_cost_rate,
            'chemistry_flow_efficiency_impact': state.fouling_impact_on_efficiency
        }
    
    def reset(self) -> None:
        """Reset chemistry flow tracker to initial state"""
        self.chemistry_flow_state = ChemistryFlowState()
        self.component_chemistry = {}
        self.chemistry_history = []
        self._initialize_default_chemistry()


# Example usage and testing
if __name__ == "__main__":
    print("Chemistry Flow Tracking System - Validation Test")
    print("=" * 50)
    
    # Create chemistry flow tracker
    tracker = ChemistryFlowTracker()
    
    # Simulate component chemistry for a typical PWR
    # Steam Generator
    sg_chemistry = {
        ChemicalSpecies.PH.value: 9.15,
        ChemicalSpecies.IRON.value: 0.12,
        ChemicalSpecies.COPPER.value: 0.06,
        ChemicalSpecies.SILICA.value: 22.0,
        ChemicalSpecies.CHLORIDE.value: 52.0,
        ChemicalSpecies.AMMONIA.value: 2.0
    }
    tracker.update_component_chemistry('steam_generator', sg_chemistry)
    
    # Turbine
    turbine_chemistry = {
        ChemicalSpecies.PH.value: 9.1,
        ChemicalSpecies.AMMONIA.value: 1.6,  # Some carryover
        ChemicalSpecies.IRON.value: 0.001,   # Minimal carryover
        ChemicalSpecies.COPPER.value: 0.001
    }
    tracker.update_component_chemistry('turbine', turbine_chemistry)
    
    # Condenser
    condenser_chemistry = {
        ChemicalSpecies.PH.value: 8.9,
        ChemicalSpecies.CHLORINE.value: 0.3,
        ChemicalSpecies.HARDNESS.value: 160.0,
        ChemicalSpecies.TDS.value: 520.0
    }
    tracker.update_component_chemistry('condenser', condenser_chemistry)
    
    # Feedwater System
    fw_chemistry = {
        ChemicalSpecies.PH.value: 9.18,
        ChemicalSpecies.IRON.value: 0.08,
        ChemicalSpecies.COPPER.value: 0.04,
        ChemicalSpecies.HYDRAZINE.value: 0.1,
        ChemicalSpecies.AMMONIA.value: 1.8
    }
    tracker.update_component_chemistry('feedwater', fw_chemistry)
    
    # Calculate system chemistry flows
    state = tracker.calculate_system_chemistry_flows()
    validation = tracker.validate_chemistry_balance()
    summary = tracker.get_chemistry_flow_summary()
    
    print(f"System Chemistry Flow Analysis:")
    print(f"  Steam Generator pH: {state.sg_liquid_chemistry.get(ChemicalSpecies.PH.value, 0.0):.2f}")
    print(f"  Feedwater pH: {state.feedwater_chemistry.get(ChemicalSpecies.PH.value, 0.0):.2f}")
    print(f"  Chemistry Balance OK: {validation['balance_acceptable']}")
    print(f"  Overall Error: {validation['overall_balance_error_percent']:.2f}%")
    print()
    
    print(f"Fouling Rates:")
    print(f"  TSP Fouling: {state.tsp_fouling_rate:.4f} kg/m²/year")
    print(f"  Condenser Fouling: {state.condenser_fouling_rate:.4f} factor/year")
    print(f"  Turbine Fouling: {state.turbine_fouling_rate:.4f} %/year")
    print()
    
    print(f"Corrosion Rates:")
    for material, rate in state.corrosion_rates.items():
        print(f"  {material.replace('_', ' ').title()}: {rate:.3f} mm/year")
    print()
    
    print(f"Performance Metrics:")
    print(f"  Chemistry Stability: {state.overall_chemistry_stability:.1%}")
    print(f"  Treatment Cost: ${state.treatment_cost_rate:.1f}/hour")
    print(f"  Efficiency Impact: {state.fouling_impact_on_efficiency:.2f}%")
    print()
    
    print(f"Control System Status:")
    print(f"  pH Control: {state.ph_control_status}")
    print(f"  Oxygen Control: {state.oxygen_control_status}")
    print(f"  Biocide Control: {state.biocide_control_status}")
    
    print("\nChemistry flow tracking system ready for integration!")
