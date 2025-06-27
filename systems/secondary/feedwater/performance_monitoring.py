"""
Performance Monitoring and Diagnostics

This module provides advanced performance monitoring, diagnostics, and
predictive maintenance capabilities for the feedwater system.

Key Features:
1. Cavitation monitoring and modeling
2. Mechanical wear tracking
3. Performance degradation analysis
4. Predictive maintenance recommendations
5. System health assessment
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


@dataclass
class CavitationConfig:
    """Configuration for cavitation monitoring"""
    npsh_safety_margin: float = 2.0                  # m NPSH safety margin
    cavitation_intensity_threshold: float = 0.1      # Intensity threshold for monitoring
    severe_cavitation_threshold: float = 0.7         # Intensity for immediate action
    damage_accumulation_rate: float = 0.01           # Damage rate per hour at full intensity
    acoustic_monitoring_enabled: bool = True         # Enable acoustic monitoring
    vibration_monitoring_enabled: bool = True        # Enable vibration monitoring


@dataclass
class WearTrackingConfig:
    """Configuration for wear tracking"""
    impeller_wear_rate_base: float = 0.001           # %/hour base impeller wear rate
    bearing_wear_rate_base: float = 0.0005           # %/hour base bearing wear rate
    seal_wear_rate_base: float = 0.0008              # %/hour base seal wear rate
    
    # Wear thresholds
    impeller_wear_warning: float = .1              # % wear warning threshold
    bearing_wear_warning: float = .15               # % wear warning threshold
    seal_wear_warning: float = .2                  # % wear warning threshold
    
    # Performance impact thresholds
    efficiency_degradation_warning: float = 5.0      # % efficiency loss warning
    flow_degradation_warning: float = 3.0            # % flow loss warning


@dataclass
class PerformanceDiagnosticsConfig:
    """Configuration for performance diagnostics system"""
    cavitation_config: CavitationConfig = None
    wear_tracking_config: WearTrackingConfig = None
    
    # Diagnostic intervals
    continuous_monitoring_enabled: bool = True       # Enable continuous monitoring
    detailed_analysis_interval: float = 24.0         # Hours between detailed analysis
    predictive_maintenance_horizon: float = 720.0    # Hours prediction horizon (30 days)
    
    # Health assessment parameters
    health_score_weights: Dict[str, float] = None    # Weights for health score calculation
    
    def __post_init__(self):
        if self.cavitation_config is None:
            self.cavitation_config = CavitationConfig()
        if self.wear_tracking_config is None:
            self.wear_tracking_config = WearTrackingConfig()
        if self.health_score_weights is None:
            self.health_score_weights = {
                'cavitation': 0.3,
                'wear': 0.4,
                'vibration': 0.2,
                'performance': 0.1
            }


class CavitationModel:
    """
    Advanced cavitation monitoring and modeling system
    
    This model provides:
    1. Real-time cavitation detection
    2. Damage accumulation tracking
    3. Acoustic signature analysis
    4. Predictive cavitation risk assessment
    """
    
    def __init__(self, config: CavitationConfig):
        """Initialize cavitation model"""
        self.config = config
        
        # Cavitation state tracking
        self.current_intensity = 0.0                  # Current cavitation intensity (0-1)
        self.accumulated_damage = 0.0                 # Total accumulated damage
        self.cavitation_events = []                   # History of cavitation events
        self.time_in_cavitation = 0.0                 # Total time spent cavitating
        
        # Acoustic monitoring
        self.acoustic_signature = 0.0                 # Current acoustic signature
        self.baseline_noise_level = 20.0              # Baseline noise level (dB)
        self.cavitation_noise_increase = 0.0          # Noise increase due to cavitation
        
        # Vibration monitoring
        self.cavitation_induced_vibration = 0.0       # Vibration from cavitation
        self.vibration_frequency_spectrum = {}        # Frequency analysis
        
        # Risk assessment
        self.cavitation_risk_score = 0.0              # Overall risk score (0-1)
        self.predicted_damage_rate = 0.0              # Predicted damage accumulation rate
        
    def update_cavitation_monitoring(self,
                                   npsh_available: float,
                                   npsh_required: float,
                                   flow_rate: float,
                                   pump_speed: float,
                                   dt: float) -> Dict[str, float]:
        """
        Update cavitation monitoring and analysis
        
        Args:
            npsh_available: Available NPSH (m)
            npsh_required: Required NPSH (m)
            flow_rate: Current flow rate (kg/s)
            pump_speed: Pump speed (%)
            dt: Time step (hours)
            
        Returns:
            Dictionary with cavitation analysis results
        """
        # Calculate cavitation threshold
        cavitation_threshold = npsh_required + self.config.npsh_safety_margin
        
        # Determine cavitation intensity
        if npsh_available < cavitation_threshold:
            npsh_deficit = cavitation_threshold - npsh_available
            severity = min(1.0, npsh_deficit / cavitation_threshold)
            
            # Flow and speed effects on cavitation intensity
            flow_factor = (flow_rate / 555.0) ** 2  # Normalized to design flow
            speed_factor = (pump_speed / 100.0) ** 1.5
            
            self.current_intensity = severity * flow_factor * speed_factor
            self.time_in_cavitation += dt
            
            # Record cavitation event
            if self.current_intensity > self.config.cavitation_intensity_threshold:
                event = {
                    'timestamp': dt,  # Simplified timestamp
                    'intensity': self.current_intensity,
                    'npsh_deficit': npsh_deficit,
                    'flow_rate': flow_rate,
                    'pump_speed': pump_speed
                }
                self.cavitation_events.append(event)
                
                # Limit event history
                if len(self.cavitation_events) > 100:
                    self.cavitation_events.pop(0)
        else:
            self.current_intensity = 0.0
        
        # Update damage accumulation
        if self.current_intensity > 0.1:  # Only accumulate damage for significant cavitation
            damage_rate = (self.current_intensity ** 2) * self.config.damage_accumulation_rate
            self.accumulated_damage += damage_rate * dt
        
        # Update acoustic monitoring
        if self.config.acoustic_monitoring_enabled:
            self.cavitation_noise_increase = self.current_intensity * 30.0  # dB increase
            self.acoustic_signature = self.baseline_noise_level + self.cavitation_noise_increase
        
        # Update vibration monitoring
        if self.config.vibration_monitoring_enabled:
            self.cavitation_induced_vibration = self.current_intensity * 2.0  # mm/s
            
            # Simplified frequency analysis
            if self.current_intensity > 0.2:
                # Cavitation typically shows up in specific frequency ranges
                self.vibration_frequency_spectrum = {
                    'low_freq': self.current_intensity * 0.5,    # 0-100 Hz
                    'mid_freq': self.current_intensity * 1.0,    # 100-1000 Hz
                    'high_freq': self.current_intensity * 0.3    # 1000+ Hz
                }
            else:
                self.vibration_frequency_spectrum = {'low_freq': 0.0, 'mid_freq': 0.0, 'high_freq': 0.0}
        
        # Calculate risk score
        self._calculate_cavitation_risk()
        
        return {
            'cavitation_intensity': self.current_intensity,
            'accumulated_damage': self.accumulated_damage,
            'time_in_cavitation': self.time_in_cavitation,
            'acoustic_signature': self.acoustic_signature,
            'cavitation_induced_vibration': self.cavitation_induced_vibration,
            'cavitation_risk_score': self.cavitation_risk_score,
            'predicted_damage_rate': self.predicted_damage_rate,
            'npsh_margin': npsh_available - npsh_required,
            'cavitation_events_count': len(self.cavitation_events)
        }
    
    def _calculate_cavitation_risk(self):
        """Calculate overall cavitation risk score"""
        # Risk factors
        intensity_risk = min(1.0, self.current_intensity / 0.5)
        damage_risk = min(1.0, self.accumulated_damage / 10.0)
        frequency_risk = min(1.0, len(self.cavitation_events) / 50.0)
        
        # Combined risk score
        self.cavitation_risk_score = (intensity_risk * 0.4 + 
                                    damage_risk * 0.4 + 
                                    frequency_risk * 0.2)
        
        # Predicted damage rate
        if self.current_intensity > 0:
            self.predicted_damage_rate = (self.current_intensity ** 2) * self.config.damage_accumulation_rate
        else:
            self.predicted_damage_rate = 0.0


class WearTrackingModel:
    """
    Mechanical wear tracking and prediction system
    
    This model tracks:
    1. Component-specific wear rates
    2. Environmental factors affecting wear
    3. Performance impact of wear
    4. Maintenance scheduling optimization
    """
    
    def __init__(self, config: WearTrackingConfig):
        """Initialize wear tracking model"""
        self.config = config
        
        # Component wear tracking
        self.impeller_wear = 0.0                      # % impeller wear
        self.bearing_wear = 0.0                       # % bearing wear
        self.seal_wear = 0.0                          # % seal wear
        
        # Wear rate tracking
        self.impeller_wear_rate = config.impeller_wear_rate_base
        self.bearing_wear_rate = config.bearing_wear_rate_base
        self.seal_wear_rate = config.seal_wear_rate_base
        
        # Environmental factors
        self.temperature_factor = 1.0                 # Temperature effect on wear
        self.load_factor = 1.0                        # Load effect on wear
        self.water_quality_factor = 1.0               # Water quality effect on wear
        
        # Performance impact
        self.flow_degradation = 0.0                   # % flow degradation due to wear
        self.efficiency_degradation = 0.0             # % efficiency degradation due to wear
        self.reliability_factor = 1.0                 # Overall reliability factor
        
        # Maintenance tracking
        self.time_since_maintenance = 0.0             # Hours since last maintenance
        self.maintenance_effectiveness = 1.0          # Effectiveness of last maintenance
        
    def update_wear_tracking(self,
                           operating_conditions: Dict[str, float],
                           dt: float) -> Dict[str, float]:
        """
        Update wear tracking based on operating conditions
        
        Args:
            operating_conditions: Current operating conditions
            dt: Time step (hours)
            
        Returns:
            Dictionary with wear tracking results
        """
        # Extract operating conditions
        flow_rate = operating_conditions.get('flow_rate', 555.0)
        pump_speed = operating_conditions.get('pump_speed', 100.0)
        bearing_temperature = operating_conditions.get('bearing_temperature', 45.0)
        oil_level = operating_conditions.get('oil_level', 100.0)
        water_aggressiveness = operating_conditions.get('water_aggressiveness', 1.0)
        power_consumption = operating_conditions.get('power_consumption', 10.0)
        
        # Calculate environmental factors
        self._calculate_environmental_factors(
            flow_rate, pump_speed, bearing_temperature, 
            oil_level, water_aggressiveness, power_consumption
        )
        
        # Update component wear
        self._update_impeller_wear(flow_rate, pump_speed, water_aggressiveness, dt)
        self._update_bearing_wear(bearing_temperature, oil_level, power_consumption, dt)
        self._update_seal_wear(power_consumption, bearing_temperature, dt)
        
        # Calculate performance impact
        self._calculate_performance_impact()
        
        # Update maintenance tracking
        self.time_since_maintenance += dt
        
        return {
            'impeller_wear': self.impeller_wear,
            'bearing_wear': self.bearing_wear,
            'seal_wear': self.seal_wear,
            'total_wear': self.impeller_wear + self.bearing_wear + self.seal_wear,
            'flow_degradation': self.flow_degradation,
            'efficiency_degradation': self.efficiency_degradation,
            'reliability_factor': self.reliability_factor,
            'impeller_wear_rate': self.impeller_wear_rate,
            'bearing_wear_rate': self.bearing_wear_rate,
            'seal_wear_rate': self.seal_wear_rate,
            'time_since_maintenance': self.time_since_maintenance,
            'maintenance_effectiveness': self.maintenance_effectiveness
        }
    
    def _calculate_environmental_factors(self, flow_rate, pump_speed, bearing_temp, 
                                       oil_level, water_aggressiveness, power_consumption):
        """Calculate environmental factors affecting wear"""
        # Temperature factor
        self.temperature_factor = max(1.0, (bearing_temp - 60.0) / 30.0)
        
        # Load factor
        load_ratio = power_consumption / 10.0  # Normalized to design power
        self.load_factor = load_ratio ** 1.2
        
        # Water quality factor
        self.water_quality_factor = water_aggressiveness
    
    def _update_impeller_wear(self, flow_rate, pump_speed, water_aggressiveness, dt):
        """Update impeller wear"""
        # Flow and speed effects
        flow_factor = (flow_rate / 555.0) ** 1.5
        speed_factor = (pump_speed / 100.0) ** 2
        
        # Calculate wear rate
        self.impeller_wear_rate = (self.config.impeller_wear_rate_base * 
                                 flow_factor * speed_factor * water_aggressiveness)
        
        # Update wear
        self.impeller_wear += self.impeller_wear_rate * dt
    
    def _update_bearing_wear(self, bearing_temp, oil_level, power_consumption, dt):
        """Update bearing wear"""
        # Temperature effect
        temp_factor = max(1.0, (bearing_temp - 60.0) / 30.0)
        
        # Oil level effect
        oil_factor = max(1.0, (100.0 - oil_level) / 50.0)
        
        # Load effect
        load_factor = (power_consumption / 10.0) ** 1.2
        
        # Calculate wear rate
        self.bearing_wear_rate = (self.config.bearing_wear_rate_base * 
                                temp_factor * oil_factor * load_factor)
        
        # Update wear
        self.bearing_wear += self.bearing_wear_rate * dt
    
    def _update_seal_wear(self, power_consumption, bearing_temp, dt):
        """Update seal wear"""
        # Pressure and temperature effects
        pressure_factor = (power_consumption / 10.0) ** 1.5
        temp_factor = max(1.0, (bearing_temp - 50.0) / 40.0)
        
        # Calculate wear rate
        self.seal_wear_rate = (self.config.seal_wear_rate_base * 
                             pressure_factor * temp_factor)
        
        # Update wear
        self.seal_wear += self.seal_wear_rate * dt
    
    def _calculate_performance_impact(self):
        """Calculate performance impact of wear"""
        # Flow degradation (primarily from impeller wear)
        self.flow_degradation = self.impeller_wear * 0.02  # 2% per % wear
        
        # Efficiency degradation (from all components)
        impeller_efficiency_loss = self.impeller_wear * 0.015
        bearing_efficiency_loss = self.bearing_wear * 0.01
        seal_efficiency_loss = self.seal_wear * 0.005
        
        self.efficiency_degradation = (impeller_efficiency_loss + 
                                     bearing_efficiency_loss + 
                                     seal_efficiency_loss)
        
        # Reliability factor (decreases with total wear)
        total_wear = self.impeller_wear + self.bearing_wear + self.seal_wear
        self.reliability_factor = max(0.1, 1.0 - total_wear / 100.0)


class PerformanceDiagnostics:
    """
    Comprehensive performance diagnostics and health assessment system
    
    This system provides:
    1. Integrated health monitoring
    2. Predictive maintenance recommendations
    3. Performance optimization suggestions
    4. System reliability assessment
    """
    
    def __init__(self, config: PerformanceDiagnosticsConfig):
        """Initialize performance diagnostics"""
        self.config = config
        
        # Initialize sub-models
        self.cavitation_model = CavitationModel(config.cavitation_config)
        self.wear_tracking = WearTrackingModel(config.wear_tracking_config)
        
        # Overall system health
        self.overall_health_score = 1.0            # Overall health score (0-1)
        self.system_reliability = 1.0              # System reliability factor
        self.maintenance_urgency = 0.0             # Maintenance urgency (0-1)
        
        # Diagnostic history
        self.health_history = []                   # Health score history
        self.diagnostic_events = []               # Significant diagnostic events
        
        # Predictive maintenance
        self.predicted_failure_time = float('inf') # Hours to predicted failure
        self.maintenance_recommendations = []      # Current maintenance recommendations
        
    def update_diagnostics(self,
                         pump_results: Dict[str, Dict],
                         water_quality_results: Dict[str, float],
                         system_conditions: Dict[str, float],
                         dt: float) -> Dict[str, float]:
        """
        Update comprehensive diagnostics
        
        Args:
            pump_results: Results from pump system
            water_quality_results: Water quality analysis results
            system_conditions: System operating conditions
            dt: Time step (hours)
            
        Returns:
            Dictionary with diagnostic results
        """
        # Aggregate pump data for analysis
        total_cavitation_risk = 0.0
        total_wear_level = 0.0
        total_vibration = 0.0
        num_pumps = len(pump_results)
        
        cavitation_results = {}
        wear_results = {}
        
        if num_pumps > 0:
            for pump_id, pump_data in pump_results.items():
                # Update cavitation monitoring
                cavitation_result = self.cavitation_model.update_cavitation_monitoring(
                    npsh_available=pump_data.get('npsh_available', 20.0),
                    npsh_required=15.0,  # Typical requirement
                    flow_rate=pump_data.get('flow_rate', 555.0),
                    pump_speed=pump_data.get('speed_percent', 100.0),
                    dt=dt
                )
                cavitation_results[pump_id] = cavitation_result
                total_cavitation_risk += cavitation_result['cavitation_risk_score']
                
                # Update wear tracking
                operating_conditions = {
                    'flow_rate': pump_data.get('flow_rate', 555.0),
                    'pump_speed': pump_data.get('speed_percent', 100.0),
                    'bearing_temperature': pump_data.get('bearing_temperature', 45.0),
                    'oil_level': pump_data.get('oil_level', 100.0),
                    'water_aggressiveness': water_quality_results.get('water_aggressiveness', 1.0),
                    'power_consumption': pump_data.get('power_consumption', 10.0)
                }
                
                wear_result = self.wear_tracking.update_wear_tracking(operating_conditions, dt)
                wear_results[pump_id] = wear_result
                total_wear_level += wear_result['total_wear']
                total_vibration += pump_data.get('vibration_level', 1.5)
            
            # Calculate averages
            avg_cavitation_risk = total_cavitation_risk / num_pumps
            avg_wear_level = total_wear_level / num_pumps
            avg_vibration = total_vibration / num_pumps
        else:
            avg_cavitation_risk = 0.0
            avg_wear_level = 0.0
            avg_vibration = 0.0
        
        # Calculate overall health score
        self._calculate_health_score(avg_cavitation_risk, avg_wear_level, avg_vibration)
        
        # Generate maintenance recommendations
        self._generate_maintenance_recommendations(cavitation_results, wear_results)
        
        # Update diagnostic history
        self.health_history.append(self.overall_health_score)
        if len(self.health_history) > 168:  # Keep one week of hourly data
            self.health_history.pop(0)
        
        return {
            'overall_health_factor': self.overall_health_score,
            'overall_cavitation_risk': avg_cavitation_risk,
            'overall_wear_level': avg_wear_level,
            'overall_vibration_level': avg_vibration,
            'overall_thermal_stress': 0.0,  # Placeholder for thermal stress
            'system_reliability': self.system_reliability,
            'maintenance_urgency': self.maintenance_urgency,
            'predicted_failure_time': self.predicted_failure_time,
            'maintenance_recommendation': self._get_primary_recommendation(),
            'cavitation_details': cavitation_results,
            'wear_details': wear_results
        }
    
    def _calculate_health_score(self, cavitation_risk, wear_level, vibration_level):
        """Calculate overall system health score"""
        # Individual health factors
        cavitation_health = max(0.0, 1.0 - cavitation_risk)
        wear_health = max(0.0, 1.0 - wear_level / 50.0)  # 50% wear = 0 health
        vibration_health = max(0.0, 1.0 - vibration_level / 10.0)  # 10 mm/s = 0 health
        performance_health = 1.0  # Placeholder for performance metrics
        
        # Weighted combination
        weights = self.config.health_score_weights
        self.overall_health_score = (
            cavitation_health * weights['cavitation'] +
            wear_health * weights['wear'] +
            vibration_health * weights['vibration'] +
            performance_health * weights['performance']
        )
        
        # Update system reliability
        self.system_reliability = self.overall_health_score
        
        # Calculate maintenance urgency
        self.maintenance_urgency = 1.0 - self.overall_health_score
    
    def _generate_maintenance_recommendations(self, cavitation_results, wear_results):
        """Generate maintenance recommendations"""
        self.maintenance_recommendations = []
        
        # Check cavitation issues
        for pump_id, cavitation_data in cavitation_results.items():
            if cavitation_data['cavitation_risk_score'] > 0.7:
                self.maintenance_recommendations.append(
                    f"{pump_id}: High cavitation risk - Check NPSH conditions"
                )
            elif cavitation_data['accumulated_damage'] > 5.0:
                self.maintenance_recommendations.append(
                    f"{pump_id}: Cavitation damage detected - Inspect impeller"
                )
        
        # Check wear issues
        for pump_id, wear_data in wear_results.items():
            if wear_data['impeller_wear'] > self.config.wear_tracking_config.impeller_wear_warning:
                self.maintenance_recommendations.append(
                    f"{pump_id}: Impeller wear warning - Schedule inspection"
                )
            if wear_data['bearing_wear'] > self.config.wear_tracking_config.bearing_wear_warning:
                self.maintenance_recommendations.append(
                    f"{pump_id}: Bearing wear warning - Check lubrication"
                )
            if wear_data['seal_wear'] > self.config.wear_tracking_config.seal_wear_warning:
                self.maintenance_recommendations.append(
                    f"{pump_id}: Seal wear warning - Monitor leakage"
                )
        
        # Overall system recommendations
        if self.overall_health_score < 0.7:
            self.maintenance_recommendations.append(
                "System health degraded - Schedule comprehensive maintenance"
            )
    
    def _get_primary_recommendation(self):
        """Get primary maintenance recommendation"""
        if not self.maintenance_recommendations:
            return "Normal"
        elif self.maintenance_urgency > 0.8:
            return "Urgent"
        elif self.maintenance_urgency > 0.5:
            return "Scheduled"
        else:
            return "Preventive"
    
    def perform_system_cleaning(self, **kwargs) -> Dict[str, float]:
        """Perform system cleaning maintenance"""
        cleaning_type = kwargs.get('cleaning_type', 'standard')
        
        results = {}
        
        if cleaning_type == 'cavitation_repair':
            # Reset cavitation damage
            self.cavitation_model.accumulated_damage *= 0.1
            self.cavitation_model.cavitation_events = []
            results['cavitation_repair'] = True
            
        elif cleaning_type == 'wear_maintenance':
            # Reduce wear levels
            self.wear_tracking.impeller_wear *= 0.8
            self.wear_tracking.bearing_wear *= 0.9
            self.wear_tracking.seal_wear *= 0.7
            self.wear_tracking.time_since_maintenance = 0.0
            self.wear_tracking.maintenance_effectiveness = 1.0
            results['wear_maintenance'] = True
            
        else:
            # General system cleaning
            self.cavitation_model.accumulated_damage *= 0.5
            self.wear_tracking.impeller_wear *= 0.9
            self.wear_tracking.bearing_wear *= 0.95
            self.wear_tracking.seal_wear *= 0.8
            self.wear_tracking.time_since_maintenance = 0.0
            results['system_cleaning'] = True
        
        # Reset health score
        self.overall_health_score = min(1.0, self.overall_health_score + 0.2)
        self.maintenance_recommendations = []
        
        return results
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            'diagnostics_health_score': self.overall_health_score,
            'diagnostics_reliability': self.system_reliability,
            'diagnostics_maintenance_urgency': self.maintenance_urgency,
            'diagnostics_cavitation_damage': self.cavitation_model.accumulated_damage,
            'diagnostics_total_wear': (self.wear_tracking.impeller_wear + 
                                     self.wear_tracking.bearing_wear + 
                                     self.wear_tracking.seal_wear),
            'diagnostics_time_since_maintenance': self.wear_tracking.time_since_maintenance
        }
    
    def reset(self):
        """Reset diagnostics to initial conditions"""
        self.cavitation_model = CavitationModel(self.config.cavitation_config)
        self.wear_tracking = WearTrackingModel(self.config.wear_tracking_config)
        self.overall_health_score = 1.0
        self.system_reliability = 1.0
        self.maintenance_urgency = 0.0
        self.health_history = []
        self.diagnostic_events = []
        self.predicted_failure_time = float('inf')
        self.maintenance_recommendations = []


# Example usage and testing
if __name__ == "__main__":
    print("Performance Monitoring and Diagnostics - Test")
    print("=" * 50)
    
    # Create diagnostics system
    config = PerformanceDiagnosticsConfig()
    diagnostics = PerformanceDiagnostics(config)
    
    print(f"Diagnostics System Configuration:")
    print(f"  Cavitation Monitoring: Enabled")
    print(f"  Wear Tracking: Enabled")
    print(f"  Predictive Maintenance: Enabled")
    print(f"  Health Score Weights: {config.health_score_weights}")
    print()
    
    # Test diagnostics operation
    print("Diagnostics Test:")
    print(f"{'Time':<6} {'Health':<8} {'Cavitation':<12} {'Wear':<8} {'Recommendation':<15}")
    print("-" * 60)
    
    # Simulate pump operation with degrading conditions
    for hour in range(48):  # 48 hours
        # Simulate pump results with gradual degradation
        pump_results = {
            'FWP-1': {
                'npsh_available': 20.0 - hour * 0.1,  # Gradually decreasing NPSH
                'flow_rate': 555.0,
                'speed_percent': 100.0,
                'bearing_temperature': 45.0 + hour * 0.2,  # Gradually increasing temperature
                'oil_level': 100.0 - hour * 0.5,  # Gradually decreasing oil level
                'power_consumption': 10.0,
                'vibration_level': 1.5 + hour * 0.05  # Gradually increasing vibration
            }
        }
        
        water_quality_results = {
            'water_aggressiveness': 1.0 + hour * 0.01  # Gradually increasing aggressiveness
        }
        
        system_conditions = {}
        
        result = diagnostics.update_diagnostics(
            pump_results=pump_results,
            water_quality_results=water_quality_results,
            system_conditions=system_conditions,
            dt=1.0
        )
        
        if hour % 8 == 0:  # Print every 8 hours
            print(f"{hour:<6} {result['overall_health_factor']:<8.3f} "
                  f"{result['overall_cavitation_risk']:<12.3f} "
                  f"{result['overall_wear_level']:<8.1f} "
                  f"{result['maintenance_recommendation']:<15}")
    
    print()
    print("Performance monitoring system ready for integration!")
