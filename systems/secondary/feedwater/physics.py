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
from simulator.state import StateProvider, StateVariable, StateCategory, make_state_name, StateProviderMixin

from .pump_system import FeedwaterPumpSystem, FeedwaterPumpSystemConfig
from .level_control import ThreeElementControl, ThreeElementConfig
from .water_chemistry import WaterQualityModel, WaterQualityConfig
from .performance_monitoring import PerformanceDiagnostics, PerformanceDiagnosticsConfig
from .protection_system import FeedwaterProtectionSystem, FeedwaterProtectionConfig

warnings.filterwarnings("ignore")


@dataclass
class EnhancedFeedwaterConfig:
    """
    Enhanced feedwater configuration that integrates all subsystems
    
    References:
    - Complete feedwater system specifications
    - Integration requirements
    - Performance optimization parameters
    """
    
    # System configuration
    system_id: str = "EFC-001"                           # Enhanced feedwater system identifier
    num_steam_generators: int = 3                        # Number of steam generators
    
    # Design parameters
    design_total_flow: float = 1665.0                    # kg/s total design flow
    design_sg_level: float = 12.5                        # m design steam generator level
    design_feedwater_temperature: float = 227.0          # °C design feedwater temperature
    design_pressure: float = 8.0                         # MPa design system pressure
    
    # Subsystem configurations
    pump_system_config: FeedwaterPumpSystemConfig = field(default_factory=FeedwaterPumpSystemConfig)
    control_config: ThreeElementConfig = field(default_factory=ThreeElementConfig)
    water_quality_config: WaterQualityConfig = field(default_factory=WaterQualityConfig)
    diagnostics_config: PerformanceDiagnosticsConfig = field(default_factory=PerformanceDiagnosticsConfig)
    protection_config: FeedwaterProtectionConfig = field(default_factory=FeedwaterProtectionConfig)
    
    # Performance parameters
    design_efficiency: float = 0.85                      # Overall system design efficiency
    minimum_flow_fraction: float = 0.1                   # Minimum flow as fraction of design
    maximum_flow_fraction: float = 1.2                   # Maximum flow as fraction of design
    
    # Control parameters
    auto_level_control: bool = True                      # Enable automatic level control
    load_following_enabled: bool = True                  # Enable load following
    steam_quality_compensation: bool = True              # Enable steam quality compensation
    predictive_maintenance: bool = True                  # Enable predictive maintenance


class EnhancedFeedwaterPhysics(StateProviderMixin):
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
    
    Implements StateProviderMixin for automatic state collection with proper naming.
    """
    
    def __init__(self, config: Optional[EnhancedFeedwaterConfig] = None):
        """Initialize enhanced feedwater physics model"""
        if config is None:
            config = EnhancedFeedwaterConfig()
        
        self.config = config
        
        # Initialize subsystems with configurations
        pump_config = config.pump_system_config or FeedwaterPumpSystemConfig(
            num_steam_generators=config.num_steam_generators
        )
        
        control_config = config.control_config or ThreeElementConfig(
            num_steam_generators=config.num_steam_generators
        )
        
        water_config = config.water_quality_config or WaterQualityConfig()
        
        diagnostics_config = config.diagnostics_config or PerformanceDiagnosticsConfig()
        
        protection_config = config.protection_config or FeedwaterProtectionConfig()
        
        # Create subsystems
        self.pump_system = FeedwaterPumpSystem(pump_config)
        self.level_control = ThreeElementControl(control_config)
        self.water_quality = WaterQualityModel(water_config)
        self.diagnostics = PerformanceDiagnostics(diagnostics_config)
        self.protection_system = FeedwaterProtectionSystem(protection_config)
        
        # Enhanced feedwater state
        self.total_flow_rate = 0.0                       # kg/s total system flow
        self.total_power_consumption = 0.0               # MW total power consumption
        self.system_efficiency = 0.0                     # Overall system efficiency
        self.system_availability = True                  # System availability status
        
        # Steam generator conditions
        self.sg_levels = [12.5] * config.num_steam_generators      # m SG levels
        self.sg_pressures = [6.895] * config.num_steam_generators  # MPa SG pressures
        self.sg_steam_flows = [555.0] * config.num_steam_generators # kg/s steam flows
        self.sg_steam_qualities = [0.99] * config.num_steam_generators # Steam qualities
        
        # Performance tracking
        self.performance_factor = 1.0                    # Overall performance factor
        self.operating_hours = 0.0                       # Total operating hours
        self.maintenance_factor = 1.0                    # Maintenance effectiveness factor
        
        # Control state
        self.control_mode = "automatic"                  # Control mode
        self.load_demand = 1.0                          # Load demand (0-1)
        
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
        
        water_quality_results = self.water_quality.update_water_chemistry(
            makeup_water_quality=makeup_water_quality,
            blowdown_rate=0.02,  # 2% blowdown rate
            chemical_doses=chemical_doses,
            dt=dt
        )
        
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
        
        # CRITICAL FIX: Convert dt from minutes to seconds for pump system
        # The feedwater physics receives dt in minutes, but pump system expects seconds
        dt_seconds = dt * 60.0
        
        pump_results = self.pump_system.update_system(
            dt=dt_seconds,
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
        water_quality_factor = 1.0 - water_quality_results.get('water_aggressiveness', 0.0) * 0.1
        diagnostics_factor = diagnostics_results.get('overall_health_factor', 1.0)
        
        self.performance_factor = pump_performance * water_quality_factor * diagnostics_factor
        self.maintenance_factor = diagnostics_results.get('maintenance_effectiveness', 1.0)
        
        # Update operating hours
        self.operating_hours += dt
        
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
            
            # Water quality results
            'water_ph': water_quality_results['ph'],
            'water_hardness': water_quality_results['hardness'],
            'water_tds': water_quality_results['total_dissolved_solids'],
            'water_aggressiveness': water_quality_results['water_aggressiveness'],
            'chemical_treatment_efficiency': water_quality_results.get('treatment_efficiency', 1.0),
            
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
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, float]:
        """
        Perform maintenance operations on feedwater systems
        
        Args:
            maintenance_type: Type of maintenance
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results
        """
        results = {}
        
        if maintenance_type == "pump_maintenance":
            # Perform pump maintenance
            pump_id = kwargs.get('pump_id', None)
            maintenance_results = self.pump_system.perform_maintenance(pump_id, **kwargs)
            results.update(maintenance_results)
            
        elif maintenance_type == "water_treatment":
            # Reset water treatment system
            treatment_results = self.water_quality.perform_treatment_maintenance(**kwargs)
            results.update(treatment_results)
            
        elif maintenance_type == "control_calibration":
            # Calibrate control system
            calibration_results = self.level_control.perform_calibration(**kwargs)
            results.update(calibration_results)
            
        elif maintenance_type == "system_cleaning":
            # Perform system cleaning
            cleaning_results = self.diagnostics.perform_system_cleaning(**kwargs)
            results.update(cleaning_results)
        
        # Update maintenance factor
        self.maintenance_factor = min(1.0, self.maintenance_factor + 0.1)
        results['maintenance_factor'] = self.maintenance_factor
        
        return results
    
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
        state_dict.update(self.pump_system.get_state_dict())
        state_dict.update(self.level_control.get_state_dict())
        state_dict.update(self.water_quality.get_state_dict())
        state_dict.update(self.diagnostics.get_state_dict())
        state_dict.update(self.protection_system.get_state_dict())
        
        prefixed = {f"feedwater.{key}": value for key, value in state_dict.items()}
        return prefixed
    
    def reset(self) -> None:
        """Reset enhanced feedwater system to initial conditions"""
        # Reset subsystems
        self.pump_system.reset()
        self.level_control.reset()
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
