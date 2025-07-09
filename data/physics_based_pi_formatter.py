"""
Physics-Based PI Data Formatter

Enhanced PI data formatter that uses actual nuclear plant physics to determine
data quality and alarm states, leveraging all existing physics modules for
realistic and meaningful quality indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import warnings

# Import the base PI formatter
from .pi_data_formatter import PIDataFormatter, PIDataQuality, PIAlarmState, PITagConfig

# Import physics modules for validation
try:
    from systems.primary.reactor.physics.neutronics import NeutronicsModel
    from systems.primary.reactor.physics.thermal_hydraulics import ThermalHydraulicsModel
    from systems.secondary.water_chemistry import WaterChemistry, WaterChemistryConfig
    from systems.secondary.feedwater.level_control import ThreeElementControl, ThreeElementConfig
    from systems.secondary.turbine.enhanced_physics import EnhancedTurbinePhysics, EnhancedTurbineConfig
    from systems.secondary.steam_generator.enhanced_physics import EnhancedSteamGeneratorPhysics, EnhancedSteamGeneratorConfig
    from systems.secondary.turbine.rotor_dynamics import RotorDynamicsModel, RotorDynamicsConfig
    from systems.secondary.steam_generator.tsp_fouling_model import TSPFoulingModel
    PHYSICS_MODULES_AVAILABLE = True
except ImportError:
    # Fallback for standalone operation
    PHYSICS_MODULES_AVAILABLE = False
    warnings.warn("Physics modules not available - using simplified validation")


@dataclass
class PhysicsValidationConfig:
    """Configuration for physics-based validation"""
    
    # Neutronics validation tolerances
    power_flux_tolerance: float = 0.15              # 15% tolerance for power-flux correlation
    reactivity_tolerance: float = 500.0             # 500 pcm tolerance for reactivity
    rod_position_tolerance: float = 0.20            # 20% tolerance for rod position correlation
    
    # Thermal hydraulics validation tolerances
    temperature_gradient_tolerance: float = 0.10    # 10% tolerance for temperature gradients
    heat_transfer_tolerance: float = 0.15           # 15% tolerance for heat transfer calculations
    pressure_consistency_tolerance: float = 0.05    # 5% tolerance for pressure consistency
    
    # Water chemistry validation tolerances
    ph_stability_tolerance: float = 0.3             # 0.3 pH units tolerance
    chemistry_stability_threshold: float = 0.8      # Minimum chemistry stability factor
    treatment_efficiency_threshold: float = 0.85    # Minimum treatment efficiency
    
    # Flow balance validation tolerances
    mass_balance_tolerance: float = 0.10            # 10% tolerance for mass balance
    energy_balance_tolerance: float = 0.12          # 12% tolerance for energy balance
    control_performance_threshold: float = 0.7      # Minimum control performance
    
    # Steam generator validation tolerances
    heat_transfer_efficiency_tolerance: float = 0.08 # 8% tolerance for heat transfer efficiency
    fouling_factor_threshold: float = 0.85          # Minimum fouling efficiency factor
    steam_quality_tolerance: float = 0.02           # 2% tolerance for steam quality


class PhysicsValidator:
    """
    Physics validation system that uses actual nuclear plant physics
    to determine data quality and detect sensor/system issues
    """
    
    def __init__(self, config: Optional[PhysicsValidationConfig] = None):
        """Initialize physics validator"""
        self.config = config if config is not None else PhysicsValidationConfig()
        
        # Initialize physics models if available
        if PHYSICS_MODULES_AVAILABLE:
            self.neutronics_model = NeutronicsModel()
            self.thermal_model = ThermalHydraulicsModel()
            self.water_chemistry = WaterChemistry(WaterChemistryConfig())
            self.level_control = ThreeElementControl(ThreeElementConfig())
        else:
            self.neutronics_model = None
            self.thermal_model = None
            self.water_chemistry = None
            self.level_control = None
        
        # Physics validation results cache
        self.validation_cache = {}
        self.validation_history = []
    
    def validate_neutronics_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate neutronics physics consistency"""
        if not PHYSICS_MODULES_AVAILABLE or self.neutronics_model is None:
            return {'status': 'unavailable', 'issues': []}
        
        issues = []
        severity = 'good'
        
        try:
            # Extract neutronics data
            power_level = self._get_value(data_row, ['power_level', 'thermal_power_mw', 'RX_PWR_THRM'])
            neutron_flux = self._get_value(data_row, ['neutron_flux', 'RX_FLUX_NEUT'])
            rod_position = self._get_value(data_row, ['control_rod_position', 'RX_ROD_POS'])
            reactivity = self._get_value(data_row, ['reactivity', 'total_reactivity_pcm', 'RX_REACT_TOT'])
            
            if power_level is not None and neutron_flux is not None:
                # Validate power-flux relationship
                expected_flux = self.neutronics_model.calculate_neutron_flux_from_power(
                    power_level if power_level <= 100 else power_level/30.0  # Handle MW vs % units
                )
                flux_deviation = abs(neutron_flux - expected_flux) / expected_flux
                
                if flux_deviation > self.config.power_flux_tolerance:
                    issues.append(f"Power-flux correlation off by {flux_deviation*100:.1f}%")
                    severity = 'questionable' if flux_deviation > 0.3 else 'uncertain'
            
            if rod_position is not None and power_level is not None:
                # Validate rod position vs power correlation
                expected_reactivity = self.neutronics_model.calculate_control_rod_reactivity(rod_position)
                
                # Check if rod position is reasonable for power level
                if power_level > 90 and rod_position < 70:
                    issues.append(f"Rod position ({rod_position:.1f}%) too low for high power ({power_level:.1f}%)")
                    severity = 'questionable'
                elif power_level < 30 and rod_position > 90:
                    issues.append(f"Rod position ({rod_position:.1f}%) too high for low power ({power_level:.1f}%)")
                    severity = 'questionable'
            
            if reactivity is not None:
                # Check reactivity bounds
                if abs(reactivity) > 1000:  # More than 1000 pcm indicates transient
                    issues.append(f"High reactivity ({reactivity:.0f} pcm) indicates transient conditions")
                    severity = 'uncertain' if abs(reactivity) < 2000 else 'questionable'
        
        except Exception as e:
            issues.append(f"Neutronics validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'neutronics'
        }
    
    def validate_thermal_hydraulics_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate thermal hydraulics physics consistency"""
        if not PHYSICS_MODULES_AVAILABLE or self.thermal_model is None:
            return {'status': 'unavailable', 'issues': []}
        
        issues = []
        severity = 'good'
        
        try:
            # Extract thermal data
            fuel_temp = self._get_value(data_row, ['fuel_temperature', 'RX_TEMP_FUEL'])
            coolant_temp = self._get_value(data_row, ['coolant_temperature', 'RX_TEMP_COOL'])
            coolant_pressure = self._get_value(data_row, ['coolant_pressure', 'RX_PRESS_COOL'])
            thermal_power = self._get_value(data_row, ['thermal_power_mw', 'RX_PWR_THRM'])
            
            # Check for NaN values (critical issue)
            nan_values = []
            if fuel_temp is not None and np.isnan(fuel_temp):
                nan_values.append('fuel_temperature')
            if coolant_temp is not None and np.isnan(coolant_temp):
                nan_values.append('coolant_temperature')
            if coolant_pressure is not None and np.isnan(coolant_pressure):
                nan_values.append('coolant_pressure')
            
            if nan_values:
                issues.append(f"NaN values detected in: {', '.join(nan_values)}")
                severity = 'bad'
                return {'status': severity, 'issues': issues, 'validation_type': 'thermal'}
            
            # Validate temperature relationships
            if fuel_temp is not None and coolant_temp is not None:
                temp_diff = fuel_temp - coolant_temp
                
                # Fuel should be hotter than coolant
                if temp_diff < 50:
                    issues.append(f"Fuel-coolant temperature difference too small ({temp_diff:.1f}°C)")
                    severity = 'questionable'
                elif temp_diff > 200:
                    issues.append(f"Fuel-coolant temperature difference too large ({temp_diff:.1f}°C)")
                    severity = 'uncertain'
                
                # Check for temperature inversion (impossible)
                if fuel_temp < coolant_temp:
                    issues.append(f"Temperature inversion: fuel ({fuel_temp:.1f}°C) < coolant ({coolant_temp:.1f}°C)")
                    severity = 'bad'
            
            # Validate PWR temperature ranges
            if coolant_temp is not None:
                if coolant_temp < 250 or coolant_temp > 350:
                    issues.append(f"Coolant temperature ({coolant_temp:.1f}°C) outside PWR range (250-350°C)")
                    severity = 'questionable'
            
            if fuel_temp is not None:
                if fuel_temp < 300 or fuel_temp > 800:
                    issues.append(f"Fuel temperature ({fuel_temp:.1f}°C) outside normal range (300-800°C)")
                    severity = 'questionable' if 250 < fuel_temp < 900 else 'bad'
            
            # Validate pressure consistency
            if coolant_pressure is not None:
                if coolant_pressure < 10 or coolant_pressure > 18:
                    issues.append(f"Coolant pressure ({coolant_pressure:.1f} MPa) outside PWR range (10-18 MPa)")
                    severity = 'questionable'
        
        except Exception as e:
            issues.append(f"Thermal validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'thermal'
        }
    
    def validate_water_chemistry_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate water chemistry physics and stability"""
        if not PHYSICS_MODULES_AVAILABLE or self.water_chemistry is None:
            return {'status': 'unavailable', 'issues': []}
        
        issues = []
        severity = 'good'
        
        try:
            # Extract chemistry data
            ph = self._get_value(data_row, ['ph', 'water_chemistry_ph', 'FW_PH'])
            iron_conc = self._get_value(data_row, ['iron_concentration', 'water_chemistry_iron_concentration'])
            copper_conc = self._get_value(data_row, ['copper_concentration', 'water_chemistry_copper_concentration'])
            dissolved_oxygen = self._get_value(data_row, ['dissolved_oxygen', 'water_chemistry_dissolved_oxygen', 'FW_O2_DISS'])
            treatment_efficiency = self._get_value(data_row, ['treatment_efficiency', 'water_chemistry_treatment_efficiency'])
            
            # Validate pH stability
            if ph is not None:
                optimal_ph = 9.2
                ph_deviation = abs(ph - optimal_ph)
                
                if ph_deviation > self.config.ph_stability_tolerance:
                    issues.append(f"pH ({ph:.2f}) deviates from optimal (9.2) by {ph_deviation:.2f}")
                    severity = 'uncertain' if ph_deviation < 0.5 else 'questionable'
                
                # Check pH bounds
                if ph < 8.5 or ph > 9.6:
                    issues.append(f"pH ({ph:.2f}) outside allowable range (8.5-9.6)")
                    severity = 'questionable'
            
            # Validate chemistry concentrations
            if iron_conc is not None and iron_conc > 0.2:  # > 0.2 ppm indicates issues
                issues.append(f"High iron concentration ({iron_conc:.3f} ppm)")
                severity = 'uncertain' if iron_conc < 0.5 else 'questionable'
            
            if copper_conc is not None and copper_conc > 0.1:  # > 0.1 ppm indicates issues
                issues.append(f"High copper concentration ({copper_conc:.3f} ppm)")
                severity = 'uncertain' if copper_conc < 0.2 else 'questionable'
            
            if dissolved_oxygen is not None and dissolved_oxygen > 0.01:  # > 0.01 ppm in PWR secondary
                issues.append(f"High dissolved oxygen ({dissolved_oxygen:.3f} ppm)")
                severity = 'uncertain' if dissolved_oxygen < 0.05 else 'questionable'
            
            # Validate treatment system effectiveness
            if treatment_efficiency is not None:
                if treatment_efficiency < self.config.treatment_efficiency_threshold:
                    issues.append(f"Low treatment efficiency ({treatment_efficiency:.1%})")
                    severity = 'uncertain' if treatment_efficiency > 0.7 else 'questionable'
        
        except Exception as e:
            issues.append(f"Chemistry validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'chemistry'
        }
    
    def validate_flow_balance_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate flow balance and mass conservation"""
        issues = []
        severity = 'good'
        
        try:
            # Extract flow data
            feedwater_flow = self._get_value(data_row, ['feedwater_total_flow', 'FW_FLOW_TOT'])
            steam_flow_1 = self._get_value(data_row, ['SG01_FLOW_STM'])
            steam_flow_2 = self._get_value(data_row, ['SG02_FLOW_STM'])
            steam_flow_3 = self._get_value(data_row, ['SG03_FLOW_STM'])
            
            # Calculate total steam flow
            steam_flows = [f for f in [steam_flow_1, steam_flow_2, steam_flow_3] if f is not None]
            if steam_flows:
                total_steam_flow = sum(steam_flows)
                
                if feedwater_flow is not None:
                    # Mass balance check: feedwater in ≈ steam out
                    flow_imbalance = abs(feedwater_flow - total_steam_flow) / max(feedwater_flow, total_steam_flow)
                    
                    if flow_imbalance > self.config.mass_balance_tolerance:
                        issues.append(f"Flow imbalance: FW={feedwater_flow:.0f}, Steam={total_steam_flow:.0f} kg/s ({flow_imbalance*100:.1f}%)")
                        severity = 'uncertain' if flow_imbalance < 0.2 else 'questionable'
            
            # Check individual steam generator flow balance
            if len(steam_flows) >= 2:
                avg_flow = np.mean(steam_flows)
                max_deviation = max(abs(f - avg_flow) / avg_flow for f in steam_flows)
                
                if max_deviation > 0.15:  # 15% deviation between SGs
                    issues.append(f"Unbalanced SG flows: max deviation {max_deviation*100:.1f}%")
                    severity = 'uncertain'
        
        except Exception as e:
            issues.append(f"Flow balance validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'flow_balance'
        }
    
    def validate_control_system_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate control system performance and response"""
        issues = []
        severity = 'good'
        
        try:
            # Extract control data
            control_performance = self._get_value(data_row, ['level_control_performance', 'control_performance'])
            level_error = self._get_value(data_row, ['level_control_avg_error', 'avg_level_error'])
            auto_mode = self._get_value(data_row, ['level_control_auto_mode', 'auto_mode'])
            
            # Validate control performance
            if control_performance is not None:
                if control_performance < self.config.control_performance_threshold:
                    issues.append(f"Poor control performance ({control_performance:.1%})")
                    severity = 'uncertain' if control_performance > 0.5 else 'questionable'
            
            # Validate level control errors
            if level_error is not None:
                if level_error > 1.0:  # > 1 meter average error
                    issues.append(f"High level control error ({level_error:.2f} m)")
                    severity = 'uncertain' if level_error < 2.0 else 'questionable'
            
            # Check for control system issues
            if auto_mode is not None and auto_mode == 0:
                issues.append("Control system in manual mode")
                severity = 'uncertain'
        
        except Exception as e:
            issues.append(f"Control validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'control'
        }
    
    def validate_steam_generator_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate steam generator heat transfer physics"""
        issues = []
        severity = 'good'
        
        try:
            # Extract steam generator data
            thermal_power = self._get_value(data_row, ['thermal_power_mw', 'RX_PWR_THRM'])
            steam_flow = self._get_value(data_row, ['total_steam_flow', 'FW_FLOW_TOT'])
            steam_pressure = self._get_value(data_row, ['steam_pressure', 'SG01_PRESS_SEC'])
            steam_quality = self._get_value(data_row, ['steam_quality', 'avg_steam_quality'])
            
            # Validate steam quality
            if steam_quality is not None:
                if steam_quality < 0.95:
                    issues.append(f"Low steam quality ({steam_quality:.3f})")
                    severity = 'uncertain' if steam_quality > 0.90 else 'questionable'
                elif steam_quality > 1.0:
                    issues.append(f"Impossible steam quality ({steam_quality:.3f} > 1.0)")
                    severity = 'bad'
            
            # Validate heat transfer efficiency
            if thermal_power is not None and steam_flow is not None:
                # Simplified heat transfer efficiency check
                # Expected steam flow for given thermal power
                expected_steam_flow = thermal_power * 0.5  # Rough correlation
                flow_deviation = abs(steam_flow - expected_steam_flow) / expected_steam_flow
                
                if flow_deviation > self.config.heat_transfer_efficiency_tolerance:
                    issues.append(f"Heat transfer efficiency deviation: {flow_deviation*100:.1f}%")
                    severity = 'uncertain' if flow_deviation < 0.15 else 'questionable'
        
        except Exception as e:
            issues.append(f"Steam generator validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'steam_generator'
        }
    
    def _get_value(self, data_row: Dict[str, Any], possible_keys: List[str]) -> Optional[float]:
        """Get value from data row using multiple possible key names"""
        for key in possible_keys:
            if key in data_row and data_row[key] is not None:
                try:
                    return float(data_row[key])
                except (ValueError, TypeError):
                    continue
        return None
    
    def validate_turbine_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate turbine physics and mechanical systems"""
        issues = []
        severity = 'good'
        
        try:
            # Extract turbine data
            rotor_speed = self._get_value(data_row, ['rotor_speed', 'TB_SPEED'])
            electrical_power = self._get_value(data_row, ['electrical_power_net', 'TB_PWR_ELEC'])
            steam_flow = self._get_value(data_row, ['steam_flow', 'total_steam_flow'])
            vibration = self._get_value(data_row, ['vibration_displacement', 'vibration_level'])
            bearing_temp = self._get_value(data_row, ['max_bearing_temperature', 'bearing_temperature'])
            thermal_stress = self._get_value(data_row, ['max_thermal_stress', 'thermal_stress'])
            
            # Validate rotor speed
            if rotor_speed is not None:
                if rotor_speed < 3550 or rotor_speed > 3650:  # ±50 RPM from 3600
                    issues.append(f"Rotor speed ({rotor_speed:.0f} RPM) outside normal range (3550-3650)")
                    severity = 'uncertain' if 3500 < rotor_speed < 3700 else 'questionable'
                
                # Check for overspeed condition
                if rotor_speed > 3780:  # 105% overspeed trip
                    issues.append(f"Overspeed condition: {rotor_speed:.0f} RPM")
                    severity = 'bad'
            
            # Validate power vs steam flow correlation
            if electrical_power is not None and steam_flow is not None:
                # Expected power for given steam flow (simplified)
                expected_power = steam_flow * 0.65  # Rough MW per kg/s correlation
                power_deviation = abs(electrical_power - expected_power) / expected_power
                
                if power_deviation > 0.15:  # 15% deviation
                    issues.append(f"Power-steam flow correlation off by {power_deviation*100:.1f}%")
                    severity = 'uncertain' if power_deviation < 0.25 else 'questionable'
            
            # Validate vibration levels
            if vibration is not None:
                if vibration > 15.0:  # > 15 mils indicates issues
                    issues.append(f"High vibration ({vibration:.1f} mils)")
                    severity = 'uncertain' if vibration < 20.0 else 'questionable'
                
                if vibration > 25.0:  # Trip level
                    issues.append(f"Vibration trip level exceeded ({vibration:.1f} mils)")
                    severity = 'bad'
            
            # Validate bearing temperatures
            if bearing_temp is not None:
                if bearing_temp > 100.0:  # > 100°C indicates issues
                    issues.append(f"High bearing temperature ({bearing_temp:.1f}°C)")
                    severity = 'uncertain' if bearing_temp < 110.0 else 'questionable'
                
                if bearing_temp > 120.0:  # Trip level
                    issues.append(f"Bearing temperature trip level exceeded ({bearing_temp:.1f}°C)")
                    severity = 'bad'
            
            # Validate thermal stress
            if thermal_stress is not None:
                stress_mpa = thermal_stress / 1e6  # Convert Pa to MPa
                if stress_mpa > 600:  # > 600 MPa indicates high stress
                    issues.append(f"High thermal stress ({stress_mpa:.0f} MPa)")
                    severity = 'uncertain' if stress_mpa < 700 else 'questionable'
                
                if stress_mpa > 800:  # Trip level
                    issues.append(f"Thermal stress trip level exceeded ({stress_mpa:.0f} MPa)")
                    severity = 'bad'
        
        except Exception as e:
            issues.append(f"Turbine validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'turbine'
        }
    
    def validate_steam_generator_advanced_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate advanced steam generator physics including fouling effects"""
        issues = []
        severity = 'good'
        
        try:
            # Extract advanced steam generator data
            fouling_efficiency = self._get_value(data_row, ['fouling_efficiency_factor', 'heat_transfer_efficiency'])
            primary_temp_in = self._get_value(data_row, ['SG01_TEMP_PRI_IN', 'primary_inlet_temp'])
            primary_temp_out = self._get_value(data_row, ['SG01_TEMP_PRI_OUT', 'primary_outlet_temp'])
            secondary_pressure = self._get_value(data_row, ['SG01_PRESS_SEC', 'secondary_pressure'])
            water_level = self._get_value(data_row, ['SG01_LVL_WTR', 'water_level'])
            
            # Validate fouling effects
            if fouling_efficiency is not None:
                if fouling_efficiency < self.config.fouling_factor_threshold:
                    fouling_loss = (1.0 - fouling_efficiency) * 100
                    issues.append(f"Significant fouling detected: {fouling_loss:.1f}% efficiency loss")
                    severity = 'uncertain' if fouling_efficiency > 0.8 else 'questionable'
            
            # Validate temperature differences
            if primary_temp_in is not None and primary_temp_out is not None:
                temp_drop = primary_temp_in - primary_temp_out
                
                # Expected temperature drop for PWR (typically 30-40°C)
                if temp_drop < 20 or temp_drop > 50:
                    issues.append(f"Primary temperature drop ({temp_drop:.1f}°C) outside normal range (20-50°C)")
                    severity = 'uncertain' if 15 < temp_drop < 60 else 'questionable'
            
            # Validate pressure consistency
            if secondary_pressure is not None:
                if secondary_pressure < 5.5 or secondary_pressure > 7.5:  # PWR secondary pressure range
                    issues.append(f"Secondary pressure ({secondary_pressure:.2f} MPa) outside normal range (5.5-7.5 MPa)")
                    severity = 'uncertain' if 5.0 < secondary_pressure < 8.0 else 'questionable'
            
            # Validate water level
            if water_level is not None:
                if water_level < 20 or water_level > 80:  # % level
                    issues.append(f"Water level ({water_level:.1f}%) outside normal range (20-80%)")
                    severity = 'uncertain' if 10 < water_level < 90 else 'questionable'
                
                if water_level < 15:  # Low level alarm
                    issues.append(f"Low water level alarm: {water_level:.1f}%")
                    severity = 'questionable'
        
        except Exception as e:
            issues.append(f"Advanced SG validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'steam_generator_advanced'
        }
    
    def validate_system_integration_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate cross-system physics integration and energy balance"""
        issues = []
        severity = 'good'
        
        try:
            # Extract system-wide data
            reactor_power = self._get_value(data_row, ['thermal_power_mw', 'RX_PWR_THRM'])
            turbine_power = self._get_value(data_row, ['electrical_power_net', 'TB_PWR_ELEC'])
            steam_flow = self._get_value(data_row, ['total_steam_flow', 'FW_FLOW_TOT'])
            feedwater_temp = self._get_value(data_row, ['feedwater_temperature'])
            steam_temp = self._get_value(data_row, ['steam_temperature'])
            
            # Validate overall energy balance
            if reactor_power is not None and turbine_power is not None:
                # Expected turbine efficiency ~34%
                expected_turbine_power = reactor_power * 0.34
                power_deviation = abs(turbine_power - expected_turbine_power) / expected_turbine_power
                
                if power_deviation > self.config.energy_balance_tolerance:
                    issues.append(f"Energy balance deviation: {power_deviation*100:.1f}%")
                    severity = 'uncertain' if power_deviation < 0.2 else 'questionable'
            
            # Validate steam cycle thermodynamics
            if feedwater_temp is not None and steam_temp is not None:
                temp_rise = steam_temp - feedwater_temp
                
                # Expected temperature rise in steam generator
                if temp_rise < 40 or temp_rise > 80:  # Typical range
                    issues.append(f"Steam cycle temperature rise ({temp_rise:.1f}°C) outside expected range")
                    severity = 'uncertain'
            
            # Validate system response consistency
            if reactor_power is not None and steam_flow is not None:
                # Steam flow should correlate with reactor power
                expected_steam_flow = reactor_power * 0.5  # Rough correlation
                flow_deviation = abs(steam_flow - expected_steam_flow) / expected_steam_flow
                
                if flow_deviation > 0.2:  # 20% deviation
                    issues.append(f"System response inconsistency: power vs steam flow deviation {flow_deviation*100:.1f}%")
                    severity = 'uncertain'
        
        except Exception as e:
            issues.append(f"System integration validation error: {str(e)}")
            severity = 'uncertain'
        
        return {
            'status': severity,
            'issues': issues,
            'validation_type': 'system_integration'
        }
    
    def validate_all_physics(self, data_row: Dict[str, Any]) -> Dict[str, Any]:
        """Run all physics validations and determine overall quality"""
        validations = [
            self.validate_neutronics_physics(data_row),
            self.validate_thermal_hydraulics_physics(data_row),
            self.validate_water_chemistry_physics(data_row),
            self.validate_flow_balance_physics(data_row),
            self.validate_control_system_physics(data_row),
            self.validate_steam_generator_physics(data_row),
            self.validate_turbine_physics(data_row),
            self.validate_steam_generator_advanced_physics(data_row),
            self.validate_system_integration_physics(data_row)
        ]
        
        # Collect all issues
        all_issues = []
        severity_levels = []
        
        for validation in validations:
            if validation['status'] != 'unavailable':
                all_issues.extend(validation['issues'])
                severity_levels.append(validation['status'])
        
        # Determine overall severity
        if 'bad' in severity_levels:
            overall_severity = 'bad'
        elif 'questionable' in severity_levels:
            overall_severity = 'questionable'
        elif 'uncertain' in severity_levels:
            overall_severity = 'uncertain'
        else:
            overall_severity = 'good'
        
        return {
            'overall_status': overall_severity,
            'all_issues': all_issues,
            'individual_validations': validations,
            'total_issues': len(all_issues)
        }


class PhysicsBasedPIFormatter(PIDataFormatter):
    """
    Enhanced PI formatter that uses actual nuclear plant physics
    to determine data quality and alarm states
    """
    
    def __init__(self, plant_code: str = "NPP", unit_number: int = 1,
                 validation_config: Optional[PhysicsValidationConfig] = None):
        super().__init__(plant_code, unit_number)
        
        # Initialize physics validator
        self.physics_validator = PhysicsValidator(validation_config)
        
        # Physics validation tracking
        self.validation_history = []
        self.physics_issues_count = 0
    
    def determine_data_quality_physics_based(self, value: Any, tag_config: PITagConfig, 
                                           full_data_row: Dict[str, Any]) -> PIDataQuality:
        """
        Determine data quality based on actual physics validation
        
        Args:
            value: Current data value
            tag_config: PI tag configuration
            full_data_row: Complete data row for physics consistency checks
            
        Returns:
            PIDataQuality based on physics validation
        """
        # Start with basic checks
        if pd.isna(value) or value is None:
            return PIDataQuality.BAD
        
        if not isinstance(value, (int, float, bool)):
            return PIDataQuality.GOOD
        
        # Check if value is outside physical limits (QUESTIONABLE)
        if tag_config.low_limit is not None and value < tag_config.low_limit:
            return PIDataQuality.QUESTIONABLE
        
        if tag_config.high_limit is not None and value > tag_config.high_limit:
            return PIDataQuality.QUESTIONABLE
        
        # Run physics validation
        physics_validation = self.physics_validator.validate_all_physics(full_data_row)
        
        # Map physics validation results to PI quality
        physics_status = physics_validation['overall_status']
        
        if physics_status == 'bad':
            return PIDataQuality.BAD
        elif physics_status == 'questionable':
            return PIDataQuality.QUESTIONABLE
        elif physics_status == 'uncertain':
            return PIDataQuality.UNCERTAIN
        else:
            return PIDataQuality.GOOD
    
    def convert_to_pi_format(self, simulation_data: pd.DataFrame) -> pd.DataFrame:
        """
        Convert simulation data to PI format using physics-based quality determination
        """
        if self.tag_mapping is None or len(self.tag_mapping) == 0:
            sim_vars = [col for col in simulation_data.columns if col != 'time']
            self.create_tag_mapping(sim_vars)
        
        pi_records = []
        
        for _, row in simulation_data.iterrows():
            timestamp = pd.to_datetime(row['time'], unit='s').strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            row_dict = row.to_dict()
            
            # Run physics validation once per row
            physics_validation = self.physics_validator.validate_all_physics(row_dict)
            
            for sim_var, pi_tag in self.tag_mapping.items():
                if sim_var in simulation_data.columns:
                    value = row[sim_var]
                    tag_config = self.tag_configs.get(pi_tag)
                    
                    if tag_config is None:
                        tag_config = PITagConfig(pi_tag, f"Unmapped variable {sim_var}", "units")
                    
                    # Use physics-based quality determination
                    quality = self.determine_data_quality_physics_based(value, tag_config, row_dict)
                    alarm_state = self.determine_alarm_state(value, tag_config)
                    
                    # Add physics issues to description if quality is not good
                    description = tag_config.description
                    if quality != PIDataQuality.GOOD and physics_validation['all_issues']:
                        # Add first physics issue to description
                        first_issue = physics_validation['all_issues'][0]
                        description += f" [Physics: {first_issue[:50]}...]"
                    
                    pi_records.append({
                        'TagName': pi_tag,
                        'Timestamp': timestamp,
                        'Value': value,
                        'Quality': quality.value,
                        'Units': tag_config.units,
                        'Description': description,
                        'AlarmState': alarm_state.value,
                        'System': tag_config.system,
                        'Subsystem': tag_config.subsystem,
                        'PhysicsIssues': len(physics_validation['all_issues']),
                        'PhysicsStatus': physics_validation['overall_status']
                    })
        
        return pd.DataFrame(pi_records)
    
    def generate_physics_validation_report(self, pi_data: pd.DataFrame) -> str:
        """Generate a detailed physics validation report"""
        report = []
        report.append("=" * 70)
        report.append("PHYSICS-BASED PI DATA VALIDATION REPORT")
        report.append("=" * 70)
        report.append(f"Plant: {self.plant_code} Unit {self.unit_number}")
        report.append(f"Report Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Physics validation summary
        if 'PhysicsStatus' in pi_data.columns:
            physics_status_counts = pi_data['PhysicsStatus'].value_counts()
            report.append("PHYSICS VALIDATION SUMMARY:")
            for status, count in physics_status_counts.items():
                percentage = (count / len(pi_data)) * 100
                report.append(f"  {status.upper()}: {count:,} ({percentage:.1f}%)")
            report.append("")
        
        # Quality vs Physics correlation
        if 'Quality' in pi_data.columns and 'PhysicsStatus' in pi_data.columns:
            report.append("QUALITY vs PHYSICS CORRELATION:")
            correlation_table = pd.crosstab(pi_data['Quality'], pi_data['PhysicsStatus'])
            for quality in correlation_table.index:
                report.append(f"  {quality}:")
                for physics_status in correlation_table.columns:
                    count = correlation_table.loc[quality, physics_status]
                    report.append(f"    {physics_status}: {count}")
            report.append("")
        
        # Physics issues summary
        if 'PhysicsIssues' in pi_data.columns:
            avg_issues = pi_data['PhysicsIssues'].mean()
            max_issues = pi_data['PhysicsIssues'].max()
            report.append("PHYSICS ISSUES SUMMARY:")
            report.append(f"  Average issues per data point: {avg_issues:.2f}")
            report.append(f"  Maximum issues in single data point: {max_issues}")
            
            # Show distribution of issue counts
            issue_counts = pi_data['PhysicsIssues'].value_counts().sort_index()
            report.append("  Issue count distribution:")
            for issues, count in issue_counts.items():
                percentage = (count / len(pi_data)) * 100
                report.append(f"    {issues} issues: {count:,} data points ({percentage:.1f}%)")
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)


def create_physics_based_formatter(plant_code: str = "NPP", 
                                  validation_config: Optional[PhysicsValidationConfig] = None) -> PhysicsBasedPIFormatter:
    """Create a physics-based PI formatter"""
    return PhysicsBasedPIFormatter(plant_code=plant_code, validation_config=validation_config)
