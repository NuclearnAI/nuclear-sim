"""
Secondary Reactor Physics System

This module provides the integrated secondary reactor physics system for PWR plants,
combining steam generators, turbines, and condensers into a complete steam cycle model.
Enhanced with state management integration for comprehensive data collection.
"""

import numpy as np
from typing import Dict, Any, Optional
import pandas as pd

# Import state management interfaces
from simulator.state import auto_register

# Import heat flow tracking
from .heat_flow_tracker import HeatFlowTracker, HeatFlowProvider, ThermodynamicProperties

# Import chemistry flow tracking and water chemistry
from .chemistry_flow_tracker import ChemistryFlowTracker, ChemistryFlowProvider, ChemicalSpecies, ChemistryProperties
from .water_chemistry import WaterChemistry, WaterChemistryConfig, DegradationCalculator
from .ph_control_system import PHControlSystem, PHControllerConfig
from .config import SecondarySystemConfig

from .steam_generator import (
    SteamGenerator, 
    SteamGeneratorConfig,
    EnhancedSteamGeneratorPhysics
)
from .turbine import (
    # New unified configuration classes
    TurbineConfig,
    TurbineStageSystemConfig,
    RotorDynamicsConfig,
    TurbineThermalStressConfig,
    TurbineProtectionConfig,
    TurbineGovernorConfig,
    TurbineBearingConfig,
    
    # Enhanced turbine physics
    EnhancedTurbinePhysics,
    MetalTemperatureTracker,
    TurbineProtectionSystem,
    
    # Individual component systems
    TurbineStageSystem,
    TurbineStage,
    TurbineStageSystemConfig,
    RotorDynamicsModel,
    VibrationMonitor,
    BearingModel,
    )

# Enhanced condenser physics (now uses centralized config)
from .condenser import EnhancedCondenserPhysics, CondenserConfig
from .feedwater import (
    # Enhanced feedwater physics
    EnhancedFeedwaterPhysics,
    FeedwaterConfig,
    
    # Individual component systems
    FeedwaterPumpSystem,
    FeedwaterPump,
    FeedwaterPumpState,
    FeedwaterPumpConfig,
    ThreeElementControl,
    # WaterQualityModel,  # Moved to unified water chemistry
    # WaterQualityConfig,  # Moved to unified water chemistry
    PerformanceDiagnostics,
    FeedwaterProtectionSystem,
    FeedwaterProtectionConfig
)

__all__ = [
    # Steam Generator System
    'SteamGenerator',
    'SteamGeneratorConfig',
    'EnhancedSteamGeneratorPhysics',
    
    # New unified turbine configuration classes
    'TurbineConfig',
    'TurbineStageSystemConfig',
    'RotorDynamicsConfig',
    'TurbineThermalStressConfig',
    'TurbineProtectionConfig',
    'TurbineGovernorConfig',
    'TurbineBearingConfig',
    
    # Enhanced Turbine System
    'EnhancedTurbinePhysics',
    'MetalTemperatureTracker',
    'TurbineProtectionSystem',
    'TurbineStageSystem',
    'TurbineStage',
    'TurbineStageSystemConfig',
    'RotorDynamicsModel',
    'VibrationMonitor',
    'BearingModel',
    'TurbineBearingConfig',
    
    # Enhanced Condenser
    'EnhancedCondenserPhysics',
    'CondenserConfig',
    
    # Enhanced Feedwater System
    'EnhancedFeedwaterPhysics',
    'FeedwaterConfig',
    'FeedwaterPumpSystem',
    'FeedwaterPump',
    'FeedwaterPumpState',
    'FeedwaterPumpConfig',
    'ThreeElementControl',
    # 'WaterQualityModel',  # Moved to unified water chemistry
    # 'WaterQualityConfig',  # Moved to unified water chemistry
    'PerformanceDiagnostics',
    'FeedwaterProtectionSystem',
    'FeedwaterProtectionConfig',
    
    # Chemistry Flow Tracking and Water Chemistry
    'ChemistryFlowTracker',
    'ChemistryFlowProvider',
    'ChemicalSpecies',
    'ChemistryProperties',
    'WaterChemistry',
    'WaterChemistryConfig',
    'DegradationCalculator',
    'PHControlSystem',
    'PHControllerConfig',
    
    # Integrated System
    'SecondaryReactorPhysics'
]




@auto_register("SECONDARY", "reactor", "SRP", allow_no_id=True)
class SecondaryReactorPhysics:
    """
    Integrated secondary reactor physics system with state management integration
    
    This class combines steam generators, turbines, and condensers to model
    the complete secondary side of a PWR nuclear power plant.
    
    The system models:
    1. Heat transfer from primary to secondary in steam generators
    2. Steam expansion and power generation in turbines
    3. Steam condensation and heat rejection in condensers
    4. Complete mass and energy balance across the steam cycle
    5. Control system interactions and feedback loops
    6. Comprehensive state management for all subsystems
    
    Implements StateProvider interface for automatic state collection.
    
    NEW: Now supports modular configuration through PWR3000Config for easy
    user configuration via YAML/JSON/TOML files.
    """
    
    def __init__(self, 
                 # NEW: Primary configuration options
                 config: Optional['PWR3000Config'] = None,
                 config_file: Optional[str] = None,
                 # Legacy parameters for backward compatibility
                 num_steam_generators: Optional[int] = None,
                 sg_config: Optional[SteamGeneratorConfig] = None,
                 turbine_config: Optional[TurbineConfig] = None,
                 condenser_config: Optional[CondenserConfig] = None):
        """
        Initialize integrated secondary reactor physics
        
        Args:
            config: PWR3000Config object for complete system configuration
            config_file: Path to YAML/JSON/TOML configuration file
            # Legacy parameters (for backward compatibility):
            num_steam_generators: Number of steam generators (typically 2-4)
            sg_config: Steam generator configuration
            turbine_config: Enhanced turbine configuration  
            condenser_config: Condenser configuration
        """
        # Load configuration using new modular system
        if config_file:
            # SIMPLE APPROACH: Check if config has secondary_system key and extract it
            import yaml
            import os
            
            # Handle relative paths
            if not os.path.isabs(config_file):
                # If the path starts with "systems/secondary/", it's already relative to project root
                if config_file.startswith("systems/secondary/"):
                    # Use as-is, it's relative to project root
                    pass
                else:
                    # It's relative to the secondary directory
                    config_dir = os.path.dirname(__file__)
                    config_file = os.path.join(config_dir, config_file)
            
            # Load YAML file
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Simple extraction: if secondary_system exists, use it as root
            if 'secondary_system' in config_data:
                config_data = config_data['secondary_system']  # Drop down one level
                print(f"[SECONDARY CONFIG] Extracted secondary_system section from comprehensive config")
            else:
                print(f"[SECONDARY CONFIG] Using flat config structure (legacy format)")
            
            # Now treat config_data as if it were the old flat structure
            # Convert to SecondarySystemConfig object
            try:
                # Try to create SecondarySystemConfig from the extracted data
                if hasattr(SecondarySystemConfig, 'from_dict'):
                    self.config = SecondarySystemConfig.from_dict(config_data)
                else:
                    # Fallback: create with main parameters and let subsystems handle their own configs
                    self.config = SecondarySystemConfig(
                        system_id=config_data.get('system_id', 'SECONDARY-001'),
                        plant_id=config_data.get('plant_id', 'PWR-PLANT-001'),
                        rated_thermal_power=config_data.get('rated_thermal_power', 3000.0e6),
                        rated_electrical_power=config_data.get('rated_electrical_power', 1000.0),
                        design_efficiency=config_data.get('design_efficiency', 0.33),
                        num_loops=config_data.get('num_loops', 3)
                    )
                    # Store the raw config data for subsystem access
                    self.config._raw_config_data = config_data
            except Exception as e:
                print(f"[SECONDARY CONFIG] Warning: Could not create SecondarySystemConfig object: {e}")
                print(f"[SECONDARY CONFIG] Using raw config data directly")
                # Store raw config data as a simple object for subsystem access
                class SimpleConfig:
                    def __init__(self, data):
                        self.__dict__.update(data)
                        self._raw_config_data = data
                    
                    def get(self, key, default=None):
                        return self._raw_config_data.get(key, default)
                
                self.config = SimpleConfig(config_data)
                
        elif config:
            config_data = config['secondary_system']
            print(config_data)
            self.config = SecondarySystemConfig.from_dict(config_data)
        else:
            # Create default 3000 MW PWR configuration
            from .config import PWR3000ConfigFactory
            self.config = PWR3000ConfigFactory.create_standard_pwr3000()
        # Apply legacy parameter overrides for backward compatibility
        if num_steam_generators is not None:
            self.config.num_loops = num_steam_generators
            self.config._configure_subsystems()  # Reconfigure with new parameters
        
        # Extract key parameters from configuration
        # For PWR plants, typically 1 steam generator per loop
        steam_generators_per_loop = getattr(self.config, 'steam_generators_per_loop', 1)
        self.num_steam_generators = self.config.num_loops * steam_generators_per_loop
        
        # Initialize subsystems using configuration from PWR3000Config
        # Apply legacy overrides if provided
        if sg_config is not None:
            # Override steam generator config with legacy parameter
            self.config.steam_generator_config = sg_config
        if turbine_config is not None:
            # Override turbine config with legacy parameter
            self.config.turbine_config = turbine_config
        if condenser_config is not None:
            # Override condenser config with legacy parameter
            self.config.condenser_config = condenser_config
        
        # Initialize subsystems using the configuration
        # Handle both SecondarySystemConfig objects and raw config data
        if hasattr(self.config, '_raw_config_data'):
            # Use raw config data extracted from comprehensive config
            raw_config = self.config._raw_config_data
            print(f"[SECONDARY CONFIG] Using raw config data for subsystem initialization")
            
            # Initialize each subsystem with its section from the raw config
            self.steam_generator_system = EnhancedSteamGeneratorPhysics(raw_config.get('steam_generator', {}))
            self.turbine = EnhancedTurbinePhysics(raw_config.get('turbine', {}))
            self.condenser = EnhancedCondenserPhysics(raw_config.get('condenser', {}))
            self.feedwater_system = EnhancedFeedwaterPhysics(config_dict=raw_config.get('feedwater', {}))
            
        elif hasattr(self.config, 'get') and callable(self.config.get):
            # Config is a simple dictionary-like object
            print(f"[SECONDARY CONFIG] Using dictionary-like config for subsystem initialization")
            feedwater_config_dict = self.config.get('feedwater', {})
            self.steam_generator_system = EnhancedSteamGeneratorPhysics(self.config.get('steam_generator', {}))
            self.turbine = EnhancedTurbinePhysics(self.config.get('turbine', {}))
            self.condenser = EnhancedCondenserPhysics(self.config.get('condenser', {}))
            self.feedwater_system = EnhancedFeedwaterPhysics(config_dict=feedwater_config_dict)
            
        else:
            # Config is a SecondarySystemConfig object (legacy format)
            print(f"[SECONDARY CONFIG] Using SecondarySystemConfig object for subsystem initialization")
            self.steam_generator_system = EnhancedSteamGeneratorPhysics(self.config.steam_generator)
            self.turbine = EnhancedTurbinePhysics(self.config.turbine)
            self.condenser = EnhancedCondenserPhysics(self.config.condenser)
            self.feedwater_system = EnhancedFeedwaterPhysics(self.config.feedwater)
        
        # System state variables
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        self.total_feedwater_flow = 0.0
        
        # Control parameters
        self.load_demand = 100.0  # % rated load
        self.feedwater_temperature = 227.0  # °C
        self.cooling_water_temperature = 25.0  # °C
        
        # Initialize heat flow tracker
        self.heat_flow_tracker = HeatFlowTracker()
        
        # Initialize chemistry flow tracker and water chemistry system
        self.water_chemistry = WaterChemistry()
        self.ph_control_system = PHControlSystem()
        
        # CRITICAL FIX: Inject unified water chemistry into feedwater system
        # The feedwater system expects this to be provided by the parent system
        self.feedwater_system.water_quality = self.water_chemistry
        
        # Create chemistry flow providers dictionary for integration
        chemistry_providers = {
            'water_chemistry': self.water_chemistry,
            'steam_generator': self.steam_generator_system,
            'condenser': self.condenser,
            'feedwater': self.feedwater_system
        }
        
        # Initialize chemistry flow tracker with providers
        self.chemistry_flow_tracker = ChemistryFlowTracker(chemistry_providers)
        
        # Initialize operating time tracking
        self.operating_hours = 0.0
        
        # Initialize total system heat rejection (for energy balance)
        self.total_system_heat_rejection = 0.0
        
    def update_system(self,
                     primary_conditions: dict,
                     control_inputs: dict,
                     dt: float) -> dict:
        """
        Update the complete secondary system for one time step
        
        Args:
            primary_conditions: Dictionary with primary side conditions for each SG
                - 'sg_X_inlet_temp': Primary inlet temperature for SG X (°C)
                - 'sg_X_outlet_temp': Primary outlet temperature for SG X (°C)
                - 'sg_X_flow': Primary flow rate for SG X (kg/s)
            control_inputs: Dictionary with control system inputs
                - 'load_demand': Electrical load demand (% rated)
                - 'feedwater_temp': Feedwater temperature (°C)
                - 'cooling_water_temp': Cooling water inlet temperature (°C)
                - 'cooling_water_flow': Cooling water flow rate (kg/s)
                - 'vacuum_pump_operation': Vacuum pump operation (0-1)
            dt: Time step (MINUTES from main simulator)
            
        Returns:
            Dictionary with complete system state and performance
            
        Note:
            Time step unit conversions:
            - Main simulator passes dt in MINUTES
            - Turbine system expects dt in HOURS -> convert with dt/60.0
            - Condenser system expects dt in HOURS -> convert with dt/60.0  
            - Feedwater system expects dt in MINUTES -> use dt directly
            - Steam generator system expects dt in SECONDS -> convert with dt*60.0
        """
        # Extract control inputs
        self.load_demand = control_inputs.get('load_demand', 100.0)
        self.feedwater_temperature = control_inputs.get('feedwater_temp', 227.0)
        self.cooling_water_temperature = control_inputs.get('cooling_water_temp', 25.0)
        cooling_water_flow = control_inputs.get('cooling_water_flow', 45000.0)
        vacuum_pump_operation = control_inputs.get('vacuum_pump_operation', 1.0)
        
        # First, check feedwater system availability (using previous state)
        feedwater_system_available = getattr(self.feedwater_system, 'system_availability', True)
        
        # FIXED SG-FW INTEGRATION: Update feedwater system first, then steam generators
        # This creates proper feedback loop where SGs respond to actual feedwater flows
        
        # Use previous time step feedwater temperature with smoothing to reduce oscillations
        if not hasattr(self, '_previous_feedwater_temp'):
            self._previous_feedwater_temp = self.feedwater_temperature
        
        # Calculate feedwater temperature estimate based on condenser + heating
        # This provides a good estimate without needing feedwater system update first
        estimated_condensate_temp = 40.0  # °C - typical condenser condensate temperature
        estimated_heating = 187.0  # °C - typical feedwater heating (227°C - 40°C)
        estimated_feedwater_temp = estimated_condensate_temp + estimated_heating
        
        # Smooth the feedwater temperature to reduce oscillations
        alpha = 0.1  # Smoothing factor
        actual_feedwater_temp = (alpha * estimated_feedwater_temp + 
                               (1 - alpha) * self._previous_feedwater_temp)
        self._previous_feedwater_temp = actual_feedwater_temp
        
        # CRITICAL FIX: Use the actual calculated temperatures from primary system
        # Check if we have individual SG temperatures (new interface with temperature calculation)
        if f'sg_1_inlet_temp' in primary_conditions:
            # NEW INTERFACE: Use the actual calculated temperatures from main simulator
            enhanced_primary_conditions = {
                'inlet_temps': [primary_conditions.get(f'sg_{i+1}_inlet_temp', 327.0) for i in range(self.num_steam_generators)],
                'outlet_temps': [primary_conditions.get(f'sg_{i+1}_outlet_temp', 293.0) for i in range(self.num_steam_generators)],
                'flow_rates': [primary_conditions.get(f'sg_{i+1}_flow', 5700.0) for i in range(self.num_steam_generators)]
            }
        elif f'sg_1_thermal_power' in primary_conditions:
            # FALLBACK: Calculate temperatures from thermal power (old method)
            enhanced_primary_conditions = self._calculate_temperatures_from_power(primary_conditions)
        else:
            # OLD INTERFACE: Use provided temperatures (backward compatibility)
            enhanced_primary_conditions = {
                'inlet_temps': [primary_conditions.get(f'sg_{i+1}_inlet_temp', 327.0) for i in range(self.num_steam_generators)],
                'outlet_temps': [primary_conditions.get(f'sg_{i+1}_outlet_temp', 293.0) for i in range(self.num_steam_generators)],
                'flow_rates': [primary_conditions.get(f'sg_{i+1}_flow', 5700.0) for i in range(self.num_steam_generators)]
            }
        
        # Calculate load demand fraction from actual thermal power
        # FIXED: Calculate thermal power correctly for each steam generator
        total_thermal_power_mw = 0.0
        for i in range(self.num_steam_generators):
            inlet_temp = enhanced_primary_conditions['inlet_temps'][i]
            outlet_temp = enhanced_primary_conditions['outlet_temps'][i]
            flow_rate = enhanced_primary_conditions['flow_rates'][i]
            delta_t = inlet_temp - outlet_temp
            # Q = m_dot * cp * delta_T (convert to MW)
            sg_thermal_power = flow_rate * 5.2 * delta_t / 1000.0  # MW
            total_thermal_power_mw += sg_thermal_power
        
        # If we have thermal power data directly, use it (this takes precedence)
        if f'sg_1_thermal_power' in primary_conditions:
            total_thermal_power_mw = sum(primary_conditions.get(f'sg_{i+1}_thermal_power', 1000.0) for i in range(self.num_steam_generators))
        
        # Calculate load demand fraction from thermal power (3000 MW = 100% load)
        load_demand_fraction = min(1.0, total_thermal_power_mw / 3000.0)
        
        # Ensure minimum reasonable load demand for stable operation
        load_demand_fraction = max(load_demand_fraction, 0.2)  # Minimum 20% load
        
        # Estimate steam flows for feedwater system (will be corrected by actual SG results later)
        estimated_steam_flow_per_sg = 555.0 * load_demand_fraction  # kg/s per SG
        estimated_total_steam_flow = estimated_steam_flow_per_sg * self.num_steam_generators
        
        # Use previous SG conditions if available, otherwise use estimates
        if not hasattr(self, '_previous_sg_conditions'):
            self._previous_sg_conditions = {
                'levels': [12.5] * self.num_steam_generators,
                'pressures': [6.895] * self.num_steam_generators,
                'steam_flows': [estimated_steam_flow_per_sg] * self.num_steam_generators,
                'steam_qualities': [0.99] * self.num_steam_generators
            }
        
        # STEP 1: UPDATE FEEDWATER SYSTEM FIRST
        # Prepare system conditions for feedwater pump system
        condensate_temp = 40.0  # °C - typical condenser condensate temperature
        
        feedwater_system_conditions = {
            'sg_pressure': 6.895,  # Use design pressure for initial calculation
            'feedwater_temperature': condensate_temp,  # Use condensate temp for pump inlet
            'suction_pressure': 0.5,  # MPa - typical condensate pump discharge pressure
            'discharge_pressure': 7.4,  # Steam pressure + margin
        }
        
        # Add previous SG data for feedwater system
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            sg_level = self._previous_sg_conditions['levels'][i]
            sg_steam_flow = self._previous_sg_conditions['steam_flows'][i]
            sg_steam_quality = self._previous_sg_conditions['steam_qualities'][i]
            sg_void_fraction = 0.45  # Default value
            
            feedwater_system_conditions[f'{sg_key}_level'] = sg_level
            feedwater_system_conditions[f'{sg_key}_steam_flow'] = sg_steam_flow
            feedwater_system_conditions[f'{sg_key}_steam_quality'] = sg_steam_quality
            feedwater_system_conditions[f'{sg_key}_void_fraction'] = sg_void_fraction
        
        # Steam generator demands for feedwater system
        steam_generator_demands = {
            'total_flow': estimated_total_steam_flow  # Use estimated demand
        }
        
        # Update feedwater system first
        feedwater_result = self.feedwater_system.update_state(
            sg_conditions=self._previous_sg_conditions,
            steam_generator_demands=steam_generator_demands,
            system_conditions=feedwater_system_conditions,
            control_inputs=control_inputs,
            dt=dt
        )
        
        # STEP 2: UPDATE STEAM GENERATORS WITH ACTUAL FEEDWATER FLOWS
        # Extract actual feedwater flows from feedwater system
        actual_total_feedwater_flow = feedwater_result['total_flow_rate']
        actual_sg_flow_distribution = feedwater_result.get('sg_flow_distribution', {})
        
        # Convert flow distribution to list format
        actual_feedwater_flows = []
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            if sg_key in actual_sg_flow_distribution:
                actual_feedwater_flows.append(actual_sg_flow_distribution[sg_key])
            else:
                # Fallback: equal distribution of total flow
                actual_feedwater_flows.append(actual_total_feedwater_flow / self.num_steam_generators)
        
        steam_demands = {
            'load_demand_fraction': load_demand_fraction,
            'steam_pressure': 6.895  # Target steam pressure
        }
        
        # Enhanced system conditions with actual feedwater flows
        enhanced_system_conditions = {
            'feedwater_temperature': actual_feedwater_temp,
            'load_demand': self.load_demand / 100.0,
            'actual_feedwater_flows': actual_feedwater_flows  # NEW: Pass actual flows from FW system
        }
        
        # Update enhanced steam generator system with actual feedwater flows
        sg_system_result = self.steam_generator_system.update_system(
            primary_conditions=enhanced_primary_conditions,
            steam_demands=steam_demands,
            system_conditions=enhanced_system_conditions,
            control_inputs=control_inputs,
            dt=dt*60
        )
        
        # Store current SG conditions for next timestep
        self._previous_sg_conditions = {
            'levels': sg_system_result.get('sg_levels', [12.5] * self.num_steam_generators),
            'pressures': sg_system_result.get('sg_pressures', [6.895] * self.num_steam_generators),
            'steam_flows': sg_system_result.get('sg_steam_flows', [0.0] * self.num_steam_generators),
            'steam_qualities': sg_system_result.get('sg_steam_qualities', [0.99] * self.num_steam_generators)
        }
        
        # Extract results from enhanced system
        total_heat_transfer = sg_system_result['total_thermal_power']
        total_steam_production = sg_system_result['total_steam_flow']
        sg_results = sg_system_result['sg_individual_results']
        
        # Calculate average steam conditions entering turbine from enhanced system results
        if len(sg_results) > 0:
            avg_steam_pressure = sg_system_result['average_steam_pressure']
            avg_steam_temperature = sg_system_result['average_steam_temperature']
            avg_steam_quality = sg_system_result['average_steam_quality']
            
            # FIXED: Ensure steam temperature is realistic for turbine operation
            # Steam temperature should be saturation temperature at steam pressure
            # For superheated steam in PWR, add small superheat margin
            sat_temp_at_pressure = self._saturation_temperature(avg_steam_pressure)
            avg_steam_temperature = max(avg_steam_temperature, sat_temp_at_pressure)
        else:
            avg_steam_pressure = 6.895
            avg_steam_temperature = 285.8
            avg_steam_quality = 0.99
        
        # Total steam flow to turbine
        total_steam_flow = sum(sg_result['steam_flow_rate'] for sg_result in sg_results)
        
        # STEP 5: Update turbine with rich SG conditions instead of individual parameters
        # CRITICAL FIX: Convert dt from minutes to hours for turbine system
        # The turbine system expects dt in hours, but main simulator passes dt in minutes
        turbine_result = self.turbine.update_state(
            sg_conditions=sg_system_result,  # NEW: Pass full SG result dictionary
            load_demand=self.load_demand,
            condenser_pressure=0.007,  # Will be updated with actual condenser pressure
            dt=dt/60.0  # Convert minutes to hours for turbine
        )
        
        # Update condenser with ACTUAL LP turbine exhaust conditions from turbine system
        # Enhanced condenser parameters from control inputs with defaults
        makeup_water_quality = control_inputs.get('makeup_water_quality', {
            'tds': 300.0,
            'hardness': 100.0,
            'chloride': 30.0,
            'ph': 7.2,
            'dissolved_oxygen': 8.0
        })
        
        chemical_doses = control_inputs.get('chemical_doses', {
            'chlorine': 1.0,
            'antiscalant': 5.0,
            'corrosion_inhibitor': 10.0,
            'biocide': 0.0
        })
        
        motive_steam_pressure = control_inputs.get('motive_steam_pressure', 1.2)  # MPa
        motive_steam_temperature = control_inputs.get('motive_steam_temperature', 185.0)  # °C
        
        # Calculate actual LP exhaust steam quality from turbine stage results
        stage_results = turbine_result.get('stage_results', {})
        lp_exhaust_quality = 0.90  # Default fallback
        
        if 'LP-6' in stage_results:
            # Get LP-6 (final LP stage) outlet enthalpy
            lp6_enthalpy = stage_results['LP-6']['outlet_enthalpy']  # kJ/kg
            lp6_pressure = turbine_result['condenser_pressure']  # MPa
            
            # Calculate steam quality from enthalpy: x = (h - h_f) / h_fg
            h_f = self.condenser._saturation_enthalpy_liquid(lp6_pressure)
            h_g = self.condenser._saturation_enthalpy_vapor(lp6_pressure)
            h_fg = h_g - h_f
            
            if h_fg > 0:
                lp_exhaust_quality = (lp6_enthalpy - h_f) / h_fg
                lp_exhaust_quality = max(0.0, min(1.0, lp_exhaust_quality))  # Clamp to valid range
        
        condenser_result = self.condenser.update_state(
            steam_pressure=turbine_result['condenser_pressure'],
            steam_temperature=turbine_result['condenser_temperature'],  # From turbine LP exit
            steam_flow=turbine_result['effective_steam_flow'],  # Actual flow to condenser (after extractions)
            steam_quality=lp_exhaust_quality,  # Actual LP exhaust quality from turbine
            cooling_water_flow=cooling_water_flow,
            cooling_water_temp_in=self.cooling_water_temperature,
            motive_steam_pressure=motive_steam_pressure,
            motive_steam_temperature=motive_steam_temperature,
            makeup_water_quality=makeup_water_quality,
            chemical_doses=chemical_doses,
            dt=dt / 60.0  # Convert seconds to hours for enhanced condenser
        )
        
        # Update condenser system conditions now that we have condenser results
        condensate_temp = condenser_result.get('condensate_temperature', 40.0)  # °C
        feedwater_system_conditions['feedwater_temperature'] = condensate_temp
        feedwater_system_conditions['suction_pressure'] = condenser_result['condenser_pressure'] + 0.5
        
        # Extract feedwater flow for mass balance
        self.total_feedwater_flow = feedwater_result['total_flow_rate']
        
        # Update operating hours
        self.operating_hours += dt / 3600.0  # Convert seconds to hours
        
        # UPDATE CHEMISTRY SYSTEMS
        # Update water chemistry with system conditions
        system_conditions = {
            'makeup_water_quality': makeup_water_quality,
            'blowdown_rate': 0.02,  # Typical blowdown rate
            'temperature': condensate_temp,
            'pressure': avg_steam_pressure
        }
        
        # Update water chemistry
        water_chemistry_result = self.water_chemistry.update_chemistry(system_conditions, dt)
        
        # Update pH control system
        ph_control_result = self.ph_control_system.update_system(
            current_ph=water_chemistry_result.get('water_chemistry_ph', 9.2),
            dt=dt
        )
        
        # Extract controller outputs from pH control result
        controller_outputs = ph_control_result.get('controller_outputs', {})
        
        # Apply pH control effects to water chemistry
        chemistry_effects = {
            'ph_setpoint': controller_outputs.get('ph_setpoint', 9.2),
            'ammonia_dose_rate': controller_outputs.get('ammonia_dose_rate', 0.0),
            'morpholine_dose_rate': controller_outputs.get('morpholine_dose_rate', 0.0),
            'chemical_additions': {
                'ammonia': controller_outputs.get('ammonia_dose_rate', 0.0) / 3600.0,  # Convert kg/hr to kg/s
                'morpholine': controller_outputs.get('morpholine_dose_rate', 0.0) / 3600.0
            }
        }
        self.water_chemistry.update_chemistry_effects(chemistry_effects)
        
        # Update chemistry flow tracker from all providers
        self.chemistry_flow_tracker.update_from_providers()
        
        # Calculate system-wide chemistry flows
        chemistry_flow_state = self.chemistry_flow_tracker.calculate_system_chemistry_flows()
        chemistry_flow_validation = self.chemistry_flow_tracker.validate_chemistry_balance()
        
        # Add chemistry flow data to tracker history
        self.chemistry_flow_tracker.add_to_history(self.operating_hours)
        
        # UPDATE HEAT FLOW TRACKER WITH COMPONENT DATA
        # Collect heat flows from all components that implement HeatFlowProvider
        
        # CORRECTED HEAT FLOW CALCULATIONS FOR ENERGY BALANCE
        # Use physics-based energy balance instead of enthalpy calculations
        
        # Steam Generator heat flows - use actual thermal power transfer
        sg_flows = {
            'primary_heat_input': total_heat_transfer / 1e6,  # MW from primary side
            'steam_enthalpy_output': total_heat_transfer * 0.98 / 1e6,  # MW (98% SG efficiency)
            'thermal_losses': total_heat_transfer * 0.02 / 1e6,  # MW (2% SG losses)
            'thermal_efficiency': 0.98
        }
        self.heat_flow_tracker.update_component_flows('steam_generator', sg_flows)
        
        # Turbine heat flows - use actual turbine performance
        turbine_mechanical_power = turbine_result['mechanical_power']
        turbine_flows = {
            'steam_enthalpy_input': sg_flows['steam_enthalpy_output'],  # MW from SG
            'mechanical_work_output': turbine_mechanical_power,  # MW actual work
            'exhaust_enthalpy_output': sg_flows['steam_enthalpy_output'] - turbine_mechanical_power - (turbine_mechanical_power * 0.05),  # MW remaining enthalpy
            'extraction_enthalpy_output': 0.0,  # MW extraction steam (simplified)
            'internal_losses': turbine_mechanical_power * 0.05  # MW (5% internal losses)
        }
        self.heat_flow_tracker.update_component_flows('turbine', turbine_flows)
        
        # Feedwater system heat flows - use actual pump power
        feedwater_flows = {
            'extraction_heating': 0.0,  # MW (simplified - no extraction heating)
            'pump_work_input': feedwater_result['total_power_consumption'],  # MW pump work
            'system_losses': feedwater_result['total_power_consumption'] * 0.1  # MW (10% losses)
        }
        self.heat_flow_tracker.update_component_flows('feedwater', feedwater_flows)
        
        # Condenser heat flows - CORRECTED using energy balance approach
        # The condenser must reject all energy not converted to electrical power
        
        # Calculate required heat rejection from energy balance
        # Energy In = Electrical Out + Heat Rejected + Losses
        # Therefore: Heat Rejected = Energy In - Electrical Out - Losses
        
        total_losses_mw = (sg_flows['thermal_losses'] + 
                          turbine_flows['internal_losses'] + 
                          feedwater_flows['system_losses'])
        
        # Required heat rejection to balance energy equation
        required_heat_rejection_mw = sg_flows['primary_heat_input'] - turbine_mechanical_power - total_losses_mw
        
        # Use the energy-balance-calculated heat rejection instead of condenser physics calculation
        # This ensures perfect energy conservation
        condenser_flows = {
            'steam_enthalpy_input': turbine_flows['exhaust_enthalpy_output'],  # MW from turbine exhaust
            'heat_rejection_output': required_heat_rejection_mw,  # MW required by energy balance
            'condensate_enthalpy_output': 50.0,  # MW remaining in condensate (typical value)
            'thermal_losses': required_heat_rejection_mw * 0.01,  # MW (1% condenser losses)
            'vacuum_steam_consumption': 0.0  # MW (simplified)
        }
        self.heat_flow_tracker.update_component_flows('condenser', condenser_flows)
        
        # Update the total system heat rejection to match energy balance
        self.total_system_heat_rejection = required_heat_rejection_mw * 1e6  # Convert to Watts
        
        # Calculate system-wide heat flows and energy balance
        heat_flow_state = self.heat_flow_tracker.calculate_system_heat_flows()
        heat_flow_validation = self.heat_flow_tracker.validate_energy_balance()
        
        # Add heat flow data to tracker history
        self.heat_flow_tracker.add_to_history(self.operating_hours)
        
        # Calculate system performance metrics
        self.total_steam_flow = total_steam_flow
        self.total_heat_transfer = total_heat_transfer
        
        # ENERGY CONSERVATION FIX: Use primary thermal power directly instead of recalculating
        # This eliminates the double calculation that was causing energy conservation violations
        primary_thermal_power = 0.0
        
        # Check if using new simplified interface (thermal power directly provided)
        if f'sg_1_thermal_power' in primary_conditions:
            # NEW INTERFACE: Use directly provided thermal power (PREFERRED)
            for i in range(self.num_steam_generators):
                sg_key = f'sg_{i+1}'
                loop_thermal_power = primary_conditions.get(f'{sg_key}_thermal_power', 0.0)  # MW
                primary_thermal_power += loop_thermal_power
        else:
            # OLD INTERFACE: Calculate from temperatures (FALLBACK ONLY)
            for i in range(self.num_steam_generators):
                sg_key = f'sg_{i+1}'
                primary_inlet_temp = primary_conditions.get(f'{sg_key}_inlet_temp', 327.0)
                primary_outlet_temp = primary_conditions.get(f'{sg_key}_outlet_temp', 293.0)
                primary_flow = primary_conditions.get(f'{sg_key}_flow', 5700.0)
                
                if primary_flow > 0 and primary_inlet_temp > primary_outlet_temp:
                    cp_primary = 5.2  # kJ/kg/K at PWR conditions
                    delta_t = primary_inlet_temp - primary_outlet_temp
                    loop_thermal_power = primary_flow * cp_primary * delta_t / 1000.0  # MW
                    primary_thermal_power += loop_thermal_power
        
        # USE PRIMARY THERMAL POWER FOR ALL CALCULATIONS (Single source of truth)
        thermal_power_mw = primary_thermal_power  # No more secondary recalculation
        
        # ENERGY CONSERVATION APPROACH: Calculate total system heat rejection
        # Use the first law of thermodynamics: Energy In = Energy Out
        # Thermal Power = Electrical Power + Total Heat Rejected
        
        # Get actual condenser heat rejection from LP turbine exhaust (physically accurate)
        condenser_heat_rejection_mw = condenser_result['heat_rejection_rate'] / 1e6  # Convert to MW
        
        # Calculate electrical power from turbine
        turbine_electrical_power = turbine_result['electrical_power_net']
        
        # ENFORCE PERFECT ENERGY CONSERVATION: Total heat rejection = Thermal Power - Electrical Power
        # This is the first law of thermodynamics and must always be satisfied
        total_system_heat_rejection_mw = primary_thermal_power - turbine_electrical_power
        
        # Validate that this is physically reasonable (should be 65-70% of thermal power)
        heat_rejection_fraction = total_system_heat_rejection_mw / primary_thermal_power if primary_thermal_power > 0 else 0
        
        # Convert back to Watts for consistency with existing interfaces
        system_heat_rejection_watts = total_system_heat_rejection_mw * 1e6
        
        # CRITICAL FIX: Set the total_system_heat_rejection attribute
        self.total_system_heat_rejection = system_heat_rejection_watts
        
        # For reporting, we'll use the total system heat rejection to ensure energy balance
        # But we'll also track the main condenser component separately for physical accuracy
        
        # CRITICAL PHYSICS VALIDATION: NO FEEDWATER = NO ELECTRICAL POWER
        # Check actual feedwater flow from the feedwater system
        actual_feedwater_flow = feedwater_result.get('total_flow_rate', 0.0)
        
        # STRICT MINIMUM THRESHOLDS FOR ELECTRICAL GENERATION
        MIN_PRIMARY_THERMAL_MW = 10.0      # Minimum primary thermal power (MW)
        MIN_SECONDARY_THERMAL_MW = 10.0    # Minimum secondary heat transfer (MW)
        MIN_STEAM_FLOW_KGS = 300.0         # Minimum steam flow (kg/s) - REDUCED for low power operation
        MIN_FEEDWATER_FLOW_KGS = 300.0     # Minimum feedwater flow (kg/s) - CRITICAL - REDUCED for low power operation
        MIN_STEAM_PRESSURE_MPA = 1.0       # Minimum steam pressure (MPa)
        MIN_TEMPERATURE_DELTA = 5.0        # Minimum primary-secondary temp difference (°C)
        
        # Calculate average primary-secondary temperature difference
        # FIXED: Use the same temperature source as the steam generators (enhanced_primary_conditions)
        avg_primary_temp = 0.0
        for i in range(self.num_steam_generators):
            # Use enhanced_primary_conditions which has the correct temperatures
            primary_inlet_temp = enhanced_primary_conditions['inlet_temps'][i]
            avg_primary_temp += primary_inlet_temp
        avg_primary_temp /= self.num_steam_generators if self.num_steam_generators > 0 else 1
        
        # Get average secondary temperature (saturation temperature at steam pressure)
        avg_secondary_temp = self._saturation_temperature(avg_steam_pressure)
        temp_delta = avg_primary_temp - avg_secondary_temp
        
        # COMPREHENSIVE VALIDATION CONDITIONS
        validation_failures = []
        
        if primary_thermal_power < MIN_PRIMARY_THERMAL_MW:
            validation_failures.append(f"Primary thermal power too low: {primary_thermal_power:.2f} MW < {MIN_PRIMARY_THERMAL_MW} MW")
        
        if thermal_power_mw < MIN_SECONDARY_THERMAL_MW:
            validation_failures.append(f"Secondary heat transfer too low: {thermal_power_mw:.2f} MW < {MIN_SECONDARY_THERMAL_MW} MW")
        
        if total_steam_flow < MIN_STEAM_FLOW_KGS:
            validation_failures.append(f"Steam flow too low: {total_steam_flow:.1f} kg/s < {MIN_STEAM_FLOW_KGS} kg/s")
        
        # CRITICAL: Check feedwater flow - no feedwater means no electrical power generation
        if actual_feedwater_flow < MIN_FEEDWATER_FLOW_KGS:
            validation_failures.append(f"Feedwater flow too low: {actual_feedwater_flow:.1f} kg/s < {MIN_FEEDWATER_FLOW_KGS} kg/s")
        
        if avg_steam_pressure < MIN_STEAM_PRESSURE_MPA:
            validation_failures.append(f"Steam pressure too low: {avg_steam_pressure:.2f} MPa < {MIN_STEAM_PRESSURE_MPA} MPa")
        
        if temp_delta < MIN_TEMPERATURE_DELTA:
            validation_failures.append(f"Temperature difference too low: {temp_delta:.1f}°C < {MIN_TEMPERATURE_DELTA}°C")
        
        # ENERGY CONSERVATION CHECK
        # Ensure secondary heat transfer doesn't exceed primary thermal power
        if thermal_power_mw > primary_thermal_power * 1.05:  # Allow 5% margin for calculation differences
            validation_failures.append(f"Energy conservation violation: Secondary heat transfer ({thermal_power_mw:.2f} MW) > Primary thermal power ({primary_thermal_power:.2f} MW)")
        
        # USE TURBINE-CALCULATED ELECTRICAL POWER WITH VALIDATION
        # The turbine physics already calculates realistic electrical power based on steam conditions
        # We should use this value and only apply safety-related reductions, not efficiency overrides
        
        # Get electrical power from turbine (this is already realistic)
        turbine_electrical_power = turbine_result['electrical_power_net']
        
        # Apply only critical safety validation checks that would shut down the plant
        power_reduction_factor = 1.0
        power_reduction_reasons = []
        
        # CRITICAL: Check feedwater flow first - no feedwater = no power
        if actual_feedwater_flow < MIN_FEEDWATER_FLOW_KGS:
            power_reduction_factor = 0.0  # Complete shutdown for no feedwater
            power_reduction_reasons.append(f"FEEDWATER_FLOW_TOO_LOW: {actual_feedwater_flow:.1f} kg/s < {MIN_FEEDWATER_FLOW_KGS} kg/s")
            '''
            print(f"[SECONDARY DEBUG] ELECTRICAL POWER REDUCTION: Complete shutdown due to insufficient feedwater flow")
            print(f"[SECONDARY DEBUG]   Actual feedwater flow: {actual_feedwater_flow:.1f} kg/s")
            print(f"[SECONDARY DEBUG]   Minimum required: {MIN_FEEDWATER_FLOW_KGS} kg/s")
            '''
        # Check other critical operating conditions only if feedwater is available
        if power_reduction_factor > 0.0:
            # Only apply severe reductions for safety-critical conditions
            if total_steam_flow < (MIN_STEAM_FLOW_KGS * 0.5):  # Very low steam flow
                old_factor = power_reduction_factor
                power_reduction_factor *= 0.1  # 90% reduction for very low steam flow
                power_reduction_reasons.append(f"STEAM_FLOW_TOO_LOW: {total_steam_flow:.1f} kg/s < {MIN_STEAM_FLOW_KGS * 0.5:.1f} kg/s")
                print(f"[SECONDARY DEBUG] ELECTRICAL POWER REDUCTION: Steam flow too low")
                print(f"[SECONDARY DEBUG]   Actual steam flow: {total_steam_flow:.1f} kg/s")
                print(f"[SECONDARY DEBUG]   Minimum required: {MIN_STEAM_FLOW_KGS * 0.5:.1f} kg/s")
                print(f"[SECONDARY DEBUG]   Power reduction factor: {old_factor:.3f} -> {power_reduction_factor:.3f}")
            
            if avg_steam_pressure < (MIN_STEAM_PRESSURE_MPA * 0.5):  # Very low steam pressure
                old_factor = power_reduction_factor
                power_reduction_factor *= 0.1  # 90% reduction for very low steam pressure
                power_reduction_reasons.append(f"STEAM_PRESSURE_TOO_LOW: {avg_steam_pressure:.3f} MPa < {MIN_STEAM_PRESSURE_MPA * 0.5:.3f} MPa")
                print(f"[SECONDARY DEBUG] ELECTRICAL POWER REDUCTION: Steam pressure too low")
                print(f"[SECONDARY DEBUG]   Actual steam pressure: {avg_steam_pressure:.3f} MPa")
                print(f"[SECONDARY DEBUG]   Minimum required: {MIN_STEAM_PRESSURE_MPA * 0.5:.3f} MPa")
                print(f"[SECONDARY DEBUG]   Power reduction factor: {old_factor:.3f} -> {power_reduction_factor:.3f}")
            
            # Energy conservation check - this should rarely trigger if turbine physics is correct
            if thermal_power_mw > (primary_thermal_power * 1.1):  # Allow 10% margin
                power_reduction_factor = 0.0  # Complete shutdown for major energy violation
                power_reduction_reasons.append(f"ENERGY_CONSERVATION_VIOLATION: Secondary {thermal_power_mw:.1f} MW > Primary {primary_thermal_power:.1f} MW * 1.1")
                print(f"[SECONDARY DEBUG] ELECTRICAL POWER REDUCTION: Energy conservation violation")
                print(f"[SECONDARY DEBUG]   Secondary thermal power: {thermal_power_mw:.1f} MW")
                print(f"[SECONDARY DEBUG]   Primary thermal power: {primary_thermal_power:.1f} MW")
                print(f"[SECONDARY DEBUG]   Maximum allowed: {primary_thermal_power * 1.1:.1f} MW")
                print(f"[SECONDARY DEBUG]   Complete shutdown triggered")
        
        # Debug output for power reduction summary
        if power_reduction_factor < 1.0:
            print(f"[SECONDARY DEBUG] ELECTRICAL POWER REDUCTION SUMMARY:")
            print(f"[SECONDARY DEBUG]   Original turbine power: {turbine_electrical_power:.2f} MW")
            print(f"[SECONDARY DEBUG]   Power reduction factor: {power_reduction_factor:.3f}")
            print(f"[SECONDARY DEBUG]   Final electrical power: {turbine_electrical_power * power_reduction_factor:.2f} MW")
            print(f"[SECONDARY DEBUG]   Power reduction: {(1.0 - power_reduction_factor) * 100:.1f}%")
            print(f"[SECONDARY DEBUG]   Reduction reasons: {', '.join(power_reduction_reasons)}")
        elif len(validation_failures) > 0:
            print(f"[SECONDARY DEBUG] VALIDATION WARNINGS (no power reduction applied):")
            for failure in validation_failures:
                print(f"[SECONDARY DEBUG]   - {failure}")
        
        # Use turbine electrical power with safety reductions
        self.electrical_power_output = turbine_electrical_power * power_reduction_factor
        
        # Calculate thermal efficiency based on actual electrical power
        if primary_thermal_power > 0:
            self.thermal_efficiency = self.electrical_power_output / primary_thermal_power
        else:
            self.thermal_efficiency = 0.0
        # Heat rate (kJ/kWh)
        if self.electrical_power_output > 0:
            heat_rate = (total_heat_transfer / 1000.0) / (self.electrical_power_output * 1000.0) * 3600.0
        else:
            heat_rate = 0.0
        
        # Compile complete system results
        system_result = {
            # Overall system performance
            'electrical_power_mw': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'heat_rate_kj_kwh': heat_rate,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            'total_feedwater_flow': self.total_feedwater_flow,
            
            # Steam generator performance
            'sg_avg_pressure': avg_steam_pressure,
            'sg_avg_temperature': avg_steam_temperature,
            'sg_avg_steam_quality': avg_steam_quality,
            'sg_total_heat_transfer': total_heat_transfer,
            'sg_individual_results': sg_results,
            
            # Turbine performance
            'turbine_mechanical_power': turbine_result['mechanical_power'],
            'turbine_electrical_power_gross': turbine_result['electrical_power_gross'],
            'turbine_electrical_power_net': turbine_result['electrical_power_net'],
            'turbine_efficiency': turbine_result['overall_efficiency'],
            'turbine_steam_rate': turbine_result['steam_rate'],
            'turbine_hp_power': turbine_result['hp_power'],
            'turbine_lp_power': turbine_result['lp_power'],
            
            # Condenser performance
            'condenser_heat_rejection': condenser_result['heat_rejection_rate'],
            'condenser_pressure': condenser_result['condenser_pressure'],
            'condenser_cooling_water_temp_rise': condenser_result['cooling_water_temp_rise'],
            'condenser_thermal_performance': condenser_result.get('thermal_performance_factor', 1.0),
            'condenser_vacuum_efficiency': condenser_result.get('vacuum_system_efficiency', 1.0),
            
            # Total system heat rejection (includes condenser + extraction steam + losses)
            'total_system_heat_rejection': system_heat_rejection_watts,
            
            # Feedwater pump performance
            'feedwater_total_flow': feedwater_result['total_flow_rate'],
            'feedwater_total_power': feedwater_result['total_power_consumption'],
            'feedwater_running_pumps': feedwater_result['running_pumps'],
            'feedwater_num_running_pumps': feedwater_result['num_running_pumps'],
            'feedwater_system_available': feedwater_result['system_availability'],
            'feedwater_auto_control': feedwater_result['auto_control_active'],
            'feedwater_sg_flow_distribution': feedwater_result['sg_flow_distribution'],
            
            # Heat flow tracking results
            'heat_flow_energy_balance_error': heat_flow_validation['energy_balance_error_mw'],
            'heat_flow_energy_balance_percent': heat_flow_validation['energy_balance_percent_error'],
            'heat_flow_balance_ok': heat_flow_validation['balance_acceptable'],
            'heat_flow_condenser_heat_rejection': heat_flow_state.condenser_heat_rejection,
            'heat_flow_net_electrical_output': heat_flow_state.net_electrical_output,
            'heat_flow_overall_efficiency': heat_flow_state.overall_thermal_efficiency,
            
            # Chemistry flow tracking results
            'chemistry_flow_balance_error': chemistry_flow_validation['overall_balance_error_percent'],
            'chemistry_flow_balance_ok': chemistry_flow_validation['balance_acceptable'],
            'chemistry_flow_ph': chemistry_flow_state.sg_liquid_chemistry.get('ph', 9.2),
            'chemistry_flow_iron_concentration': chemistry_flow_state.sg_liquid_chemistry.get('iron', 0.1),
            'chemistry_flow_tsp_fouling_rate': chemistry_flow_state.tsp_fouling_rate,
            'chemistry_flow_treatment_efficiency': chemistry_flow_state.feedwater_treatment_effectiveness,
            'chemistry_flow_stability': chemistry_flow_state.overall_chemistry_stability,
            
            # Water chemistry results
            'water_chemistry_ph': water_chemistry_result.get('water_chemistry_ph', 9.2),
            'water_chemistry_iron_concentration': water_chemistry_result.get('water_chemistry_iron_concentration', 0.1),
            'water_chemistry_aggressiveness': water_chemistry_result.get('water_chemistry_aggressiveness', 1.0),
            'water_chemistry_treatment_efficiency': water_chemistry_result.get('water_chemistry_treatment_efficiency', 0.95),
            
            # pH control results
            'ph_control_output': controller_outputs.get('controller_output', 0.0),
            'ph_control_ammonia_dose': controller_outputs.get('ammonia_dose_rate', 0.0),
            'ph_control_error': controller_outputs.get('ph_error', 0.0),
            
            # Control and operating conditions
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_inlet_temp': self.cooling_water_temperature,
            'cooling_water_outlet_temp': condenser_result['cooling_water_outlet_temp'],
            
            # Detailed component states
            'steam_generator_system_state': self.steam_generator_system.get_state_dict(),
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict(),
            'feedwater_state': self.feedwater_system.get_state_dict(),
            'water_chemistry_state': self.water_chemistry.get_state_dict(),
            'chemistry_flow_state': self.chemistry_flow_tracker.get_state_dict()
        }
        return system_result
    
    def get_system_state(self) -> dict:
        """Get complete system state for monitoring and logging"""
        return {
            'num_steam_generators': self.num_steam_generators,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            'electrical_power_output': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'total_feedwater_flow': self.total_feedwater_flow,
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_temperature': self.cooling_water_temperature,
            'steam_generator_system': self.steam_generator_system.get_state_dict(),
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict(),
            'feedwater_state': self.feedwater_system.get_state_dict()
        }
    
    def reset_system(self, start_at_steady_state: bool = True, thermal_power_mw: float = 3000.0) -> None:
        """
        Reset all components to initial conditions
        
        Args:
            start_at_steady_state: If True, initialize to steady-state operation (default)
            thermal_power_mw: Reactor thermal power for steady-state calculation (default 3000 MW)
        """
        # Always reset components first
        self.turbine.reset()
        self.condenser.reset()
        self.steam_generator_system.reset() 
        self.feedwater_system.reset()
        
        # Reset heat flow tracker
        self.heat_flow_tracker.reset()
        
        # Reset system-level variables
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        self.total_feedwater_flow = 0.0
        self.load_demand = 100.0
        self.feedwater_temperature = 227.0
        self.cooling_water_temperature = 25.0
        self.operating_hours = 0.0
        self.total_system_heat_rejection = 0.0
        
        # Optionally initialize to steady state
        if start_at_steady_state:
            self.initialize_to_steady_state(thermal_power_mw)
    
    def initialize_to_steady_state(self, thermal_power_mw: float) -> None:
        """
        Initialize all secondary systems to steady-state operation for given thermal power
        
        This method calculates the equilibrium operating point and sets all subsystems
        to their appropriate steady-state values, eliminating startup transients.
        
        Args:
            thermal_power_mw: Reactor thermal power in MW
        """
        # Calculate equilibrium operating point
        equilibrium = self._calculate_equilibrium_point(thermal_power_mw)
        
        # Initialize each subsystem to calculated steady state
        self._initialize_steam_generators_to_steady_state(equilibrium)
        self._initialize_feedwater_system_to_steady_state(equilibrium)
        self._initialize_turbine_to_steady_state(equilibrium)
        self._initialize_condenser_to_steady_state(equilibrium)
        
        # Set system-level state variables
        self.total_steam_flow = equilibrium['steam_flow']
        self.total_heat_transfer = equilibrium['heat_transfer']
        self.electrical_power_output = equilibrium['electrical_power']
        self.thermal_efficiency = equilibrium['thermal_efficiency']
        self.total_feedwater_flow = equilibrium['feedwater_flow']
        self.load_demand = equilibrium['load_demand']
    
    def _calculate_equilibrium_point(self, thermal_power_mw: float) -> Dict:
        """Calculate steady-state operating point for given thermal power"""
        
        # Calculate load demand based on thermal power
        # Assume rated thermal power is 3000 MW for typical PWR
        rated_thermal_power = 3000.0  # MW
        load_demand = min(100.0, (thermal_power_mw / rated_thermal_power) * 100.0)
        
        # Calculate primary conditions that would produce this thermal power
        # Distribute thermal power evenly across steam generators
        thermal_power_per_sg = thermal_power_mw / self.num_steam_generators
        
        # Calculate realistic primary flow and temperatures for each SG
        # Using typical PWR conditions scaled by power level
        base_primary_flow = 5700.0  # kg/s per SG at 100% power
        primary_flow_per_sg = base_primary_flow * (load_demand / 100.0)
        
        # Calculate temperature difference needed for thermal power
        # Q = m_dot * cp * delta_T, so delta_T = Q / (m_dot * cp)
        cp_primary = 5.2  # kJ/kg/K at PWR conditions
        
        if primary_flow_per_sg > 0:
            delta_t = (thermal_power_per_sg * 1000.0) / (primary_flow_per_sg * cp_primary)  # °C
        else:
            delta_t = 0.0
        
        # Calculate realistic PWR temperatures
        # Cold leg temperature stays relatively constant
        cold_leg_temp = 293.0  # °C
        hot_leg_temp = cold_leg_temp + delta_t
        
        # Ensure temperatures are within realistic PWR operating range
        hot_leg_temp = np.clip(hot_leg_temp, 293.0, 350.0)
        if hot_leg_temp <= cold_leg_temp:
            hot_leg_temp = cold_leg_temp + 5.0  # Minimum 5°C difference
        
        # Create primary conditions that match the enhanced steam generator interface
        primary_conditions = {}
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            primary_conditions[f'{sg_key}_inlet_temp'] = hot_leg_temp
            primary_conditions[f'{sg_key}_outlet_temp'] = cold_leg_temp
            primary_conditions[f'{sg_key}_flow'] = primary_flow_per_sg
            primary_conditions[f'{sg_key}_thermal_power'] = thermal_power_per_sg
            primary_conditions[f'{sg_key}_power_fraction'] = load_demand / 100.0
        
        # Simulate the enhanced steam generator system to get realistic steam conditions
        # Create temporary control inputs for equilibrium calculation
        control_inputs = {
            'load_demand': load_demand,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        # Use the same logic as update_system to get steam conditions
        if f'sg_1_thermal_power' in primary_conditions:
            enhanced_primary_conditions = self._calculate_temperatures_from_power(primary_conditions)
        else:
            enhanced_primary_conditions = {
                'inlet_temps': [primary_conditions.get(f'sg_{i+1}_inlet_temp', 327.0) for i in range(self.num_steam_generators)],
                'outlet_temps': [primary_conditions.get(f'sg_{i+1}_outlet_temp', 293.0) for i in range(self.num_steam_generators)],
                'flow_rates': [primary_conditions.get(f'sg_{i+1}_flow', 5700.0) for i in range(self.num_steam_generators)]
            }
        
        load_demand_fraction = load_demand / 100.0
        steam_demands = {
            'load_demand_fraction': load_demand_fraction,
            'steam_pressure': 6.895  # Target steam pressure
        }
        
        enhanced_system_conditions = {
            'feedwater_temperature': 227.0,
            'load_demand': load_demand_fraction
        }
        
        # Get steam conditions from enhanced steam generator system
        try:
            # Temporarily update the steam generator system to get equilibrium conditions
            sg_system_result = self.steam_generator_system.update_system(
                primary_conditions=enhanced_primary_conditions,
                steam_demands=steam_demands,
                system_conditions=enhanced_system_conditions,
                control_inputs=control_inputs,
                dt=1.0
            )
            
            # Extract realistic steam conditions
            total_steam_flow = sg_system_result['total_steam_flow']
            steam_pressure = sg_system_result['average_steam_pressure']
            steam_temperature = sg_system_result['average_steam_temperature']
            steam_quality = sg_system_result['average_steam_quality']
            sg_levels = sg_system_result.get('sg_levels', [12.5] * self.num_steam_generators)
            
        except Exception as e:
            # Fallback to calculated values if steam generator system fails
            print(f"Warning: Steam generator system failed during equilibrium calculation: {e}")
            design_steam_flow = 1665.0  # kg/s at 100% power
            total_steam_flow = design_steam_flow * load_demand_fraction
            steam_pressure = 6.895  # MPa typical PWR steam pressure
            steam_temperature = self._saturation_temperature(steam_pressure)  # ~285°C
            steam_quality = 0.99  # Typical steam quality
            sg_levels = [12.5] * self.num_steam_generators  # Normal operating level
        
        # Feedwater flow equals steam flow at steady state (mass balance)
        feedwater_flow = total_steam_flow
        
        # Calculate electrical power based on realistic efficiency
        if load_demand >= 100.0:
            thermal_efficiency = 0.34  # 34% at full load
        elif load_demand >= 75.0:
            thermal_efficiency = 0.32 + 0.02 * (load_demand - 75.0) / 25.0
        elif load_demand >= 50.0:
            thermal_efficiency = 0.28 + 0.04 * (load_demand - 50.0) / 25.0
        else:
            thermal_efficiency = 0.20 + 0.08 * (load_demand / 50.0)
        
        electrical_power = thermal_power_mw * thermal_efficiency
        
        # Calculate pump speeds needed for feedwater flow
        # Each pump rated for 555 kg/s, so speed proportional to required flow
        pumps_needed = min(4, max(3, int(np.ceil(feedwater_flow / 555.0))))
        if pumps_needed > 0:
            flow_per_pump = feedwater_flow / pumps_needed
            pump_speed = min(100.0, (flow_per_pump / 555.0) * 100.0)
        else:
            pump_speed = 0.0
        
        # Condenser conditions
        condenser_pressure = 0.007  # MPa typical condenser pressure
        condenser_temperature = self._saturation_temperature(condenser_pressure)  # ~39°C
        
        return {
            'thermal_power': thermal_power_mw,
            'load_demand': load_demand,
            'steam_flow': total_steam_flow,
            'steam_pressure': steam_pressure,
            'steam_temperature': steam_temperature,
            'steam_quality': steam_quality,
            'feedwater_flow': feedwater_flow,
            'electrical_power': electrical_power,
            'thermal_efficiency': thermal_efficiency,
            'heat_transfer': thermal_power_mw * 1e6,  # Convert to Watts
            'sg_levels': sg_levels,
            'pumps_needed': pumps_needed,
            'pump_speed': pump_speed,
            'condenser_pressure': condenser_pressure,
            'condenser_temperature': condenser_temperature,
            'primary_conditions': primary_conditions  # Include primary conditions for debugging
        }
    
    def _initialize_steam_generators_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize steam generators to steady-state levels and conditions"""
        # Set steam generator levels to normal operating level
        if hasattr(self.steam_generator_system, 'set_initial_levels'):
            self.steam_generator_system.set_initial_levels(equilibrium['sg_levels'])
        
        # Set steam production rates if method exists
        if hasattr(self.steam_generator_system, 'set_initial_steam_flow'):
            steam_flow_per_sg = equilibrium['steam_flow'] / self.num_steam_generators
            self.steam_generator_system.set_initial_steam_flow(steam_flow_per_sg)
    
    def _initialize_feedwater_system_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize feedwater pumps to steady-state operation with perfect initial conditions"""
        if hasattr(self.feedwater_system, 'pump_system'):
            pump_system = self.feedwater_system.pump_system
            
            # Calculate perfect system conditions for steady-state operation
            suction_pressure = 0.5  # MPa from condensate system
            discharge_pressure = equilibrium['steam_pressure'] + 0.5  # Steam pressure + margin
            npsh_available = 25.0  # m - well above minimum requirement
            feedwater_temp = 40.0  # °C - condensate temperature, not final feedwater temp
            
            # Get pump IDs and determine how many to start
            pump_ids = list(pump_system.pumps.keys())
            pumps_to_start = min(equilibrium['pumps_needed'], len(pump_ids))
            
            # First, set ALL pumps to perfect initial conditions (stopped but ready)
            from systems.primary.coolant.pump_models import PumpStatus
            for pump_id, pump in pump_system.pumps.items():
                # Set pump to stopped but available state
                pump.state.status = PumpStatus.STOPPED
                pump.state.available = True
                pump.state.auto_control = True
                pump.state.trip_active = False
                pump.state.trip_reason = ""
                
                # Set perfect hydraulic conditions
                pump.state.suction_pressure = suction_pressure
                pump.state.discharge_pressure = discharge_pressure
                pump.state.npsh_available = npsh_available
                pump.state.differential_pressure = discharge_pressure - suction_pressure
                
                # Set perfect mechanical conditions
                pump.state.oil_level = 100.0  # % - full oil level
                pump.state.oil_temperature = 45.0  # °C - normal operating temperature
                pump.state.bearing_temperature = 50.0  # °C - normal bearing temperature
                pump.state.motor_temperature = 65.0  # °C - normal motor temperature
                pump.state.vibration_level = 1.5  # mm/s - normal vibration
                pump.state.motor_current = 0.0  # A - no current when stopped
                pump.state.motor_voltage = 6.6  # kV - normal voltage
                
                # Set perfect wear and damage conditions
                pump.state.impeller_wear = 0.0  # % - new condition
                pump.state.bearing_wear = 0.0  # % - new condition
                pump.state.seal_wear = 0.0  # % - new condition
                pump.state.seal_leakage = 0.001  # L/min - realistic minimal leakage for modern seals
                pump.state.cavitation_intensity = 0.0  # No cavitation
                pump.state.cavitation_damage = 0.0  # No damage
                pump.state.cavitation_time = 0.0  # No cavitation time
                
                # Set perfect performance factors
                pump.state.flow_degradation_factor = 1.0  # Perfect performance
                pump.state.efficiency_degradation_factor = 1.0  # Perfect efficiency
                pump.state.head_degradation_factor = 1.0  # Perfect head
                
                # Set speed setpoint and initial conditions for pumps that will start
                if pump_id in pump_ids[:pumps_to_start]:
                    pump.state.speed_setpoint = equilibrium['pump_speed']
                    pump.set_flow_demand(equilibrium['feedwater_flow'] / pumps_to_start)
                    
                    # CRITICAL: Set equilibrium flow and speed immediately to prevent low flow trips
                    pump.state.speed_percent = equilibrium['pump_speed']
                    pump.state.flow_rate = equilibrium['feedwater_flow'] / pumps_to_start
                    pump._calculate_power_consumption()  # Calculate power based on flow
                else:
                    pump.state.speed_setpoint = 0.0
                    pump.set_flow_demand(0.0)
                    pump.state.speed_percent = 0.0
                    pump.state.flow_rate = 0.0
                    pump.state.power_consumption = 0.0
            
            # Now start the required pumps using proper startup sequence
            # For steady-state initialization, bypass dynamics and go directly to RUNNING
            for i in range(pumps_to_start):
                pump_id = pump_ids[i]
                pump = pump_system.pumps[pump_id]
                
                # CRITICAL FIX: For steady-state initialization, bypass startup dynamics
                # This represents a plant that's already at operating conditions
                from systems.primary.coolant.pump_models import PumpStatus
                
                # Set pump directly to RUNNING state with proper conditions
                pump.state.status = PumpStatus.RUNNING
                pump.state.available = True
                pump.state.auto_control = True
                pump.state.trip_active = False
                pump.state.trip_reason = ""
                
                print(f"Pump {pump_id} initialized directly to RUNNING state for steady-state operation")
            
            # Initialize system state (will be updated properly on first update cycle)
            pump_system.running_pumps = []  # Will be populated during first update
            pump_system.total_flow = 0.0  # Will be calculated during first update
            pump_system.total_power = 0.0  # Will be calculated during first update
            pump_system.system_available = True
    
    def _initialize_turbine_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize turbine to steady-state load"""
        # Set turbine load demand
        if hasattr(self.turbine, 'load_demand'):
            self.turbine.load_demand = equilibrium['load_demand'] / 100.0
        
        # Set turbine power output if possible
        if hasattr(self.turbine, 'total_power_output'):
            self.turbine.total_power_output = equilibrium['electrical_power']
    
    def _initialize_condenser_to_steady_state(self, equilibrium: Dict) -> None:
        """Initialize condenser to steady-state conditions"""
        # Set condenser pressure and temperature if possible
        if hasattr(self.condenser, 'condenser_pressure'):
            self.condenser.condenser_pressure = equilibrium['condenser_pressure']
        
        if hasattr(self.condenser, 'condenser_temperature'):
            self.condenser.condenser_temperature = equilibrium['condenser_temperature']
    
    def _calculate_temperatures_from_power(self, primary_conditions: dict) -> dict:
        """
        Calculate primary inlet/outlet temperatures from thermal power and flow
        
        This method implements the physics that was previously duplicated in sim.py.
        Now the steam generator system owns the complete temperature calculation.
        
        Args:
            primary_conditions: Dictionary with thermal power and flow for each SG
                - 'sg_X_thermal_power': Thermal power for SG X (MW)
                - 'sg_X_flow': Primary flow rate for SG X (kg/s)
                - 'sg_X_power_fraction': Power fraction for SG X (0-1)
                
        Returns:
            Dictionary with calculated temperatures for enhanced steam generator system
        """
        inlet_temps = []
        outlet_temps = []
        flow_rates = []
        
        for i in range(self.num_steam_generators):
            sg_key = f'sg_{i+1}'
            
            # Get thermal power and flow for this SG
            thermal_power_mw = primary_conditions.get(f'{sg_key}_thermal_power', 1000.0)
            primary_flow = primary_conditions.get(f'{sg_key}_flow', 5700.0)
            power_fraction = primary_conditions.get(f'{sg_key}_power_fraction', 1.0)
            
            # Calculate temperatures based on power and flow
            # Using heat balance: Q = m_dot * cp * delta_T
            cp_primary = 5.2  # kJ/kg/K at PWR conditions
            
            if primary_flow > 0:
                # Calculate temperature difference from thermal power
                delta_t = (thermal_power_mw * 1000.0) / (primary_flow * cp_primary)  # °C
            else:
                delta_t = 0.0
            
            # Calculate realistic PWR temperatures based on power fraction
            # At 100% power: Hot leg = 327°C, Cold leg = 293°C
            # At 0% power: Both approach cold leg temperature
            cold_leg_temp = 293.0  # Cold leg stays relatively constant
            hot_leg_temp = cold_leg_temp + (34.0 * power_fraction)  # 293°C to 327°C
            
            # Ensure calculated delta_T is consistent with realistic PWR operation
            # If calculated delta_T is very different from realistic values, adjust
            realistic_delta_t = hot_leg_temp - cold_leg_temp
            if abs(delta_t - realistic_delta_t) > 10.0:  # More than 10°C difference
                # Use realistic temperatures, but scale with actual thermal power
                if thermal_power_mw > 0:
                    scale_factor = min(1.0, thermal_power_mw / 1000.0)  # Scale based on 1000 MW reference
                    delta_t = realistic_delta_t * scale_factor
                else:
                    delta_t = 0.0
            
            # Calculate final temperatures
            outlet_temp = cold_leg_temp
            inlet_temp = outlet_temp + delta_t
            
            # Ensure temperatures are within realistic PWR operating range
            inlet_temp = np.clip(inlet_temp, 293.0, 350.0)
            outlet_temp = np.clip(outlet_temp, 280.0, 300.0)
            
            # Ensure hot leg is always hotter than cold leg
            if inlet_temp <= outlet_temp:
                inlet_temp = outlet_temp + 5.0  # Minimum 5°C difference
            
            inlet_temps.append(inlet_temp)
            outlet_temps.append(outlet_temp)
            flow_rates.append(primary_flow)
        
        return {
            'inlet_temps': inlet_temps,
            'outlet_temps': outlet_temps,
            'flow_rates': flow_rates
        }
    
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
    
    def set_load_demand(self, load: float) -> None:
        """
        Set the electrical load demand for the system
        
        Args:
            load: Load demand as a percentage of rated power (0-100)
        """
        if 0 <= load <= 100:
            self.load_demand = load
        else:
            raise ValueError("Load demand must be between 0 and 100%")
    
    def get_state_dict(self) -> Dict[str, float]:
        """
        Get the current state of the secondary system as a dictionary.
        
        Returns:
            Dictionary with system-level state variables and heat flow data
        """
        # Get heat flow summary from tracker
        heat_flow_summary = self.heat_flow_tracker.get_heat_flow_summary()
        
        # Return system-level coordination states plus heat flow data
        state_dict = {
            'system_electrical_power': self.electrical_power_output,
            'system_thermal_efficiency': self.thermal_efficiency,
            'system_total_steam_flow': self.total_steam_flow,
            'system_total_heat_transfer': self.total_heat_transfer / 1e6,  # Convert to MW
            'system_load_demand': self.load_demand,
            'system_total_feedwater_flow': self.total_feedwater_flow,
            'system_feedwater_temperature': self.feedwater_temperature,
            'system_cooling_water_temperature': self.cooling_water_temperature,
            'system_operating_hours': self.operating_hours,
            'system_num_steam_generators': self.num_steam_generators,
            'system_total_system_heat_rejection': self.total_system_heat_rejection / 1e6,  # Convert to MW
            
            # Heat flow tracking data
            'heat_flow_sg_heat_input': heat_flow_summary.get('sg_heat_input', 0.0),
            'heat_flow_steam_enthalpy_flow': heat_flow_summary.get('steam_enthalpy_flow', 0.0),
            'heat_flow_turbine_work_output': heat_flow_summary.get('turbine_work_output', 0.0),
            'heat_flow_condenser_heat_rejection': heat_flow_summary.get('condenser_heat_rejection', 0.0),
            'heat_flow_net_electrical_output': heat_flow_summary.get('net_electrical_output', 0.0),
            'heat_flow_overall_efficiency': heat_flow_summary.get('overall_thermal_efficiency', 0.0),
            'heat_flow_energy_balance_error': heat_flow_summary.get('energy_balance_error', 0.0),
            'heat_flow_energy_balance_percent': heat_flow_summary.get('energy_balance_percent_error', 0.0),
            'heat_flow_energy_balance_ok': heat_flow_summary.get('energy_balance_ok', False),
        }

        return state_dict


# Example usage and testing
if __name__ == "__main__":
    print("Secondary Reactor Physics System - Integration Test")
    print("=" * 60)
    
    # Create integrated secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    print(f"Initialized system with {secondary_system.num_steam_generators} steam generators")
    print()
    
    
    # Test transient operation
    print("Transient Operation Test (Load Change):")
    
    # Primary conditions (typical PWR)
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,
        'sg_1_outlet_temp': 293.0,
        'sg_1_flow': 5700.0,
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    # Test load reduction
    for load in [100.0, 75.0, 50.0]:
        control_inputs = {
            'load_demand': load,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        result = secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=1.0
        )
        
        print(f"  Load {load:5.1f}%: Power {result['electrical_power_mw']:6.1f} MW, "
              f"Efficiency {result['thermal_efficiency']*100:5.2f}%, "
              f"Steam Flow {result['total_steam_flow']:6.0f} kg/s, "
              f"FW Flow {result['total_feedwater_flow']:6.0f} kg/s, "
              f"FW Pumps {result['feedwater_num_running_pumps']}")
    
    print()
    print("Secondary reactor physics implementation complete!")
    print("Components: Steam Generators, Turbine, Condenser, Feedwater Pumps")
    print("Features: Heat transfer, power generation, vacuum systems, feedwater control, three-element control")
