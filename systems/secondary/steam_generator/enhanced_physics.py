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
from simulator.state import auto_register

# Import heat flow tracking
from ..heat_flow_tracker import HeatFlowProvider, ThermodynamicProperties

# Import chemistry flow tracking
from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies

from .steam_generator import SteamGenerator
from .config import SteamGeneratorConfig
from ..water_chemistry import WaterChemistry, WaterChemistryConfig
from ..component_descriptions import STEAM_GENERATOR_COMPONENT_DESCRIPTIONS


@auto_register("SECONDARY", "steam_generator", allow_no_id=True,
               description=STEAM_GENERATOR_COMPONENT_DESCRIPTIONS['enhanced_steam_generator_physics'])
class EnhancedSteamGeneratorPhysics(HeatFlowProvider, ChemistryFlowProvider):
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
    
    Uses @auto_register decorator for automatic state collection with proper naming.
    """
    
    def __init__(self, config: Optional[SteamGeneratorConfig] = None, water_chemistry: Optional[WaterChemistry] = None):
        """Initialize enhanced steam generator physics model"""
        if config is None:
            # Create default SteamGeneratorConfig if none provided
            from .config import create_standard_sg_config
            config = create_standard_sg_config()
        
        self.config = config
        
        # Initialize or use provided unified water chemistry system
        if water_chemistry is not None:
            self.water_chemistry = water_chemistry
        else:
            # Create own instance if not provided (for standalone use)
            self.water_chemistry = WaterChemistry(WaterChemistryConfig())
        
        # Initialize individual steam generators with shared water chemistry
        # Simply pass the main config to each SG - they can extract their individual parameters
        self.steam_generators = []
        for i in range(config.num_steam_generators):
            # Create a copy of the config with a unique system_id for this SG
            sg_config = SteamGeneratorConfig(
                system_id=f"SG-{i}",
                num_steam_generators=config.num_steam_generators,
                design_total_thermal_power=config.design_total_thermal_power,
                design_total_steam_flow=config.design_total_steam_flow,
                design_steam_pressure=config.design_steam_pressure,
                design_steam_temperature=config.design_steam_temperature,
                design_feedwater_temperature=config.design_feedwater_temperature,
                design_thermal_power_per_sg=config.design_thermal_power_per_sg,
                design_steam_flow_per_sg=config.design_steam_flow_per_sg,
                design_feedwater_flow_per_sg=config.design_feedwater_flow_per_sg,
                design_overall_htc=config.design_overall_htc,
                heat_transfer_area_per_sg=config.heat_transfer_area_per_sg,
                tube_count_per_sg=config.tube_count_per_sg,
                tube_inner_diameter=config.tube_inner_diameter,
                tube_wall_thickness=config.tube_wall_thickness,
                tube_outer_diameter=config.tube_outer_diameter,
                tube_length=config.tube_length,
                secondary_water_mass=config.secondary_water_mass,
                steam_dome_volume=config.steam_dome_volume,
                primary_htc=config.primary_htc,
                secondary_htc=config.secondary_htc,
                design_pressure_primary=config.design_pressure_primary,
                design_pressure_secondary=config.design_pressure_secondary,
                tube_material_conductivity=config.tube_material_conductivity,
                tube_material_density=config.tube_material_density,
                tube_material_specific_heat=config.tube_material_specific_heat,
                minimum_power_fraction=config.minimum_power_fraction,
                maximum_power_fraction=config.maximum_power_fraction,
                minimum_steam_quality=config.minimum_steam_quality,
                maximum_tube_wall_temperature=config.maximum_tube_wall_temperature,
                level_control_enabled=config.level_control_enabled,
                pressure_control_enabled=config.pressure_control_enabled,
                load_following_enabled=config.load_following_enabled,
                feedwater_control_gain=config.feedwater_control_gain,
                steam_pressure_control_gain=config.steam_pressure_control_gain,
                auto_load_balancing=config.auto_load_balancing,
                system_coordination=config.system_coordination,
                performance_optimization=config.performance_optimization,
                predictive_maintenance=config.predictive_maintenance,
                auto_pressure_control=config.auto_pressure_control,
                system_optimization=config.system_optimization,
                design_efficiency=config.design_efficiency,
                thermal_performance_factor=config.thermal_performance_factor,
                availability_factor=config.availability_factor,
                enable_chemistry_tracking=config.enable_chemistry_tracking,
                chemistry_update_interval_hours=config.chemistry_update_interval_hours,
                initial_conditions=config.initial_conditions,
                tsp_fouling=config.tsp_fouling,
                maintenance=config.maintenance
            )
            
            sg = SteamGenerator(sg_config, water_chemistry=self.water_chemistry)
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
        Streamlined enhanced steam generator system update
        
        Phase 2 Optimization: Removed redundant processing, simplified data flow.
        Focus on coordination and load balancing - let individual SGs handle physics.
        
        Args:
            primary_conditions: Primary side conditions for each SG
            steam_demands: Steam demand conditions  
            system_conditions: Overall system conditions
            control_inputs: Control system inputs
            dt: Time step (s)
            
        Returns:
            Dictionary with essential system results (streamlined)
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Phase 3: Steam Generator is Single Source of Truth for Steam Flow
        # Calculate actual steam flow based on load demand and physics, not external demand
        self.load_demand = system_conditions.get('load_demand', 1.0)
        feedwater_temperature = system_conditions.get('feedwater_temperature', 227.0)
        
        # Calculate actual steam flow based on load demand and design capacity
        load_demand_fraction = steam_demands.get('load_demand_fraction', self.load_demand)
        actual_total_steam_flow = self.config.design_total_steam_flow * load_demand_fraction
        
        # Simplified load distribution (core coordination function)
        individual_demands = self._calculate_load_distribution(actual_total_steam_flow, primary_conditions)
        
        # Update unified water chemistry system if conditions provided
        if 'water_chemistry_update' in system_conditions:
            self.water_chemistry.update_chemistry(
                system_conditions['water_chemistry_update'],
                dt / 60.0  # Convert seconds to hours
            )
        
        # Direct update of individual steam generators (minimal wrapper processing)
        sg_results = []

        for i, sg in enumerate(self.steam_generators):
            # Prepare system conditions for individual SG (include water chemistry update if provided)
            sg_system_conditions = None
            if 'water_chemistry_update' in system_conditions:
                sg_system_conditions = {
                    'water_chemistry_update': system_conditions['water_chemistry_update']
                }
            
            # Direct parameter extraction - no redundant processing
            sg_result = sg.update_state(
                primary_temp_in=primary_conditions.get('inlet_temps', [327.0] * self.config.num_steam_generators)[i],
                primary_temp_out=primary_conditions.get('outlet_temps', [293.0] * self.config.num_steam_generators)[i],
                primary_flow=primary_conditions.get('flow_rates', [5700.0] * self.config.num_steam_generators)[i],
                steam_flow_out=individual_demands[i],
                feedwater_flow_in=individual_demands[i],  # Mass balance
                feedwater_temp=feedwater_temperature,
                dt=dt,
                system_conditions=sg_system_conditions
            )
            
            sg_results.append(sg_result)
        
        # Streamlined system aggregation (essential metrics only)
        self.total_thermal_power = sum(result['heat_transfer_rate'] for result in sg_results)
        self.total_steam_flow = sum(result['steam_flow_rate'] for result in sg_results)
        
        # Essential system state (removed redundant calculations)
        if self.steam_generators:
            self.average_steam_pressure = sum(sg.secondary_pressure for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_temperature = sum(sg.secondary_temperature for sg in self.steam_generators) / len(self.steam_generators)
            self.average_steam_quality = sum(sg.steam_quality for sg in self.steam_generators) / len(self.steam_generators)
        
        # Simplified performance tracking (removed complex metrics)
        self.system_availability = self._check_system_availability(sg_results)
        self.operating_hours += dt / 3600.0
        
        # Streamlined return data (essential results only)
        return {
            # Core system performance
            'total_thermal_power': self.total_thermal_power,
            'total_steam_flow': self.total_steam_flow,
            'average_steam_pressure': self.average_steam_pressure,
            'average_steam_temperature': self.average_steam_temperature,
            'average_steam_quality': self.average_steam_quality,
            'system_availability': self.system_availability,
            
            # Individual SG results (essential for downstream systems)
            'sg_individual_results': sg_results,
            'sg_steam_flows': [result['steam_flow_rate'] for result in sg_results],
            'sg_pressures': [sg.secondary_pressure for sg in self.steam_generators],
            'sg_levels': [sg.water_level for sg in self.steam_generators],
            'sg_steam_qualities': [sg.steam_quality for sg in self.steam_generators],
            
            # Essential control data
            'load_demand': self.load_demand,
            'operating_hours': self.operating_hours
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
        if not self.config.auto_load_balancing:
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
    
    # Removed redundant performance calculation methods
    # Phase 2 Optimization: Let individual SGs handle their own performance metrics
    
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
        
        return state_dict
    
    def get_heat_flows(self) -> Dict[str, float]:
        """
        Get current heat flows for this component (MW) with chemistry fouling effects
        
        Returns:
            Dictionary with heat flow values in MW including fouling losses
        """
        # Calculate primary side heat input
        primary_heat_input = self.total_thermal_power / 1e6  # Convert W to MW
        
        # Calculate feedwater enthalpy input
        feedwater_temp = 227.0  # Typical feedwater temperature
        feedwater_enthalpy = ThermodynamicProperties.liquid_enthalpy(feedwater_temp)
        feedwater_enthalpy_input = ThermodynamicProperties.enthalpy_flow_mw(self.total_steam_flow, feedwater_enthalpy)
        
        # Calculate steam enthalpy output
        steam_enthalpy = ThermodynamicProperties.steam_enthalpy(
            self.average_steam_temperature, 
            self.average_steam_pressure, 
            self.average_steam_quality
        )
        steam_enthalpy_output = ThermodynamicProperties.enthalpy_flow_mw(self.total_steam_flow, steam_enthalpy)
        
        # ENHANCED: Calculate chemistry fouling effects on heat transfer
        fouling_efficiency_factor = self._calculate_fouling_efficiency_factor()
        
        # Apply fouling effects to steam generation
        fouled_steam_enthalpy_output = steam_enthalpy_output * fouling_efficiency_factor
        
        # Calculate fouling losses (energy lost due to reduced heat transfer efficiency)
        fouling_losses = steam_enthalpy_output - fouled_steam_enthalpy_output
        
        # Calculate thermal losses (base losses + fouling losses)
        base_thermal_losses = primary_heat_input * 0.02
        total_thermal_losses = base_thermal_losses + fouling_losses
        
        # Calculate heat transfer efficiency with fouling effects
        if primary_heat_input > 0:
            heat_transfer_efficiency = (fouled_steam_enthalpy_output - feedwater_enthalpy_input) / primary_heat_input
        else:
            heat_transfer_efficiency = 0.0
        
        return {
            'primary_heat_input': primary_heat_input,
            'feedwater_enthalpy_input': feedwater_enthalpy_input,
            'steam_enthalpy_output': fouled_steam_enthalpy_output,  # Reduced by fouling
            'thermal_losses': total_thermal_losses,  # Includes fouling losses
            'fouling_losses': fouling_losses,  # NEW: Chemistry-based losses
            'heat_transfer_efficiency': heat_transfer_efficiency,  # Reduced by fouling
            'fouling_efficiency_factor': fouling_efficiency_factor,  # NEW: Fouling impact
            'clean_steam_enthalpy_output': steam_enthalpy_output  # NEW: What it would be without fouling
        }
    
    def _calculate_fouling_efficiency_factor(self) -> float:
        """
        Calculate efficiency reduction factor due to TSP fouling and chemistry effects
        
        Returns:
            Efficiency factor (0.0-1.0) where 1.0 = no fouling, lower = more fouling
        """
        # Get TSP fouling parameters from water chemistry system
        tsp_params = self.water_chemistry.get_tsp_fouling_parameters()
        
        # Calculate fouling resistance accumulation over operating time
        # Using realistic TSP fouling rates from chemistry system
        
        # Iron fouling (magnetite formation)
        iron_concentration = tsp_params['iron_concentration']  # ppm
        iron_fouling_rate = iron_concentration * 1.5 * 0.001  # kg/m²/year (from config)
        
        # Copper fouling (copper deposits)
        copper_concentration = tsp_params['copper_concentration']  # ppm
        copper_fouling_rate = copper_concentration * 2.0 * 0.001  # kg/m²/year
        
        # Silica fouling (silica scale)
        silica_concentration = tsp_params['silica_concentration']  # ppm
        silica_fouling_rate = silica_concentration * 1.8 * 0.001  # kg/m²/year
        
        # Total fouling rate
        total_fouling_rate = iron_fouling_rate + copper_fouling_rate + silica_fouling_rate
        
        # Convert fouling rate to thermal resistance accumulation
        # Typical fouling thermal resistance: 0.0001 m²K/W per kg/m²
        fouling_resistance_rate = total_fouling_rate * 0.0001  # m²K/W per year
        
        # Accumulate fouling resistance over operating time
        operating_years = self.operating_hours / 8760.0  # Convert hours to years
        accumulated_fouling_resistance = fouling_resistance_rate * operating_years
        
        # Apply temperature effects (Arrhenius relationship)
        temperature_factor = np.exp((self.average_steam_temperature - 280.0) / 50.0)
        accumulated_fouling_resistance *= temperature_factor
        
        # Apply pH effects (optimal pH around 9.2)
        ph = tsp_params['ph']
        ph_factor = 1.0 + 0.5 * abs(ph - 9.2)
        accumulated_fouling_resistance *= ph_factor
        
        # Convert fouling resistance to efficiency factor
        # Typical clean heat transfer coefficient: 3000 W/m²K
        clean_htc = 3000.0  # W/m²K
        fouled_htc = 1.0 / (1.0/clean_htc + accumulated_fouling_resistance)
        
        # Efficiency factor is ratio of fouled to clean heat transfer coefficient
        efficiency_factor = fouled_htc / clean_htc
        
        # Ensure reasonable bounds (minimum 70% efficiency, maximum 100%)
        efficiency_factor = np.clip(efficiency_factor, 0.7, 1.0)
        
        return efficiency_factor
    
    def get_enthalpy_flows(self) -> Dict[str, float]:
        """
        Get current enthalpy flows for this component (MW)
        
        Returns:
            Dictionary with enthalpy flow values in MW
        """
        heat_flows = self.get_heat_flows()
        
        return {
            'inlet_enthalpy_flow': heat_flows['feedwater_enthalpy_input'],
            'outlet_enthalpy_flow': heat_flows['steam_enthalpy_output'],
            'enthalpy_added': heat_flows['steam_enthalpy_output'] - heat_flows['feedwater_enthalpy_input'],
            'primary_heat_input': heat_flows['primary_heat_input'],
            'thermal_efficiency': heat_flows['heat_transfer_efficiency']
        }
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data
        """
        # Get water chemistry flows from the integrated water quality system
        water_chemistry_flows = self.water_chemistry.get_chemistry_flows()
        
        # Add steam generator-specific chemistry flows
        sg_flows = {
            'sg_liquid_chemistry': {
                ChemicalSpecies.PH.value: self.water_chemistry.ph,
                ChemicalSpecies.IRON.value: self.water_chemistry.iron_concentration,
                ChemicalSpecies.COPPER.value: self.water_chemistry.copper_concentration,
                ChemicalSpecies.SILICA.value: self.water_chemistry.silica_concentration,
                ChemicalSpecies.DISSOLVED_OXYGEN.value: self.water_chemistry.dissolved_oxygen,
                ChemicalSpecies.HARDNESS.value: self.water_chemistry.hardness,
                ChemicalSpecies.CHLORIDE.value: self.water_chemistry.chloride,
                ChemicalSpecies.TDS.value: self.water_chemistry.total_dissolved_solids
            },
            'sg_steam_carryover': {
                # Calculate steam carryover for each species
                ChemicalSpecies.IRON.value: self.water_chemistry.iron_concentration * 0.001,  # Very low carryover
                ChemicalSpecies.COPPER.value: self.water_chemistry.copper_concentration * 0.001,
                ChemicalSpecies.SILICA.value: self.water_chemistry.silica_concentration * 0.02,  # Higher carryover
                ChemicalSpecies.AMMONIA.value: self.water_chemistry.antiscalant_concentration * 0.8  # High volatility
            }
        }
        
        # Combine flows
        combined_flows = {}
        combined_flows.update(water_chemistry_flows)
        combined_flows.update(sg_flows)
        
        return combined_flows
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state for chemistry flow tracker
        
        Returns:
            Dictionary with current chemistry concentrations
        """
        return self.water_chemistry.get_chemistry_state()
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update steam generator system based on chemistry state feedback
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Pass chemistry effects to the water quality system
        self.water_chemistry.update_chemistry_effects(chemistry_state)
        
        # Apply chemistry effects to steam generator performance if needed
        if 'water_aggressiveness' in chemistry_state:
            aggressiveness = chemistry_state['water_aggressiveness']
            # Reduce performance factor based on water aggressiveness (fouling effects)
            chemistry_performance_factor = max(0.7, 1.0 - (aggressiveness - 1.0) * 0.05)
            self.performance_factor *= chemistry_performance_factor
        
        # Apply TSP fouling effects if available
        if 'tsp_fouling_rate' in chemistry_state:
            fouling_rate = chemistry_state['tsp_fouling_rate']
            # Reduce efficiency based on fouling rate
            fouling_efficiency_factor = max(0.8, 1.0 - fouling_rate * 0.1)
            self.system_efficiency *= fouling_efficiency_factor
    
    def setup_maintenance_integration(self, maintenance_system):
        """
        Set up maintenance integration for the entire steam generator system
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
        """
        print(f"STEAM GENERATOR SYSTEM: Setting up maintenance integration")
        
        # Set up individual steam generator maintenance integration
        for i, sg in enumerate(self.steam_generators):
            component_id = f"SG-{i}"
            sg.setup_maintenance_integration(maintenance_system, component_id)
        
        # Register enhanced system controller for system-level coordination
        system_monitoring_config = {
            'system_availability': {
                'attribute': 'system_availability',
                'threshold': 0.5,  # System availability below 50%
                'comparison': 'less_than',
                'action': 'system_coordination_maintenance',
                'cooldown_hours': 24.0
            },
            'average_steam_quality': {
                'attribute': 'average_steam_quality',
                'threshold': 0.98,  # Average quality below 98%
                'comparison': 'less_than',
                'action': 'system_steam_quality_maintenance',
                'cooldown_hours': 48.0
            },
            'load_balance_factor': {
                'attribute': 'load_balance_factor',
                'threshold': 0.8,  # Poor load balancing
                'comparison': 'less_than',
                'action': 'load_balancing_maintenance',
                'cooldown_hours': 72.0
            }
        }
        
        maintenance_system.register_component("SG-SYSTEM", self, system_monitoring_config)
        print(f"  Registered SG-SYSTEM controller for system-level coordination")
        
        # Store reference for coordination
        self.maintenance_system = maintenance_system
        
        # Subscribe to system-level maintenance events
        maintenance_system.event_bus.subscribe('maintenance_completed', self._handle_maintenance_completed)
        maintenance_system.event_bus.subscribe('maintenance_scheduled', self._handle_maintenance_scheduled)
        
        print(f"STEAM GENERATOR SYSTEM: Maintenance integration complete")
        print(f"  Total registered components: {len(self.steam_generators) + 1}")
    
    def _handle_maintenance_completed(self, event):
        """Handle maintenance completion events for system coordination"""
        component_id = event.component_id
        maintenance_data = event.data
        
        # Update system performance based on completed maintenance
        if maintenance_data.get('success', False):
            effectiveness = maintenance_data.get('effectiveness_score', 0.8)
            
            # Improve system performance factor
            self.performance_factor = min(1.0, self.performance_factor + effectiveness * 0.02)
            
            # If individual SG maintenance completed, check if system coordination needed
            if component_id.startswith('SG-') and component_id != 'SG-SYSTEM':
                self._check_system_coordination_after_maintenance()
            
            print(f"SG SYSTEM: Maintenance completed on {component_id}, "
                  f"system performance factor: {self.performance_factor:.3f}")
    
    def _handle_maintenance_scheduled(self, event):
        """Handle maintenance scheduling events for system coordination"""
        component_id = event.component_id
        maintenance_data = event.data
        
        # Check if maintenance would affect system availability
        if component_id.startswith('SG-') and component_id != 'SG-SYSTEM':
            # Count how many SGs are currently under maintenance or scheduled
            maintenance_count = self._count_sgs_under_maintenance()
            
            # If too many SGs would be offline, coordinate scheduling
            if maintenance_count >= 2:  # More than 1 SG under maintenance
                print(f"SG SYSTEM: Coordinating maintenance - {maintenance_count} SGs affected")
                self._coordinate_maintenance_scheduling(component_id, maintenance_data)
    
    def _count_sgs_under_maintenance(self) -> int:
        """Count how many steam generators are currently under maintenance"""
        # This would check with the maintenance system for active work orders
        # For now, simplified implementation
        maintenance_count = 0
        
        if hasattr(self, 'maintenance_system'):
            for i in range(self.config.num_steam_generators):
                sg_id = f"SG-{i}"
                # Check if there are active work orders for this SG
                active_orders = [wo for wo in self.maintenance_system.work_order_manager.work_orders.values()
                               if wo.component_id == sg_id and wo.status.value in ['in_progress', 'scheduled']]
                if active_orders:
                    maintenance_count += 1
        
        return maintenance_count
    
    def _check_system_coordination_after_maintenance(self):
        """Check if system coordination is needed after individual SG maintenance"""
        # Recalculate load balance factor
        if self.steam_generators:
            # Check performance variation across SGs
            sg_performances = []
            for sg in self.steam_generators:
                # Estimate SG performance based on TSP fouling and steam quality
                tsp_performance = 1.0 - sg.tsp_fouling.heat_transfer_degradation
                quality_performance = sg.steam_quality / 0.999  # Normalized to design
                sg_performance = (tsp_performance + quality_performance) / 2.0
                sg_performances.append(sg_performance)
            
            # Calculate load balance factor (lower variance = better balance)
            if len(sg_performances) > 1:
                avg_performance = sum(sg_performances) / len(sg_performances)
                variance = sum((p - avg_performance) ** 2 for p in sg_performances) / len(sg_performances)
                self.load_balance_factor = max(0.5, 1.0 - variance * 5.0)  # Scale variance to factor
    
    def _coordinate_maintenance_scheduling(self, component_id: str, maintenance_data: Dict):
        """Coordinate maintenance scheduling to maintain system availability"""
        print(f"SG SYSTEM: Coordinating maintenance for {component_id}")
        
        # This would implement intelligent scheduling logic
        # For now, just log the coordination attempt
        maintenance_type = maintenance_data.get('maintenance_type', 'unknown')
        priority = maintenance_data.get('priority', 'MEDIUM')
        
        if priority == 'HIGH':
            print(f"  HIGH priority {maintenance_type} - allowing immediate scheduling")
        else:
            print(f"  MEDIUM/LOW priority {maintenance_type} - deferring to maintain availability")
    
    def perform_maintenance(self, maintenance_type: str = None, **kwargs):
        """
        Perform maintenance operations on steam generator system
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        if maintenance_type == "system_coordination_maintenance":
            # Perform system-level coordination maintenance
            # Reset system availability and performance factors
            self.system_availability = True
            self.performance_factor = min(1.0, self.performance_factor + 0.1)
            self.load_balance_factor = min(1.0, self.load_balance_factor + 0.1)
            
            return {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'System coordination maintenance completed',
                'findings': 'Restored system availability and coordination',
                'effectiveness_score': 0.9,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['System coordination software update']
            }
        
        elif maintenance_type == "system_steam_quality_maintenance":
            # Perform system-wide steam quality maintenance
            quality_improvements = []
            
            for i, sg in enumerate(self.steam_generators):
                if sg.steam_quality < 0.99:
                    # Perform moisture separator maintenance on affected SGs
                    result = sg.perform_maintenance("moisture_separator_maintenance")
                    if result.get('success', False):
                        quality_improvements.append(f"SG-{i}")
            
            if quality_improvements:
                findings = f"Improved steam quality on {', '.join(quality_improvements)}"
                effectiveness = len(quality_improvements) / len(self.steam_generators)
            else:
                findings = "No steam quality issues found"
                effectiveness = 1.0
            
            return {
                'success': True,
                'duration_hours': 6.0 * len(quality_improvements),
                'work_performed': 'System-wide steam quality maintenance',
                'findings': findings,
                'effectiveness_score': effectiveness,
                'next_maintenance_due': 4380.0,  # Semi-annual
                'parts_used': ['Moisture separator components'] if quality_improvements else []
            }
        
        elif maintenance_type == "load_balancing_maintenance":
            # Perform load balancing maintenance
            # Identify SGs with performance issues
            performance_issues = []
            
            for i, sg in enumerate(self.steam_generators):
                if sg.tsp_fouling.heat_transfer_degradation > 0.05:  # More than 5% degradation
                    performance_issues.append(f"SG-{i}")
            
            # Perform maintenance on worst performing SGs
            maintenance_results = []
            for sg_id in performance_issues[:2]:  # Limit to 2 SGs to maintain availability
                sg_index = int(sg_id.split('-')[1])
                sg = self.steam_generators[sg_index]
                result = sg.perform_maintenance("tsp_chemical_cleaning")
                if result.get('success', False):
                    maintenance_results.append(sg_id)
            
            # Update load balance factor
            self.load_balance_factor = min(1.0, self.load_balance_factor + 0.2)
            
            if maintenance_results:
                findings = f"Performed load balancing maintenance on {', '.join(maintenance_results)}"
                effectiveness = len(maintenance_results) / max(1, len(performance_issues))
            else:
                findings = "Load balancing assessment completed - no immediate action needed"
                effectiveness = 0.8
            
            return {
                'success': True,
                'duration_hours': 12.0 * len(maintenance_results),
                'work_performed': 'Load balancing maintenance',
                'findings': findings,
                'effectiveness_score': effectiveness,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['TSP cleaning chemicals'] if maintenance_results else []
            }
        
        elif maintenance_type == "routine_maintenance":
            # Perform routine system maintenance
            # Minor improvements to all SGs
            for sg in self.steam_generators:
                sg.perform_maintenance("routine_maintenance")
            
            # Improve system factors slightly
            self.performance_factor = min(1.0, self.performance_factor + 0.05)
            self.load_balance_factor = min(1.0, self.load_balance_factor + 0.05)
            
            return {
                'success': True,
                'duration_hours': 8.0,
                'work_performed': 'Routine system maintenance on all steam generators',
                'findings': f'Completed routine maintenance on {len(self.steam_generators)} steam generators',
                'effectiveness_score': 0.8,
                'next_maintenance_due': 2190.0,  # Quarterly
                'parts_used': ['General maintenance supplies']
            }
        
        else:
            # Try to delegate to individual SG maintenance
            sg_index = kwargs.get('sg_index', None)
            if sg_index is not None and 0 <= sg_index < len(self.steam_generators):
                # Maintenance on specific SG
                sg = self.steam_generators[sg_index]
                return sg.perform_maintenance(maintenance_type, **kwargs)
            else:
                # Unknown maintenance type
                return {
                    'success': False,
                    'duration_hours': 0.0,
                    'work_performed': f'Unknown system maintenance type: {maintenance_type}',
                    'error_message': f'System maintenance type {maintenance_type} not supported',
                    'effectiveness_score': 0.0
                }
    
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
    
    # Create unified water chemistry system
    water_chemistry = WaterChemistry(WaterChemistryConfig())
    
    # Create enhanced steam generator system with unified water chemistry
    enhanced_sg = EnhancedSteamGeneratorPhysics(water_chemistry=water_chemistry)
    
    print(f"Created system with {enhanced_sg.config.num_steam_generators} steam generators")
    print(f"Design total thermal power: {enhanced_sg.config.design_total_thermal_power/1e6:.0f} MW")
    print(f"Design total steam flow: {enhanced_sg.config.design_total_steam_flow:.0f} kg/s")
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
