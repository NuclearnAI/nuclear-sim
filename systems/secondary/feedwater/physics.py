"""
Enhanced Feedwater Physics Model for PWR Feedwater System

This module implements the main enhanced feedwater physics model that orchestrates
all feedwater subsystems following the condenser's proven architectural pattern.

Parameter Sources:
- Power Plant Engineering (Black & Veatch)
- Feedwater System Design Guidelines
- EPRI Feedwater System Performance Standards
- PWR Plant Operating Procedures

Physical Basis:
- Integrated multi-pump system coordination
- Three-element control with steam quality compensation
- Water chemistry effects on system performance
- Advanced cavitation and wear modeling
- Protection systems and trip logic
- Performance optimization and diagnostics
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Import state management interfaces
from simulator.state import StateProvider, StateVariable, StateCategory, make_state_name, auto_register

# Import heat flow tracking
from ..heat_flow_tracker import HeatFlowProvider, ThermodynamicProperties

# Import chemistry flow tracking
from ..chemistry_flow_tracker import ChemistryFlowProvider, ChemicalSpecies

from ..component_descriptions import FEEDWATER_COMPONENT_DESCRIPTIONS
from .pump_system import FeedwaterPumpSystem, FeedwaterPumpSystemConfig
from .level_control import ThreeElementControl
from ..water_chemistry import WaterChemistry, WaterChemistryConfig
from .performance_monitoring import PerformanceDiagnostics, PerformanceDiagnosticsConfig
from .protection_system import FeedwaterProtectionSystem, FeedwaterProtectionConfig
from .config import FeedwaterConfig, create_standard_feedwater_config

warnings.filterwarnings("ignore")


@auto_register("SECONDARY", "feedwater", allow_no_id=True,
               description=FEEDWATER_COMPONENT_DESCRIPTIONS['enhanced_feedwater_physics'])
class EnhancedFeedwaterPhysics(HeatFlowProvider, ChemistryFlowProvider):
    """
    Enhanced feedwater physics model - analogous to EnhancedCondenserPhysics
    
    This model integrates:
    1. Multi-pump system coordination and control
    2. Three-element control with steam quality compensation
    3. Water chemistry effects on performance
    4. Advanced cavitation and wear modeling
    5. Protection systems and trip logic
    6. Performance diagnostics and optimization
    
    Physical Models Used:
    - Pump system hydraulics with degradation effects
    - Three-element control with feedforward/feedback
    - Water chemistry impact on pump performance
    - Cavitation modeling with damage accumulation
    - Mechanical wear tracking and prediction
    - Protection logic with emergency response
    
    Uses @auto_register decorator for automatic state collection with proper naming.
    """
    
    def __init__(self, config: Optional[FeedwaterConfig] = None, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced feedwater physics model
        
        Args:
            config: FeedwaterConfig object (supports dataclass-wizard)
            config_dict: Configuration dictionary from unified configuration system
        """
        if config_dict is not None:
            # Use unified configuration system with dataclass-wizard
            try:
                self.config = FeedwaterConfig.from_dict(config_dict)
                print(f"FEEDWATER: Using unified configuration system with dataclass-wizard")
            except Exception as e:
                print(f"FEEDWATER: Failed to deserialize with dataclass-wizard: {e}")
                print(f"FEEDWATER: Falling back to default configuration")
                self.config = create_standard_feedwater_config()
        elif config is not None:
            # Use provided configuration
            self.config = config
            print(f"FEEDWATER: Using provided FeedwaterConfig")
        else:
            # Use defaults
            self.config = create_standard_feedwater_config()
            print(f"FEEDWATER: Using default configuration")
        
        print(f"FEEDWATER: Initialized with system_id={self.config.system_id}, "
              f"design_flow={self.config.design_total_flow} kg/s")
        
        # Initialize subsystems with configurations from FeedwaterConfig
        pump_config = self.config.pump_system
        control_config = self.config.control_system
        water_config = self.config.water_treatment
        diagnostics_config = self.config.performance_monitoring
        protection_config = self.config.protection_system
        
        # Create pump system config with proper parameters
        from .pump_system import FeedwaterPumpSystemConfig, FeedwaterPumpConfig
        
        # Create individual pump config with correct flow rates from feedwater config
        individual_pump_config = FeedwaterPumpConfig(
            pump_id="FWP-TEMPLATE",  # Will be overridden for each pump
            rated_flow=pump_config.design_flow_per_pump,
            rated_power=pump_config.design_flow_per_pump * 0.02,  # Approximate 20 kW per kg/s
            rated_head=pump_config.design_head_per_pump
        )
        
        pump_system_config = FeedwaterPumpSystemConfig(
            num_steam_generators=self.config.num_steam_generators,
            pumps_per_sg=1,
            spare_pumps=1,
            pump_config=individual_pump_config,  # Now properly configured
            auto_sequencing=True,
            load_sharing=True,
            auto_start_enabled=True,
            startup_sequence_enabled=True,
            min_running_pumps=3,
            max_running_pumps=4
        )
        
        # Create subsystems
        self.pump_system = FeedwaterPumpSystem(pump_system_config)
        self.level_control = ThreeElementControl(
            control_config, 
            num_steam_generators=self.config.num_steam_generators,
            design_sg_level=self.config.design_sg_level,
            design_flow_per_sg=self.config.design_total_flow / self.config.num_steam_generators
        )
        
        # Use unified water chemistry system instead of creating our own
        # The water chemistry is managed at the secondary system level
        self.water_quality = None  # Will be set by parent system if needed
        
        # Create compatible diagnostics config from new config structure
        from .performance_monitoring import PerformanceDiagnosticsConfig, CavitationConfig, WearTrackingConfig
        compatible_diagnostics_config = PerformanceDiagnosticsConfig(
            cavitation_config=CavitationConfig(),
            wear_tracking_config=WearTrackingConfig(),
            continuous_monitoring_enabled=diagnostics_config.enable_performance_monitoring,
            detailed_analysis_interval=diagnostics_config.efficiency_monitoring_interval,
            predictive_maintenance_horizon=diagnostics_config.performance_trend_window
        )
        self.diagnostics = PerformanceDiagnostics(compatible_diagnostics_config)
        self.protection_system = FeedwaterProtectionSystem(protection_config)
        
        # CRITICAL: Apply initial conditions after creating components
        self._apply_initial_conditions()
        
        print(f"FEEDWATER: Applied initial conditions from config")
        
        # Enhanced feedwater state
        self.total_flow_rate = 0.0                       # kg/s total system flow
        self.total_power_consumption = 0.0               # MW total power consumption
        self.system_efficiency = 0.0                     # Overall system efficiency
        self.system_availability = True                  # System availability status
        
        # Steam generator conditions
        self.sg_levels = [12.5] * self.config.num_steam_generators      # m SG levels
        self.sg_pressures = [6.895] * self.config.num_steam_generators  # MPa SG pressures
        self.sg_steam_flows = [555.0] * self.config.num_steam_generators # kg/s steam flows
        self.sg_steam_qualities = [0.99] * self.config.num_steam_generators # Steam qualities
        
        # Performance tracking
        self.performance_factor = 1.0                    # Overall performance factor
        self.operating_hours = 0.0                       # Total operating hours
        self.maintenance_factor = 1.0                    # Maintenance effectiveness factor
        
        # Control state
        self.control_mode = "automatic"                  # Control mode
        self.load_demand = 1.0                          # Load demand (0-1)
    
    def _apply_initial_conditions(self):
        """
        Apply initial conditions from config to feedwater components
        
        This method reads the initial_conditions from the FeedwaterConfig dataclass
        and applies them to the actual component states. This is critical for
        maintenance scenarios that start with pre-degraded conditions.
        
        Following DRY principles - applies parameters to single source of truth only.
        """
        ic = self.config.initial_conditions
        
        print(f"FEEDWATER: Applying initial conditions:")
        print(f"  System flow rate: {ic.total_flow_rate} kg/s")
        print(f"  System efficiency: {ic.system_efficiency}")
        print(f"  Pump oil levels: {ic.pump_oil_levels}")
        print(f"  Bearing temperatures: {ic.bearing_temperatures}")
        print(f"  Pump vibrations: {ic.pump_vibrations}")
        print(f"  Running pumps: {ic.running_pumps}")

        # Apply system-level initial conditions
        self.total_flow_rate = ic.total_flow_rate
        self.system_efficiency = ic.system_efficiency
        self.sg_levels = ic.sg_levels.copy()
        self.sg_pressures = ic.sg_pressures.copy()
        self.sg_steam_flows = ic.sg_steam_flows.copy()
        self.sg_steam_qualities = ic.sg_steam_qualities.copy()
        
        # Apply initial conditions to pump system
        if hasattr(self.pump_system, 'pumps'):
            pump_ids = list(self.pump_system.pumps.keys())
            
            for i, pump_id in enumerate(pump_ids):
                pump = self.pump_system.pumps[pump_id]
                
                print(f"  Applying initial conditions to pump {pump_id}:")
                
                # === APPLY TO LUBRICATION SYSTEM (SINGLE SOURCE OF TRUTH) ===
                if hasattr(pump, 'lubrication_system'):
                    print(f"    Applying lubrication system parameters:")
                    
                    # Oil quality parameters (system-wide, single values)
                    if hasattr(ic, 'pump_oil_contamination'):
                        pump.lubrication_system.oil_contamination_level = ic.pump_oil_contamination
                        print(f"      Oil contamination: {ic.pump_oil_contamination} ppm")
                    
                    if hasattr(ic, 'pump_oil_water_content'):
                        pump.lubrication_system.oil_moisture_content = ic.pump_oil_water_content
                        print(f"      Oil moisture: {ic.pump_oil_water_content}%")
                    
                    if hasattr(ic, 'pump_oil_acid_number'):
                        pump.lubrication_system.oil_acidity_number = ic.pump_oil_acid_number
                        print(f"      Oil acidity: {ic.pump_oil_acid_number} mg KOH/g")
                    
                    # Oil level and temperature (per-pump)
                    if i < len(ic.pump_oil_levels):
                        pump.lubrication_system.oil_level = ic.pump_oil_levels[i]
                        print(f"      Oil level: {ic.pump_oil_levels[i]}%")
                    
                    if hasattr(ic, 'oil_temperature'):
                        pump.lubrication_system.oil_temperature = ic.oil_temperature
                        print(f"      Oil temperature: {ic.oil_temperature}°C")
                    
                    # Component wear with additive approach
                    base_bearing_wear = ic.bearing_wear[i] * 100.0 if i < len(ic.bearing_wear) else 0.0
                    impeller_contribution = ic.impeller_wear[i] * 100.0 if (hasattr(ic, 'impeller_wear') and i < len(ic.impeller_wear)) else 0.0
                    seal_wear_value = ic.seal_face_wear[i] * 100.0 if (hasattr(ic, 'seal_face_wear') and i < len(ic.seal_face_wear)) else 0.0
                    
                    # Apply to lubrication system components
                    pump.lubrication_system.component_wear['motor_bearings'] = base_bearing_wear
                    pump.lubrication_system.component_wear['pump_bearings'] = base_bearing_wear + impeller_contribution
                    pump.lubrication_system.component_wear['thrust_bearing'] = base_bearing_wear
                    pump.lubrication_system.component_wear['mechanical_seals'] = seal_wear_value
                    
                    print(f"      Motor bearing wear: {base_bearing_wear:.1f}%")
                    print(f"      Pump bearing wear: {base_bearing_wear + impeller_contribution:.1f}% (bearing: {base_bearing_wear:.1f}% + impeller: {impeller_contribution:.1f}%)")
                    print(f"      Thrust bearing wear: {base_bearing_wear:.1f}%")
                    print(f"      Seal wear: {seal_wear_value:.1f}%")
                    
                    # Seal leakage (per-pump)
                    if hasattr(ic, 'seal_leakage_rate') and i < len(ic.seal_leakage_rate):
                        pump.lubrication_system.seal_leakage_rate = ic.seal_leakage_rate[i]
                        print(f"      Seal leakage: {ic.seal_leakage_rate[i]} L/min")
                    
                    # Recalculate performance factors after setting initial conditions
                    pump.lubrication_system._calculate_pump_performance_factors()
                    print(f"      Performance factors recalculated")
                
                # === APPLY HYDRAULIC CONDITIONS TO PUMP STATE ===
                # Hydraulic conditions (pump state only)
                if hasattr(ic, 'suction_pressure'):
                    pump.state.suction_pressure = ic.suction_pressure
                    print(f"    Suction pressure: {ic.suction_pressure} MPa")
                
                if hasattr(ic, 'discharge_pressure'):
                    pump.state.discharge_pressure = ic.discharge_pressure
                    print(f"    Discharge pressure: {ic.discharge_pressure} MPa")
                
                if hasattr(ic, 'npsh_available') and i < len(ic.npsh_available):
                    pump.state.npsh_available = ic.npsh_available[i]
                    print(f"    NPSH available: {ic.npsh_available[i]} m")
                
                # Cavitation conditions (pump hydraulic specific)
                if hasattr(ic, 'cavitation_intensity') and i < len(ic.cavitation_intensity):
                    pump.state.cavitation_intensity = ic.cavitation_intensity[i]
                    print(f"    Cavitation intensity: {ic.cavitation_intensity[i]}")
                
                if hasattr(ic, 'impeller_cavitation_damage') and i < len(ic.impeller_cavitation_damage):
                    pump.state.cavitation_damage = ic.impeller_cavitation_damage[i] * 10.0  # Scale to damage units
                    print(f"    Cavitation damage: {pump.state.cavitation_damage}")
                
                # Motor conditions (pump electrical specific)
                if hasattr(ic, 'motor_temperature') and i < len(ic.motor_temperature):
                    pump.state.motor_temperature = ic.motor_temperature[i]
                    print(f"    Motor temperature: {ic.motor_temperature[i]}°C")
                
                # Vibration (pump mechanical specific)
                if i < len(ic.pump_vibrations):
                    pump.state.vibration_level = ic.pump_vibrations[i]
                    print(f"    Vibration level: {ic.pump_vibrations[i]} mm/s")
                
                # === APPLY OPERATIONAL CONDITIONS ===
                # Apply running status and speed
                if i < len(ic.running_pumps):
                    from systems.primary.coolant.pump_models import PumpStatus
                    if ic.running_pumps[i]:
                        pump.state.status = PumpStatus.RUNNING
                        pump.state.available = True
                        if i < len(ic.pump_speeds):
                            pump.state.speed_percent = ic.pump_speeds[i]
                        else:
                            pump.state.speed_percent = 100.0
                        print(f"    Status: RUNNING at {pump.state.speed_percent}%")
                    else:
                        pump.state.status = PumpStatus.STOPPED
                        pump.state.speed_percent = 0.0
                        print(f"    Status: STOPPED")
                
                # Apply flow conditions
                if i < len(ic.pump_flows):
                    pump.state.flow_rate = ic.pump_flows[i]
                    print(f"    Flow rate: {ic.pump_flows[i]} kg/s")
                
                # Apply power conditions
                if hasattr(ic, 'pump_power') and i < len(ic.pump_power):
                    # pump_power is a fraction, convert to actual power
                    design_power = pump.config.rated_power if hasattr(pump.config, 'rated_power') else 10.0
                    pump.state.power_consumption = ic.pump_power[i] * design_power
                    print(f"    Power consumption: {pump.state.power_consumption} MW")
                
                # NO SYNC NEEDED - unidirectional flow from lubrication system to pump state
                # The integration function handles this automatically
        
        # === APPLY SYSTEM-LEVEL CONDITIONS ===
        # Apply system-wide parameters to main feedwater physics state
        if hasattr(ic, 'lubrication_system_pressure'):
            # FIXED: Handle single value (system-wide parameter)
            self.lubrication_system_pressure = ic.lubrication_system_pressure
            print(f"  System lubrication pressure: {ic.lubrication_system_pressure} MPa")
        
        if hasattr(ic, 'cooling_water_temperature') and ic.cooling_water_temperature:
            # Apply average cooling water temperature
            avg_cooling_temp = sum(ic.cooling_water_temperature) / len(ic.cooling_water_temperature)
            self.cooling_water_temperature = avg_cooling_temp
            print(f"  System cooling water temp: {avg_cooling_temp}°C")
        
        # Apply control system initial conditions
        self.control_mode = ic.control_mode
        if hasattr(ic, 'level_setpoint'):
            self.config.design_sg_level = ic.level_setpoint
        
        # Apply water quality initial conditions
        if self.water_quality is not None:
            if hasattr(ic, 'feedwater_ph'):
                self.water_quality.ph = ic.feedwater_ph
            if hasattr(ic, 'dissolved_oxygen'):
                self.water_quality.dissolved_oxygen = ic.dissolved_oxygen
            if hasattr(ic, 'iron_concentration'):
                self.water_quality.iron_concentration = ic.iron_concentration
            if hasattr(ic, 'copper_concentration'):
                self.water_quality.copper_concentration = ic.copper_concentration
        
        # === APPLY CONDITIONS TO SUBSYSTEMS ===
        # Apply initial conditions to diagnostics system
        if hasattr(self.diagnostics, 'cavitation_model'):
            # Apply cavitation parameters to diagnostics
            if hasattr(ic, 'cavitation_intensity'):
                avg_cavitation = sum(ic.cavitation_intensity) / len(ic.cavitation_intensity)
                self.diagnostics.cavitation_model.current_intensity = avg_cavitation
            
            if hasattr(ic, 'impeller_cavitation_damage'):
                avg_damage = sum(ic.impeller_cavitation_damage) / len(ic.impeller_cavitation_damage)
                self.diagnostics.cavitation_model.accumulated_damage = avg_damage * 10.0  # Scale to damage units
        
        if hasattr(self.diagnostics, 'wear_tracking'):
            # Apply wear parameters to diagnostics
            if hasattr(ic, 'impeller_wear'):
                avg_impeller_wear = sum(ic.impeller_wear) / len(ic.impeller_wear)
                self.diagnostics.wear_tracking.impeller_wear = avg_impeller_wear * 100.0  # Convert to percentage
            
            if hasattr(ic, 'bearing_wear'):
                avg_bearing_wear = sum(ic.bearing_wear) / len(ic.bearing_wear)
                self.diagnostics.wear_tracking.bearing_wear = avg_bearing_wear * 100.0  # Convert to percentage
            
            if hasattr(ic, 'seal_face_wear'):
                avg_seal_wear = sum(ic.seal_face_wear) / len(ic.seal_face_wear)
                self.diagnostics.wear_tracking.seal_wear = avg_seal_wear * 100.0  # Convert to percentage
        
        print(f"FEEDWATER: Initial conditions applied successfully")
        print(f"  Applied parameters to pump states, lubrication systems, and diagnostics")
        
        # Validate that critical initial conditions were applied
        self._validate_initial_conditions_applied()
    
    def _validate_initial_conditions_applied(self):
        """
        Validate that initial conditions were properly applied to the new DRY architecture
        
        This method validates that parameters were applied to the correct systems:
        - Lubrication system: oil quality, component wear, performance factors
        - Pump state: hydraulic conditions, operational status
        - System-wide: lubrication pressure, cooling water temperature
        """
        ic = self.config.initial_conditions
        
        print(f"FEEDWATER: Validating initial conditions application:")
        
        validation_errors = []
        validation_successes = []
        
        if hasattr(self.pump_system, 'pumps'):
            pump_ids = list(self.pump_system.pumps.keys())
            for i, pump_id in enumerate(pump_ids):
                pump = self.pump_system.pumps[pump_id]
                
                # === VALIDATE LUBRICATION SYSTEM PARAMETERS ===
                if hasattr(pump, 'lubrication_system'):
                    
                    # Validate oil quality parameters (system-wide)
                    if hasattr(ic, 'pump_oil_contamination'):
                        expected = ic.pump_oil_contamination
                        actual = pump.lubrication_system.oil_contamination_level
                        if abs(actual - expected) > 0.1:
                            validation_errors.append(f"Pump {pump_id} oil contamination mismatch: expected {expected} ppm, got {actual} ppm")
                        else:
                            validation_successes.append(f"Pump {pump_id} oil contamination: {actual} ppm")
                    
                    if hasattr(ic, 'pump_oil_water_content'):
                        expected = ic.pump_oil_water_content
                        actual = pump.lubrication_system.oil_moisture_content
                        if abs(actual - expected) > 0.01:
                            validation_errors.append(f"Pump {pump_id} oil moisture mismatch: expected {expected}%, got {actual}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} oil moisture: {actual}%")
                    
                    if hasattr(ic, 'pump_oil_acid_number'):
                        expected = ic.pump_oil_acid_number
                        actual = pump.lubrication_system.oil_acidity_number
                        if abs(actual - expected) > 0.1:
                            validation_errors.append(f"Pump {pump_id} oil acidity mismatch: expected {expected} mg KOH/g, got {actual} mg KOH/g")
                        else:
                            validation_successes.append(f"Pump {pump_id} oil acidity: {actual} mg KOH/g")
                    
                    # Validate oil level (per-pump)
                    if i < len(ic.pump_oil_levels):
                        expected = ic.pump_oil_levels[i]
                        actual = pump.lubrication_system.oil_level
                        if abs(actual - expected) > 0.1:
                            validation_errors.append(f"Pump {pump_id} oil level mismatch: expected {expected}%, got {actual}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} oil level: {actual}%")
                    
                    # Validate component wear with additive approach
                    if i < len(ic.bearing_wear) and hasattr(ic, 'impeller_wear') and i < len(ic.impeller_wear):
                        expected_motor_bearing = ic.bearing_wear[i] * 100.0
                        expected_pump_bearing = (ic.bearing_wear[i] + ic.impeller_wear[i]) * 100.0
                        expected_thrust_bearing = ic.bearing_wear[i] * 100.0
                        
                        actual_motor_bearing = pump.lubrication_system.component_wear.get('motor_bearings', 0.0)
                        actual_pump_bearing = pump.lubrication_system.component_wear.get('pump_bearings', 0.0)
                        actual_thrust_bearing = pump.lubrication_system.component_wear.get('thrust_bearing', 0.0)
                        
                        if abs(actual_motor_bearing - expected_motor_bearing) > 0.1:
                            validation_errors.append(f"Pump {pump_id} motor bearing wear mismatch: expected {expected_motor_bearing:.1f}%, got {actual_motor_bearing:.1f}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} motor bearing wear: {actual_motor_bearing:.1f}%")
                        
                        if abs(actual_pump_bearing - expected_pump_bearing) > 0.1:
                            validation_errors.append(f"Pump {pump_id} pump bearing wear mismatch: expected {expected_pump_bearing:.1f}%, got {actual_pump_bearing:.1f}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} pump bearing wear: {actual_pump_bearing:.1f}% (additive: {ic.bearing_wear[i]*100:.1f}% + {ic.impeller_wear[i]*100:.1f}%)")
                        
                        if abs(actual_thrust_bearing - expected_thrust_bearing) > 0.1:
                            validation_errors.append(f"Pump {pump_id} thrust bearing wear mismatch: expected {expected_thrust_bearing:.1f}%, got {actual_thrust_bearing:.1f}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} thrust bearing wear: {actual_thrust_bearing:.1f}%")
                    
                    # Validate seal wear
                    if hasattr(ic, 'seal_face_wear') and i < len(ic.seal_face_wear):
                        expected_seal_wear = ic.seal_face_wear[i] * 100.0
                        actual_seal_wear = pump.lubrication_system.component_wear.get('mechanical_seals', 0.0)
                        if abs(actual_seal_wear - expected_seal_wear) > 0.1:
                            validation_errors.append(f"Pump {pump_id} seal wear mismatch: expected {expected_seal_wear:.1f}%, got {actual_seal_wear:.1f}%")
                        else:
                            validation_successes.append(f"Pump {pump_id} seal wear: {actual_seal_wear:.1f}%")
                    
                    # Validate performance factors were recalculated
                    efficiency_factor = pump.lubrication_system.pump_efficiency_factor
                    flow_factor = pump.lubrication_system.pump_flow_factor
                    head_factor = pump.lubrication_system.pump_head_factor
                    
                    if not (0.5 <= efficiency_factor <= 1.0):
                        validation_errors.append(f"Pump {pump_id} invalid efficiency factor: {efficiency_factor}")
                    else:
                        validation_successes.append(f"Pump {pump_id} efficiency factor: {efficiency_factor:.3f}")
                    
                    if not (0.5 <= flow_factor <= 1.0):
                        validation_errors.append(f"Pump {pump_id} invalid flow factor: {flow_factor}")
                    else:
                        validation_successes.append(f"Pump {pump_id} flow factor: {flow_factor:.3f}")
                    
                    if not (0.5 <= head_factor <= 1.0):
                        validation_errors.append(f"Pump {pump_id} invalid head factor: {head_factor}")
                    else:
                        validation_successes.append(f"Pump {pump_id} head factor: {head_factor:.3f}")
                
                else:
                    validation_errors.append(f"Pump {pump_id} missing lubrication system integration")
                
                # === VALIDATE PUMP STATE (HYDRAULIC PARAMETERS ONLY) ===
                
                # Validate hydraulic conditions
                if hasattr(ic, 'suction_pressure'):
                    expected = ic.suction_pressure
                    actual = pump.state.suction_pressure
                    if abs(actual - expected) > 0.01:
                        validation_errors.append(f"Pump {pump_id} suction pressure mismatch: expected {expected} MPa, got {actual} MPa")
                    else:
                        validation_successes.append(f"Pump {pump_id} suction pressure: {actual} MPa")
                
                if hasattr(ic, 'discharge_pressure'):
                    expected = ic.discharge_pressure
                    actual = pump.state.discharge_pressure
                    if abs(actual - expected) > 0.01:
                        validation_errors.append(f"Pump {pump_id} discharge pressure mismatch: expected {expected} MPa, got {actual} MPa")
                    else:
                        validation_successes.append(f"Pump {pump_id} discharge pressure: {actual} MPa")
                
                # Validate vibration (pump mechanical specific)
                if i < len(ic.pump_vibrations):
                    expected = ic.pump_vibrations[i]
                    actual = pump.state.vibration_level
                    if abs(actual - expected) > 0.1:
                        validation_errors.append(f"Pump {pump_id} vibration mismatch: expected {expected} mm/s, got {actual} mm/s")
                    else:
                        validation_successes.append(f"Pump {pump_id} vibration: {actual} mm/s")
                
                # Validate cavitation conditions
                if hasattr(ic, 'cavitation_intensity') and i < len(ic.cavitation_intensity):
                    expected = ic.cavitation_intensity[i]
                    actual = pump.state.cavitation_intensity
                    if abs(actual - expected) > 0.01:
                        validation_errors.append(f"Pump {pump_id} cavitation intensity mismatch: expected {expected}, got {actual}")
                    else:
                        validation_successes.append(f"Pump {pump_id} cavitation intensity: {actual}")
                
                # === VALIDATE OPERATIONAL CONDITIONS ===
                
                # Validate running status
                if i < len(ic.running_pumps):
                    expected_running = ic.running_pumps[i]
                    from systems.primary.coolant.pump_models import PumpStatus
                    actual_running = (pump.state.status == PumpStatus.RUNNING)
                    if expected_running != actual_running:
                        validation_errors.append(f"Pump {pump_id} running status mismatch: expected {expected_running}, got {actual_running}")
                    else:
                        validation_successes.append(f"Pump {pump_id} running status: {actual_running}")
                
                # Validate flow rate
                if i < len(ic.pump_flows):
                    expected = ic.pump_flows[i]
                    actual = pump.state.flow_rate
                    if abs(actual - expected) > 1.0:  # Allow 1 kg/s tolerance
                        validation_errors.append(f"Pump {pump_id} flow rate mismatch: expected {expected} kg/s, got {actual} kg/s")
                    else:
                        validation_successes.append(f"Pump {pump_id} flow rate: {actual} kg/s")
        
        # === VALIDATE SYSTEM-WIDE PARAMETERS ===
        
        # Validate system lubrication pressure
        if hasattr(ic, 'lubrication_system_pressure'):
            if hasattr(self, 'lubrication_system_pressure'):
                expected = ic.lubrication_system_pressure
                actual = self.lubrication_system_pressure
                if abs(actual - expected) > 0.01:
                    validation_errors.append(f"System lubrication pressure mismatch: expected {expected} MPa, got {actual} MPa")
                else:
                    validation_successes.append(f"System lubrication pressure: {actual} MPa")
        
        # Validate system cooling water temperature
        if hasattr(ic, 'cooling_water_temperature') and ic.cooling_water_temperature:
            if hasattr(self, 'cooling_water_temperature'):
                expected_avg = sum(ic.cooling_water_temperature) / len(ic.cooling_water_temperature)
                actual = self.cooling_water_temperature
                if abs(actual - expected_avg) > 1.0:
                    validation_errors.append(f"System cooling water temp mismatch: expected {expected_avg}°C, got {actual}°C")
                else:
                    validation_successes.append(f"System cooling water temp: {actual}°C")
        
        # === PRINT VALIDATION RESULTS ===
        
        print(f"  Validation Results:")
        print(f"    ✓ Successful validations: {len(validation_successes)}")
        print(f"    ⚠ Validation errors: {len(validation_errors)}")
        
        if validation_errors:
            print(f"  Validation Errors:")
            for error in validation_errors[:5]:  # Show first 5 errors
                print(f"    ⚠ {error}")
            if len(validation_errors) > 5:
                print(f"    ... and {len(validation_errors) - 5} more errors")
        
        if validation_successes:
            print(f"  Sample Successful Validations:")
            for success in validation_successes[:3]:  # Show first 3 successes
                print(f"    ✓ {success}")
            if len(validation_successes) > 3:
                print(f"    ... and {len(validation_successes) - 3} more successful validations")
        
        print(f"FEEDWATER: Initial conditions validation complete")
        
        # Return validation status for testing
        return len(validation_errors) == 0
        
    def update_state(self,
                    sg_conditions: Dict[str, List[float]],
                    steam_generator_demands: Dict[str, float],
                    system_conditions: Dict[str, float],
                    control_inputs: Dict[str, float] = None,
                    dt: float = 1.0) -> Dict[str, float]:
        """
        Update enhanced feedwater state for one time step
        
        Args:
            sg_conditions: Steam generator conditions (levels, pressures, flows, qualities)
            steam_generator_demands: Steam demands from each SG
            system_conditions: Overall system conditions (temperatures, pressures)
            control_inputs: Control system inputs
            dt: Time step (hours)
            
        Returns:
            Dictionary with enhanced feedwater performance results
        """
        if control_inputs is None:
            control_inputs = {}
        
        # Extract steam generator conditions
        self.sg_levels = sg_conditions.get('levels', self.sg_levels)
        self.sg_pressures = sg_conditions.get('pressures', self.sg_pressures)
        self.sg_steam_flows = sg_conditions.get('steam_flows', self.sg_steam_flows)
        self.sg_steam_qualities = sg_conditions.get('steam_qualities', self.sg_steam_qualities)
        
        # Update water quality model
        makeup_water_quality = system_conditions.get('makeup_water_quality', {
            'tds': 300.0,
            'hardness': 100.0,
            'chloride': 30.0,
            'ph': 7.2,
            'dissolved_oxygen': 8.0
        })
        
        chemical_doses = system_conditions.get('chemical_doses', {
            'chlorine': 0.5,
            'antiscalant': 5.0,
            'corrosion_inhibitor': 10.0,
            'biocide': 0.0
        })
        
        # Use unified water chemistry system if available, otherwise use defaults
        if self.water_quality is not None:
            water_quality_results = self.water_quality.update_chemistry(
                system_conditions={
                    'makeup_water_quality': makeup_water_quality,
                    'blowdown_rate': 0.02  # 2% blowdown rate
                },
                dt=dt
            )
        else:
            # Default water quality results when unified system is not available
            water_quality_results = {
                'water_chemistry_ph': 9.2,
                'water_chemistry_hardness': 100.0,
                'water_chemistry_tds': 300.0,
                'water_chemistry_aggressiveness': 1.0,
                'water_chemistry_treatment_efficiency': 0.95
            }
        
        # Update three-element control system
        if self.config.auto_level_control:
            control_demands = self.level_control.calculate_flow_demands(
                sg_levels=self.sg_levels,
                sg_steam_flows=self.sg_steam_flows,
                sg_steam_qualities=self.sg_steam_qualities,
                target_levels=[self.config.design_sg_level] * self.config.num_steam_generators,
                load_demand=self.load_demand,
                dt=dt
            )
        else:
            # Manual control mode
            manual_flow = steam_generator_demands.get('total_flow', self.config.design_total_flow)
            control_demands = {
                'total_flow_demand': manual_flow,
                'individual_demands': [manual_flow / self.config.num_steam_generators] * self.config.num_steam_generators
            }
        
        # Prepare system conditions for pump system
        pump_system_conditions = {
            'feedwater_temperature': system_conditions.get('feedwater_temperature', self.config.design_feedwater_temperature),
            'suction_pressure': system_conditions.get('suction_pressure', 0.5),
            'discharge_pressure': system_conditions.get('discharge_pressure', self.config.design_pressure),
            'sg_levels': self.sg_levels,
            'sg_pressures': self.sg_pressures,
            'water_quality': water_quality_results
        }
        
        # Update pump system with control demands
        pump_control_inputs = control_inputs.copy()
        pump_control_inputs.update({
            'flow_demand': control_demands['total_flow_demand'],
            'individual_demands': control_demands['individual_demands']
        })
        
        # Use dt directly - pump system should handle the same time units as the calling system
        pump_results = self.pump_system.update_system(
            dt=dt,
            system_conditions=pump_system_conditions,
            control_inputs=pump_control_inputs
        )
        
        # Update performance diagnostics
        diagnostics_results = self.diagnostics.update_diagnostics(
            pump_results=pump_results.get('pump_details', {}),
            water_quality_results=water_quality_results,
            system_conditions=pump_system_conditions,
            dt=dt
        )
        
        # Update protection system
        protection_results = self.protection_system.check_protection_systems(
            pump_results=pump_results.get('pump_details', {}),
            diagnostics_results=diagnostics_results,
            system_conditions=pump_system_conditions,
            dt=dt
        )
        
        # Update system state
        self.total_flow_rate = pump_results['total_flow_rate']
        self.total_power_consumption = pump_results['total_power_consumption']
        self.system_availability = pump_results['system_available'] and not protection_results['system_trip_active']
        
        # Calculate system efficiency
        if self.total_power_consumption > 0:
            # Hydraulic power = flow * head * density * gravity
            hydraulic_power = (self.total_flow_rate * 
                             (self.config.design_pressure - pump_system_conditions['suction_pressure']) * 1e6 * 
                             1000 * 9.81) / 1e6  # Convert to MW
            self.system_efficiency = hydraulic_power / self.total_power_consumption
        else:
            self.system_efficiency = 0.0
        
        # Calculate performance factors
        pump_performance = pump_results.get('average_performance_factor', 1.0)
        water_quality_factor = 1.0 - water_quality_results.get('water_chemistry_aggressiveness', 0.0) * 0.1
        diagnostics_factor = diagnostics_results.get('overall_health_factor', 1.0)
        
        self.performance_factor = pump_performance * water_quality_factor * diagnostics_factor
        self.maintenance_factor = diagnostics_results.get('maintenance_effectiveness', 1.0)
        
        # Update operating hours
        self.operating_hours += dt / 60
        
        return {
            # Overall system performance
            'total_flow_rate': self.total_flow_rate,
            'total_power_consumption': self.total_power_consumption,
            'system_efficiency': self.system_efficiency,
            'system_availability': self.system_availability,
            'performance_factor': self.performance_factor,
            'maintenance_factor': self.maintenance_factor,
            
            # Steam generator distribution
            'sg_flow_distribution': pump_results.get('sg_flow_distribution', {}),
            'sg_levels': self.sg_levels,
            'sg_level_errors': control_demands.get('level_errors', [0.0] * self.config.num_steam_generators),
            
            # Pump system results
            'running_pumps': pump_results['running_pumps'],
            'num_running_pumps': pump_results['num_running_pumps'],
            'pump_details': pump_results['pump_details'],
            'average_pump_speed': pump_results.get('average_pump_speed', 0.0),
            'average_pump_efficiency': pump_results.get('average_pump_efficiency', 0.0),
            
            # Control system results
            'control_mode': self.control_mode,
            'auto_control_active': self.config.auto_level_control,
            'total_flow_demand': control_demands['total_flow_demand'],
            'flow_demand_error': control_demands['total_flow_demand'] - self.total_flow_rate,
            
            # Water quality results - using unified water chemistry system
            'water_ph': water_quality_results['water_chemistry_ph'],
            'water_hardness': water_quality_results['water_chemistry_hardness'],
            'water_tds': water_quality_results['water_chemistry_tds'],
            'water_aggressiveness': water_quality_results['water_chemistry_aggressiveness'],
            'chemical_treatment_efficiency': water_quality_results['water_chemistry_treatment_efficiency'],
            
            # Performance diagnostics
            'cavitation_risk': diagnostics_results.get('overall_cavitation_risk', 0.0),
            'wear_level': diagnostics_results.get('overall_wear_level', 0.0),
            'vibration_level': diagnostics_results.get('overall_vibration_level', 0.0),
            'thermal_stress': diagnostics_results.get('overall_thermal_stress', 0.0),
            'maintenance_recommendation': diagnostics_results.get('maintenance_recommendation', 'Normal'),
            
            # Protection system
            'protection_active': protection_results['system_trip_active'],
            'active_trips': protection_results.get('active_trips', []),
            'protection_warnings': protection_results.get('warnings', []),
            'emergency_actions': protection_results.get('emergency_actions', {}),
            
            # Operating conditions
            'load_demand': self.load_demand,
            'operating_hours': self.operating_hours,
            'feedwater_temperature': pump_system_conditions['feedwater_temperature'],
            'system_pressure': pump_system_conditions['discharge_pressure']
        }
    
    def set_control_mode(self, mode: str) -> bool:
        """
        Set feedwater system control mode
        
        Args:
            mode: Control mode ('automatic', 'manual', 'emergency')
            
        Returns:
            Success status
        """
        valid_modes = ['automatic', 'manual', 'emergency']
        if mode in valid_modes:
            self.control_mode = mode
            if mode == 'automatic':
                self.config.auto_level_control = True
            elif mode == 'manual':
                self.config.auto_level_control = False
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
    
    def setup_maintenance_integration(self, maintenance_system):
        """
        Set up maintenance integration for the entire feedwater system
        
        Args:
            maintenance_system: AutoMaintenanceSystem instance
        """
        from systems.maintenance import AutoMaintenanceSystem
        
        print(f"FEEDWATER SYSTEM: Setting up maintenance integration")
        
        # Set up pump system maintenance integration (primary integration point)
        self.pump_system.setup_maintenance_integration(maintenance_system)
        
        # Connect protection system to maintenance event bus for trip events
        self.protection_system.set_maintenance_event_bus(
            maintenance_system.event_bus, 
            "FEEDWATER_SYSTEM"
        )
        print(f"  Connected feedwater protection system to maintenance event bus")
        
        # Register protection system for maintenance monitoring
        protection_monitoring_config = {
            'system_trip_active': {
                'attribute': 'system_trip_active',
                'threshold': 0.5,
                'comparison': 'greater_than',
                'action': 'protection_system_test',
                'cooldown_hours': 24.0
            },
            'false_trip_count': {
                'attribute': 'false_trip_count',
                'threshold': 3.0,
                'comparison': 'greater_than',
                'action': 'protection_system_calibration',
                'cooldown_hours': 168.0  # Weekly
            }
        }
        
        maintenance_system.register_component("feedwater_protection", self.protection_system, protection_monitoring_config)
        print(f"  Registered feedwater protection system for maintenance monitoring")
        
        # Register diagnostics system for health monitoring
        diagnostics_monitoring_config = {
            'overall_health_score': {
                'attribute': 'overall_health_score',
                'threshold': 0.7,
                'comparison': 'less_than',
                'action': 'system_cleaning',
                'cooldown_hours': 72.0  # 3 days
            },
            'maintenance_urgency': {
                'attribute': 'maintenance_urgency',
                'threshold': 0.8,
                'comparison': 'greater_than',
                'action': 'routine_maintenance',
                'cooldown_hours': 24.0
            }
        }
        
        maintenance_system.register_component("feedwater_diagnostics", self.diagnostics, diagnostics_monitoring_config)
        print(f"  Registered feedwater diagnostics system for maintenance monitoring")
        
        # Store reference for coordination
        self.maintenance_system = maintenance_system
        
        # Subscribe to system-level maintenance events
        maintenance_system.event_bus.subscribe('maintenance_completed', self._handle_maintenance_completed)
        
        print(f"FEEDWATER SYSTEM: Maintenance integration complete")
    
    def _handle_maintenance_completed(self, event):
        """Handle maintenance completion events to update system performance"""
        component_id = event.component_id
        maintenance_data = event.data
        
        # Update maintenance factor based on completed maintenance
        if maintenance_data.get('success', False):
            effectiveness = maintenance_data.get('effectiveness_score', 0.8)
            self.maintenance_factor = min(1.0, self.maintenance_factor + effectiveness * 0.1)
            
            print(f"FEEDWATER SYSTEM: Maintenance completed on {component_id}, "
                  f"system maintenance factor: {self.maintenance_factor:.3f}")
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Enhanced maintenance operations on feedwater systems
        
        Args:
            maintenance_type: Type of maintenance
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results compatible with MaintenanceResult
        """
        results = {}
        
        if maintenance_type == "pump_maintenance":
            # Perform pump maintenance through pump system
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="general", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "oil_change":
            # Oil change on specific pump or all pumps
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="oil_change", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "oil_top_off":
            # Oil top-off on specific pump or all pumps
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="oil_top_off", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "impeller_inspection":
            # Impeller inspection
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="impeller_inspection", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "bearing_replacement":
            # Bearing replacement
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="bearing_replacement", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "seal_replacement":
            # Seal replacement
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="seal_replacement", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "vibration_analysis":
            # Vibration analysis
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="vibration_analysis", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "component_overhaul":
            # Component overhaul
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="component_overhaul", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "routine_maintenance":
            # Routine maintenance
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, maintenance_type="routine_maintenance", **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "water_treatment":
            # Reset water treatment system
            if hasattr(self.water_quality, 'perform_treatment_maintenance'):
                treatment_results = self.water_quality.perform_treatment_maintenance(**kwargs)
                results.update(treatment_results)
            else:
                # Basic water treatment maintenance
                self.water_quality.reset()
                results['water_treatment'] = {
                    'success': True,
                    'duration_hours': 4.0,
                    'work_performed': 'Water treatment system maintenance',
                    'effectiveness_score': 0.9
                }
            
        elif maintenance_type == "control_calibration":
            # Calibrate control system
            if hasattr(self.level_control, 'perform_calibration'):
                calibration_results = self.level_control.perform_calibration(**kwargs)
                results.update(calibration_results)
            else:
                # Basic control calibration
                results['control_calibration'] = {
                    'success': True,
                    'duration_hours': 2.0,
                    'work_performed': 'Control system calibration',
                    'effectiveness_score': 0.95
                }
            
        elif maintenance_type == "system_cleaning":
            # Perform system cleaning
            cleaning_results = self.diagnostics.perform_system_cleaning(**kwargs)
            results.update(cleaning_results)
            
        elif maintenance_type == "protection_system_test":
            # Test protection system
            test_results = self.protection_system.perform_protection_test()
            results['protection_test'] = {
                'success': test_results.get('overall_test_passed', True),
                'duration_hours': 1.0,
                'work_performed': 'Protection system test',
                'findings': f"Test results: {test_results}",
                'effectiveness_score': 1.0 if test_results.get('overall_test_passed', True) else 0.5
            }
            
        elif maintenance_type == "protection_system_calibration":
            # Calibrate protection system
            self.protection_system.reset_protection_system()
            results['protection_calibration'] = {
                'success': True,
                'duration_hours': 4.0,
                'work_performed': 'Protection system calibration',
                'findings': 'Protection system reset and calibrated',
                'effectiveness_score': 1.0
            }
        
        # Update maintenance factor
        if results:
            avg_effectiveness = sum(r.get('effectiveness_score', 0.8) for r in results.values() if isinstance(r, dict)) / max(1, len(results))
            self.maintenance_factor = min(1.0, self.maintenance_factor + avg_effectiveness * 0.05)
        
        # Return compatible format for automatic maintenance system
        if len(results) == 1:
            # Single maintenance action - return the result directly
            return list(results.values())[0]
        else:
            # Multiple maintenance actions - return summary
            all_successful = all(r.get('success', True) for r in results.values() if isinstance(r, dict))
            total_duration = sum(r.get('duration_hours', 1.0) for r in results.values() if isinstance(r, dict))
            
            return {
                'success': all_successful,
                'duration_hours': total_duration,
                'work_performed': f"Performed {maintenance_type} on feedwater system",
                'findings': f"Completed {len(results)} maintenance actions",
                'effectiveness_score': 1.0 if all_successful else 0.7
            }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            # Basic feedwater state
            'feedwater_total_flow': self.total_flow_rate,
            'feedwater_total_power': self.total_power_consumption,
            'feedwater_system_efficiency': self.system_efficiency,
            'feedwater_system_availability': float(self.system_availability),
            'feedwater_performance_factor': self.performance_factor,
            'feedwater_operating_hours': self.operating_hours,
            'feedwater_load_demand': self.load_demand,
            
            # Steam generator conditions
            'feedwater_avg_sg_level': np.mean(self.sg_levels),
            'feedwater_avg_sg_pressure': np.mean(self.sg_pressures),
            'feedwater_total_steam_flow': sum(self.sg_steam_flows),
            'feedwater_avg_steam_quality': np.mean(self.sg_steam_qualities)
        }
        
        # Add subsystem states
        state_dict.update(self.level_control.get_state_dict())
        if self.water_quality is not None:
            state_dict.update(self.water_quality.get_state_dict())
        state_dict.update(self.diagnostics.get_state_dict())
        state_dict.update(self.protection_system.get_state_dict())
        
        return state_dict 
    
    def get_heat_flows(self) -> Dict[str, float]:
        """
        Get current heat flows for this component (MW)
        
        Returns:
            Dictionary with heat flow values in MW
        """
        # Calculate feedwater enthalpy flows
        feedwater_temp = self.config.design_feedwater_temperature
        feedwater_enthalpy = ThermodynamicProperties.liquid_enthalpy(feedwater_temp)
        
        # Input: Condensate from condenser (lower temperature)
        condensate_temp = 39.0  # Typical condenser outlet temperature
        condensate_enthalpy = ThermodynamicProperties.liquid_enthalpy(condensate_temp)
        condensate_enthalpy_input = ThermodynamicProperties.enthalpy_flow_mw(self.total_flow_rate, condensate_enthalpy)
        
        # Output: Heated feedwater to steam generators
        feedwater_enthalpy_output = ThermodynamicProperties.enthalpy_flow_mw(self.total_flow_rate, feedwater_enthalpy)
        
        # Pump work input (mechanical energy converted to fluid energy)
        pump_work_input = self.total_power_consumption  # MW
        
        # Extraction heating from turbine extractions
        extraction_heating = feedwater_enthalpy_output - condensate_enthalpy_input - pump_work_input
        extraction_heating = max(0.0, extraction_heating)  # Ensure positive
        
        # Get heat flow contributions from lubrication system with temperature integration
        if hasattr(self.pump_system, 'pumps'):
            total_lube_heat_flows = {'mechanical_losses_mw': 0.0, 'motor_heat_to_feedwater_mw': 0.0}
            
            for pump in self.pump_system.pumps.values():
                if hasattr(pump, 'lubrication_system'):
                    pump_work = pump.state.power_consumption  # MW for this pump
                    lube_heat_flows = pump.lubrication_system.calculate_heat_flow_contributions(
                        pump_work, feedwater_temp
                    )
                    total_lube_heat_flows['mechanical_losses_mw'] += lube_heat_flows['mechanical_losses_mw']
                    total_lube_heat_flows['motor_heat_to_feedwater_mw'] += lube_heat_flows['motor_heat_to_feedwater_mw']
            
            # Use calculated losses instead of fixed 2%
            internal_losses = total_lube_heat_flows['mechanical_losses_mw']
            motor_heat_to_feedwater = total_lube_heat_flows['motor_heat_to_feedwater_mw']
        else:
            # Fallback to fixed losses if lubrication system not available
            internal_losses = pump_work_input * 0.02
            motor_heat_to_feedwater = 0.0
        
        return {
            'condensate_enthalpy_input': condensate_enthalpy_input,
            'feedwater_enthalpy_output': feedwater_enthalpy_output,
            'pump_work_input': pump_work_input,
            'extraction_heating': extraction_heating,
            'internal_losses': internal_losses
        }
    
    def get_enthalpy_flows(self) -> Dict[str, float]:
        """
        Get current enthalpy flows for this component (MW)
        
        Returns:
            Dictionary with enthalpy flow values in MW
        """
        heat_flows = self.get_heat_flows()
        
        return {
            'inlet_enthalpy_flow': heat_flows['condensate_enthalpy_input'],
            'outlet_enthalpy_flow': heat_flows['feedwater_enthalpy_output'],
            'enthalpy_added': heat_flows['feedwater_enthalpy_output'] - heat_flows['condensate_enthalpy_input'],
            'work_input': heat_flows['pump_work_input'],
            'extraction_heating': heat_flows['extraction_heating']
        }
    
    def get_chemistry_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get chemistry flows for chemistry flow tracker integration
        
        Returns:
            Dictionary with chemistry flow data
        """
        # Get water chemistry flows from the integrated water quality system
        water_chemistry_flows = self.water_quality.get_chemistry_flows()
        
        # Add feedwater-specific chemistry flows
        feedwater_flows = {
            'feedwater_chemistry': {
                ChemicalSpecies.PH.value: self.water_quality.ph,
                ChemicalSpecies.IRON.value: self.water_quality.iron_concentration,
                ChemicalSpecies.COPPER.value: self.water_quality.copper_concentration,
                ChemicalSpecies.HARDNESS.value: self.water_quality.hardness,
                ChemicalSpecies.CHLORIDE.value: self.water_quality.chloride,
                ChemicalSpecies.TDS.value: self.water_quality.total_dissolved_solids,
                ChemicalSpecies.ANTISCALANT.value: self.water_quality.antiscalant_concentration,
                ChemicalSpecies.CORROSION_INHIBITOR.value: self.water_quality.corrosion_inhibitor_level
            }
        }
        
        # Combine flows
        combined_flows = {}
        combined_flows.update(water_chemistry_flows)
        combined_flows.update(feedwater_flows)
        
        return combined_flows
    
    def get_chemistry_state(self) -> Dict[str, float]:
        """
        Get current chemistry state for chemistry flow tracker
        
        Returns:
            Dictionary with current chemistry concentrations
        """
        return self.water_quality.get_chemistry_state()
    
    def update_chemistry_effects(self, chemistry_state: Dict[str, float]) -> None:
        """
        Update feedwater system based on chemistry state feedback
        
        Args:
            chemistry_state: Chemistry state from external systems
        """
        # Pass chemistry effects to the water quality system
        self.water_quality.update_chemistry_effects(chemistry_state)
        
        # Apply chemistry effects to pump performance if needed
        if 'water_aggressiveness' in chemistry_state:
            aggressiveness = chemistry_state['water_aggressiveness']
            # Reduce performance factor based on water aggressiveness
            chemistry_performance_factor = max(0.5, 1.0 - (aggressiveness - 1.0) * 0.1)
            self.performance_factor *= chemistry_performance_factor
    
    def reset(self) -> None:
        """Reset enhanced feedwater system to initial conditions"""
        # CRITICAL FIX: Store initial conditions before reset to preserve them
        ic = self.config.initial_conditions
        
        # Reset subsystems
        self.pump_system.reset()
        self.level_control.reset()
        if self.water_quality is not None:
            self.water_quality.reset()
        self.diagnostics.reset()
        self.protection_system.reset()
        
        # Reset main state
        self.total_flow_rate = 0.0
        self.total_power_consumption = 0.0
        self.system_efficiency = 0.0
        self.system_availability = True
        
        # Reset SG conditions to design values
        self.sg_levels = [self.config.design_sg_level] * self.config.num_steam_generators
        self.sg_pressures = [6.895] * self.config.num_steam_generators
        self.sg_steam_flows = [555.0] * self.config.num_steam_generators
        self.sg_steam_qualities = [0.99] * self.config.num_steam_generators
        
        # Reset performance tracking
        self.performance_factor = 1.0
        self.operating_hours = 0.0
        self.maintenance_factor = 1.0
        
        # Reset control state
        self.control_mode = "automatic"
        self.load_demand = 1.0
        
        # CRITICAL FIX: Re-apply initial conditions after reset to preserve targeted degraded conditions
        print(f"FEEDWATER: Re-applying initial conditions after reset to preserve targeted degraded conditions")
        self._apply_initial_conditions()
    


# Example usage and testing
if __name__ == "__main__":
    # Create enhanced feedwater system with default configuration
    enhanced_feedwater = EnhancedFeedwaterPhysics()
    
    print("Enhanced Feedwater Physics Model - Parameter Validation")
    print("=" * 65)
    print(f"System ID: {enhanced_feedwater.config.system_id}")
    print(f"Number of Steam Generators: {enhanced_feedwater.config.num_steam_generators}")
    print(f"Design Total Flow: {enhanced_feedwater.config.design_total_flow} kg/s")
    print(f"Design SG Level: {enhanced_feedwater.config.design_sg_level} m")
    print(f"Number of Pumps: {len(enhanced_feedwater.pump_system.pumps)}")
    print(f"Auto Level Control: {enhanced_feedwater.config.auto_level_control}")
    print()
    
    # Test enhanced feedwater operation
    for hour in range(24):  # 24 hours
        # Simulate load following operation
        if hour < 4:
            # Startup phase
            load_demand = 0.5 + 0.1 * hour  # 50% to 80% load
        elif hour < 8:
            # Ramp to full load
            load_demand = 0.8 + 0.05 * (hour - 4)  # 80% to 100% load
        elif hour < 16:
            # Full load operation
            load_demand = 1.0  # 100% load
        elif hour < 20:
            # Load reduction
            load_demand = 1.0 - 0.1 * (hour - 16)  # 100% to 60% load
        else:
            # Night operation
            load_demand = 0.6  # 60% load
        
        enhanced_feedwater.set_load_demand(load_demand)
        
        # Simulate varying SG conditions
        sg_conditions = {
            'levels': [12.5 + 0.5 * np.sin(hour * 0.1)] * 3,  # Slight level variations
            'pressures': [6.895] * 3,
            'steam_flows': [555.0 * load_demand] * 3,
            'steam_qualities': [0.99] * 3
        }
        
        steam_demands = {
            'total_flow': 1665.0 * load_demand
        }
        
        system_conditions = {
            'feedwater_temperature': 227.0,
            'suction_pressure': 0.5,
            'discharge_pressure': 8.0
        }
        
        result = enhanced_feedwater.update_state(
            sg_conditions=sg_conditions,
            steam_generator_demands=steam_demands,
            system_conditions=system_conditions,
            dt=1.0
        )
        
        if hour % 4 == 0:  # Print every 4 hours
            print(f"Hour {hour:2d}:")
            print(f"  Load Demand: {load_demand:.1%}")
            print(f"  Total Flow: {result['total_flow_rate']:.0f} kg/s")
            print(f"  Total Power: {result['total_power_consumption']:.1f} MW")
            print(f"  System Efficiency: {result['system_efficiency']:.1%}")
            print(f"  Running Pumps: {result['num_running_pumps']}")
            print(f"  Performance Factor: {result['performance_factor']:.3f}")
            print(f"  System Available: {result['system_availability']}")
            
            # Show any active protection
            if result['protection_active']:
                print(f"  PROTECTION ACTIVE: {', '.join(result['active_trips'])}")
            
            # Show diagnostics
            print(f"  Cavitation Risk: {result['cavitation_risk']:.3f}")
            print(f"  Wear Level: {result['wear_level']:.3f}")
            print(f"  Water pH: {result['water_ph']:.2f}")
            print()
    
    print(f"Final State Summary:")
    final_state = enhanced_feedwater.get_state_dict()
    print(f"  Operating Hours: {final_state['feedwater_operating_hours']:.0f}")
    print(f"  Final Flow: {final_state['feedwater_total_flow']:.0f} kg/s")
    print(f"  Final Efficiency: {final_state['feedwater_system_efficiency']:.1%}")
    print(f"  Performance Factor: {final_state['feedwater_performance_factor']:.3f}")
    print(f"  System Availability: {bool(final_state['feedwater_system_availability'])}")
