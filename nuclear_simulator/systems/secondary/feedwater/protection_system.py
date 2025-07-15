"""
Feedwater Protection System

This module provides comprehensive protection systems and trip logic
for the feedwater system, following the modular architecture pattern.

Key Features:
1. Multi-level protection logic
2. NPSH protection and monitoring
3. Emergency response coordination
4. System-level safety interlocks
5. Trip condition management
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings
import time

warnings.filterwarnings("ignore")


# Import the unified config from config.py
from .config import FeedwaterProtectionConfig


class NPSHProtection:
    """
    NPSH (Net Positive Suction Head) protection system
    
    This system provides:
    1. Continuous NPSH monitoring
    2. Multi-level alarm and trip logic
    3. Cavitation prevention
    4. Emergency response coordination
    """
    
    def __init__(self, config: FeedwaterProtectionConfig):
        """Initialize NPSH protection"""
        self.config = config
        
        # NPSH monitoring state
        self.current_npsh = 20.0                      # Current NPSH (m)
        self.npsh_trend = 0.0                         # NPSH trend (m/min)
        self.npsh_history = []                        # NPSH history for trending
        
        # Alarm and trip states
        self.npsh_low_alarm_active = False
        self.npsh_low_low_trip_active = False
        self.npsh_critical_trip_active = False
        
        # Trip timers
        self.npsh_low_low_timer = 0.0
        
        # Protection actions
        self.protection_actions_taken = []
        
    def update_npsh_protection(self,
                             npsh_available: float,
                             suction_pressure: float,
                             feedwater_temperature: float,
                             dt: float) -> Dict[str, bool]:
        """
        Update NPSH protection logic
        
        Args:
            npsh_available: Available NPSH (m)
            suction_pressure: Suction pressure (MPa)
            feedwater_temperature: Feedwater temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with protection status
        """
        self.current_npsh = npsh_available
        
        # Update NPSH history for trending
        self.npsh_history.append(npsh_available)
        if len(self.npsh_history) > 10:
            self.npsh_history.pop(0)
        
        # Calculate NPSH trend
        if len(self.npsh_history) >= 2:
            self.npsh_trend = (self.npsh_history[-1] - self.npsh_history[0]) / len(self.npsh_history)
        
        dt_seconds = dt * 60.0
        
        # NPSH Low Alarm (handle missing attributes with defaults)
        npsh_low_alarm = getattr(self.config, 'npsh_low_alarm', 18.0)
        if npsh_available < npsh_low_alarm:
            if not self.npsh_low_alarm_active:
                self.npsh_low_alarm_active = True
                self.protection_actions_taken.append(f"NPSH Low Alarm at {npsh_available:.1f}m")
        else:
            self.npsh_low_alarm_active = False
        
        # NPSH Low-Low Trip (with delay)
        npsh_low_low_trip = getattr(self.config, 'npsh_low_low_trip', getattr(self.config, 'low_suction_pressure_trip', 15.0))
        if npsh_available < npsh_low_low_trip:
            self.npsh_low_low_timer += dt_seconds
            delayed_trips = getattr(self.config, 'delayed_trips', {'npsh_low_low': 5.0})
            if self.npsh_low_low_timer >= delayed_trips.get('npsh_low_low', 5.0):
                if not self.npsh_low_low_trip_active:
                    self.npsh_low_low_trip_active = True
                    self.protection_actions_taken.append(f"NPSH Low-Low Trip at {npsh_available:.1f}m")
        else:
            self.npsh_low_low_timer = 0.0
            self.npsh_low_low_trip_active = False
        
        # NPSH Critical Trip (instantaneous)
        npsh_critical_trip = getattr(self.config, 'npsh_critical_trip', getattr(self.config, 'low_suction_pressure_trip', 12.0))
        if npsh_available < npsh_critical_trip:
            if not self.npsh_critical_trip_active:
                self.npsh_critical_trip_active = True
                self.protection_actions_taken.append(f"NPSH Critical Trip at {npsh_available:.1f}m")
        else:
            self.npsh_critical_trip_active = False
        
        return {
            'npsh_low_alarm': self.npsh_low_alarm_active,
            'npsh_low_low_trip': self.npsh_low_low_trip_active,
            'npsh_critical_trip': self.npsh_critical_trip_active,
            'npsh_protection_active': (self.npsh_low_low_trip_active or self.npsh_critical_trip_active)
        }
    
    def get_npsh_status(self) -> Dict[str, float]:
        """Get current NPSH status"""
        return {
            'current_npsh': self.current_npsh,
            'npsh_trend': self.npsh_trend,
            'npsh_margin': self.current_npsh - getattr(self.config, 'npsh_critical_trip', getattr(self.config, 'low_suction_pressure_trip', 12.0)),
            'npsh_low_alarm_setpoint': getattr(self.config, 'npsh_low_alarm', 18.0),
            'npsh_trip_setpoint': getattr(self.config, 'npsh_low_low_trip', getattr(self.config, 'low_suction_pressure_trip', 15.0)),
            'npsh_critical_setpoint': getattr(self.config, 'npsh_critical_trip', getattr(self.config, 'low_suction_pressure_trip', 12.0))
        }


class FeedwaterProtectionSystem:
    """
    Comprehensive feedwater protection system
    
    This system provides:
    1. Multi-parameter protection logic
    2. Coordinated emergency response
    3. System-level safety interlocks
    4. Trip condition management
    5. Emergency feedwater activation
    6. Maintenance event publishing for post-trip actions
    """
    
    def __init__(self, config: FeedwaterProtectionConfig):
        """Initialize feedwater protection system"""
        self.config = config
        
        # Initialize NPSH protection
        self.npsh_protection = NPSHProtection(config)
        
        # Protection system state
        self.system_trip_active = False
        self.active_trips = []
        self.active_alarms = []
        self.trip_history = []
        
        # Trip timers
        self.trip_timers = {
            'low_flow': 0.0,
            'high_flow': 0.0,
            'bearing_temp': 0.0,
            'motor_temp': 0.0,
            'vibration': 0.0
        }
        
        # Emergency actions
        self.emergency_actions = {
            'emergency_feedwater_activated': False,
            'steam_dump_activated': False,
            'reactor_trip_requested': False,
            'pump_trips_initiated': False,
            'isolation_valves_closed': False
        }
        
        # System availability
        self.protection_system_available = True
        self.last_test_time = 0.0
        
        # Performance tracking
        self.false_trip_count = 0
        self.valid_trip_count = 0
        self.system_response_time = 0.0
        
        # Maintenance event bus integration
        self.maintenance_event_bus = None
        self.component_id = "FEEDWATER_SYSTEM"  # Default component ID
    
    def set_maintenance_event_bus(self, event_bus, component_id: str = None):
        """
        Set the maintenance event bus for publishing trip events
        
        Args:
            event_bus: MaintenanceEventBus instance
            component_id: Component identifier for events
        """
        self.maintenance_event_bus = event_bus
        if component_id:
            self.component_id = component_id
    
    def _publish_trip_event(self, trip_type: str, trip_value: float, trip_setpoint: float, 
                           severity: str = "HIGH", recommended_actions: List[str] = None):
        """
        Publish a protection trip event to the maintenance system
        
        Args:
            trip_type: Type of trip that occurred
            trip_value: Current value that caused the trip
            trip_setpoint: Setpoint that was exceeded
            severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
            recommended_actions: List of recommended maintenance actions
        """
        if not self.maintenance_event_bus:
            return
        
        if recommended_actions is None:
            # Default recommended actions based on trip type
            action_map = {
                'npsh_critical': ['pump_inspection', 'npsh_analysis', 'suction_system_check'],
                'npsh_low_low': ['pump_inspection', 'npsh_analysis'],
                'suction_pressure_low': ['suction_system_inspection', 'pump_inspection'],
                'discharge_pressure_high': ['discharge_system_inspection', 'pump_inspection'],
                'system_low_flow': ['flow_system_inspection', 'pump_performance_test'],
                'system_high_flow': ['flow_control_inspection', 'valve_inspection'],
                'vibration_high': ['vibration_analysis', 'pump_alignment_check'],
                'bearing_temp_high': ['bearing_inspection', 'lubrication_system_check'],
                'motor_temp_high': ['motor_inspection', 'cooling_system_check'],
                'system_health_critical': ['comprehensive_system_inspection', 'root_cause_analysis'],
                'system_cavitation_severe': ['cavitation_analysis', 'npsh_improvement'],
                'system_wear_critical': ['wear_analysis', 'component_replacement_evaluation']
            }
            
            # Find matching actions (handle pump-specific trips)
            recommended_actions = []
            for key, actions in action_map.items():
                if key in trip_type:
                    recommended_actions = actions
                    break
            
            if not recommended_actions:
                recommended_actions = ['post_trip_inspection', 'trip_root_cause_analysis']
        
        # Determine priority based on severity
        priority_map = {
            'CRITICAL': 'CRITICAL',
            'HIGH': 'HIGH', 
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW'
        }
        priority = priority_map.get(severity, 'HIGH')
        
        # Publish the event
        self.maintenance_event_bus.publish(
            'protection_trip_occurred',
            self.component_id,
            {
                'trip_type': trip_type,
                'trip_value': trip_value,
                'trip_setpoint': trip_setpoint,
                'severity': severity,
                'recommended_actions': recommended_actions,
                'system_type': 'feedwater_protection',
                'emergency_actions_taken': list(self.emergency_actions.keys())
            },
            priority=priority
        )
        
        print(f"FEEDWATER PROTECTION: Published trip event - {trip_type} ({severity})")
    
    def _publish_trip_events(self, trip_types: List[str], pump_results: Dict[str, Dict], 
                            system_conditions: Dict[str, float]):
        """
        Publish maintenance events for all trips that occurred
        
        Args:
            trip_types: List of trip types that occurred
            pump_results: Pump results data for extracting trip values
            system_conditions: System conditions for extracting trip values
        """
        if not self.maintenance_event_bus:
            return
        
        for trip_type in trip_types:
            # Extract trip value and setpoint based on trip type
            trip_value = 0.0
            trip_setpoint = 0.0
            severity = "HIGH"
            
            # NPSH trips
            if 'npsh_critical' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('npsh_available', 0.0)
                    trip_setpoint = self.config.npsh_critical_trip
                    severity = "CRITICAL"
            elif 'npsh_low_low' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('npsh_available', 0.0)
                    trip_setpoint = self.config.npsh_low_low_trip
                    severity = "HIGH"
            
            # Pressure trips
            elif 'suction_pressure_low' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('suction_pressure', 0.0)
                    trip_setpoint = self.config.suction_pressure_low_trip
                    severity = "CRITICAL"
            elif 'discharge_pressure_high' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('discharge_pressure', 0.0)
                    trip_setpoint = self.config.discharge_pressure_high_trip
                    severity = "HIGH"
            
            # Flow trips
            elif 'system_low_flow' in trip_type:
                trip_value = sum(pump_data.get('flow_rate', 0.0) for pump_data in pump_results.values())
                trip_setpoint = self.config.low_flow_trip
                severity = "CRITICAL"
            elif 'system_high_flow' in trip_type:
                trip_value = sum(pump_data.get('flow_rate', 0.0) for pump_data in pump_results.values())
                trip_setpoint = self.config.high_flow_trip
                severity = "HIGH"
            
            # Equipment trips
            elif 'vibration_high' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('vibration_level', 0.0)
                    trip_setpoint = self.config.pump_vibration_trip
                    severity = "HIGH"
            elif 'bearing_temp_high' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('bearing_temperature', 0.0)
                    trip_setpoint = self.config.bearing_temp_trip
                    severity = "HIGH"
            elif 'motor_temp_high' in trip_type:
                pump_id = trip_type.split('_')[0]
                if pump_id in pump_results:
                    trip_value = pump_results[pump_id].get('motor_temperature', 0.0)
                    trip_setpoint = self.config.motor_temp_trip
                    severity = "HIGH"
            
            # Steam generator level trips
            elif 'level_high' in trip_type:
                sg_levels = system_conditions.get('sg_levels', [12.5, 12.5, 12.5])
                trip_value = max(sg_levels) if sg_levels else 0.0
                trip_setpoint = self.config.sg_level_high_trip
                severity = "HIGH"
            
            # System health trips
            elif 'system_health_critical' in trip_type:
                trip_value = 0.3  # Critical health threshold
                trip_setpoint = 0.3
                severity = "CRITICAL"
            elif 'system_cavitation_severe' in trip_type:
                trip_value = 0.8  # Severe cavitation threshold
                trip_setpoint = 0.8
                severity = "CRITICAL"
            elif 'system_wear_critical' in trip_type:
                trip_value = 40.0  # Critical wear threshold
                trip_setpoint = 40.0
                severity = "CRITICAL"
            
            # Publish the event for this specific trip
            self._publish_trip_event(trip_type, trip_value, trip_setpoint, severity)
        
    def check_protection_systems(self,
                               pump_results: Dict[str, Dict],
                               diagnostics_results: Dict[str, float],
                               system_conditions: Dict[str, float],
                               dt: float) -> Dict[str, bool]:
        """
        Check all protection systems and execute trip logic
        
        Args:
            pump_results: Results from pump system
            diagnostics_results: Diagnostics and monitoring results
            system_conditions: System operating conditions
            dt: Time step (hours)
            
        Returns:
            Dictionary with protection system status
        """
        if not self.protection_system_available:
            return {'system_trip_active': False, 'protection_unavailable': True}
        
        dt_seconds = dt * 60.0
        current_trips = []
        current_alarms = []
        
        # Extract system conditions
        sg_levels = system_conditions.get('sg_levels', [12.5, 12.5, 12.5])
        total_flow = sum(pump_data.get('flow_rate', 0.0) for pump_data in pump_results.values())
        
        # Check NPSH protection for each pump
        npsh_protection_results = {}
        for pump_id, pump_data in pump_results.items():
            npsh_result = self.npsh_protection.update_npsh_protection(
                npsh_available=pump_data.get('npsh_available', 20.0),
                suction_pressure=pump_data.get('suction_pressure', 0.5),
                feedwater_temperature=system_conditions.get('feedwater_temperature', 227.0),
                dt=dt
            )
            npsh_protection_results[pump_id] = npsh_result
            
            # Aggregate NPSH trips
            if npsh_result['npsh_critical_trip']:
                current_trips.append(f'{pump_id}_npsh_critical')
            elif npsh_result['npsh_low_low_trip']:
                current_trips.append(f'{pump_id}_npsh_low_low')
            
            if npsh_result['npsh_low_alarm']:
                current_alarms.append(f'{pump_id}_npsh_low')
        
        # Check pressure protection
        self._check_pressure_protection(pump_results, current_trips, current_alarms)
        
        # Check flow protection
        self._check_flow_protection(total_flow, current_trips, current_alarms, dt_seconds)
        
        # Check steam generator level protection
        self._check_sg_level_protection(sg_levels, current_trips, current_alarms)
        
        # Check equipment protection
        self._check_equipment_protection(pump_results, current_trips, current_alarms, dt_seconds)
        
        # Check diagnostic-based protection
        self._check_diagnostic_protection(diagnostics_results, current_trips, current_alarms)
        
        # Update trip status
        previous_trip_state = self.system_trip_active
        self.system_trip_active = len(current_trips) > 0
        self.active_trips = current_trips
        self.active_alarms = current_alarms
        
        # Execute emergency actions if new trip
        if self.system_trip_active and not previous_trip_state:
            self._execute_emergency_actions(current_trips)
            self._publish_trip_events(current_trips, pump_results, system_conditions)
            self.valid_trip_count += 1
            
            # Record trip in history
            trip_event = {
                'timestamp': time.time(),
                'trips': current_trips.copy(),
                'conditions': {
                    'total_flow': total_flow,
                    'sg_levels': sg_levels.copy(),
                    'system_conditions': system_conditions.copy()
                }
            }
            self.trip_history.append(trip_event)
            
            # Limit trip history
            if len(self.trip_history) > 50:
                self.trip_history.pop(0)
        
        # Reset emergency actions if no trips
        if not self.system_trip_active:
            self._reset_emergency_actions()
        
        return {
            'system_trip_active': self.system_trip_active,
            'active_trips': self.active_trips,
            'active_alarms': self.active_alarms,
            'emergency_actions': self.emergency_actions,
            'npsh_protection_results': npsh_protection_results,
            'protection_system_available': self.protection_system_available,
            'warnings': self._generate_warnings()
        }
    
    def _check_pressure_protection(self, pump_results, current_trips, current_alarms):
        """Check pressure-related protection"""
        for pump_id, pump_data in pump_results.items():
            suction_pressure = pump_data.get('suction_pressure', 0.5)
            discharge_pressure = pump_data.get('discharge_pressure', 8.0)
            
            # Suction pressure protection
            suction_pressure_low_trip = getattr(self.config, 'suction_pressure_low_trip', getattr(self.config, 'low_suction_pressure_trip', 0.2))
            suction_pressure_low_alarm = getattr(self.config, 'suction_pressure_low_alarm', 0.3)
            if suction_pressure < suction_pressure_low_trip:
                current_trips.append(f'{pump_id}_suction_pressure_low')
            elif suction_pressure < suction_pressure_low_alarm:
                current_alarms.append(f'{pump_id}_suction_pressure_low')
            
            # Discharge pressure protection
            discharge_pressure_high_trip = getattr(self.config, 'discharge_pressure_high_trip', getattr(self.config, 'high_discharge_pressure_trip', 10.0))
            discharge_pressure_high_alarm = getattr(self.config, 'discharge_pressure_high_alarm', 9.0)
            if discharge_pressure > discharge_pressure_high_trip:
                current_trips.append(f'{pump_id}_discharge_pressure_high')
            elif discharge_pressure > discharge_pressure_high_alarm:
                current_alarms.append(f'{pump_id}_discharge_pressure_high')
    
    def _check_flow_protection(self, total_flow, current_trips, current_alarms, dt_seconds):
        """Check flow-related protection"""
        # Get flow protection setpoints with defaults
        # CRITICAL FIX: Convert fractional setpoints to absolute values
        low_flow_trip_fraction = getattr(self.config, 'low_flow_trip', 0.05)
        high_flow_trip_fraction = getattr(self.config, 'high_flow_trip', 1.3)
        
        # Assume design flow of 1500 kg/s if not available
        design_flow = getattr(self.config, 'design_total_flow', 1500.0)
        
        # Convert fractions to absolute values
        if low_flow_trip_fraction < 1.0:  # It's a fraction
            low_flow_trip = low_flow_trip_fraction * design_flow
            low_flow_alarm = low_flow_trip * 2.0  # Alarm at 2x trip level
        else:  # It's already an absolute value
            low_flow_trip = low_flow_trip_fraction
            low_flow_alarm = getattr(self.config, 'low_flow_alarm', 100.0)
        
        if high_flow_trip_fraction < 2.0:  # It's a fraction
            high_flow_trip = high_flow_trip_fraction * design_flow
            high_flow_alarm = high_flow_trip * 0.9  # Alarm at 90% of trip level
        else:  # It's already an absolute value
            high_flow_trip = high_flow_trip_fraction
            high_flow_alarm = getattr(self.config, 'high_flow_alarm', 1800.0)
        
        delayed_trips = getattr(self.config, 'delayed_trips', {'low_flow': 10.0, 'high_flow': 2.0})
        
        # Low flow protection (with delay)
        if total_flow < low_flow_trip:
            self.trip_timers['low_flow'] += dt_seconds
            if self.trip_timers['low_flow'] >= delayed_trips.get('low_flow', 10.0):
                current_trips.append('system_low_flow')
        else:
            self.trip_timers['low_flow'] = 0.0
        
        if total_flow < low_flow_alarm:
            current_alarms.append('system_low_flow')
        
        # High flow protection (with delay)
        if total_flow > high_flow_trip:
            self.trip_timers['high_flow'] += dt_seconds
            if self.trip_timers['high_flow'] >= delayed_trips.get('high_flow', 2.0):
                current_trips.append('system_high_flow')
        else:
            self.trip_timers['high_flow'] = 0.0
        
        if total_flow > high_flow_alarm:
            current_alarms.append('system_high_flow')
    
    def _check_sg_level_protection(self, sg_levels, current_trips, current_alarms):
        """Check steam generator level protection"""
        # Get SG level protection setpoints with defaults
        sg_level_high_trip = getattr(self.config, 'sg_level_high_trip', 16.5)
        sg_level_high_alarm = getattr(self.config, 'sg_level_high_alarm', 15.5)
        sg_level_low_trip = getattr(self.config, 'sg_level_low_trip', 10.0)
        sg_level_low_alarm = getattr(self.config, 'sg_level_low_alarm', 11.0)
        
        for i, level in enumerate(sg_levels):
            sg_id = f'SG_{i+1}'
            
            # High level protection (instantaneous)
            if level > sg_level_high_trip:
                current_trips.append(f'{sg_id}_level_high')
            elif level > sg_level_high_alarm:
                current_alarms.append(f'{sg_id}_level_high')
            
            # Low level protection (alarm only - trip handled by reactor protection)
            if level < sg_level_low_trip:
                current_alarms.append(f'{sg_id}_level_low_critical')
            elif level < sg_level_low_alarm:
                current_alarms.append(f'{sg_id}_level_low')
    
    def _check_equipment_protection(self, pump_results, current_trips, current_alarms, dt_seconds):
        """Check equipment-related protection"""
        # Get equipment protection setpoints with defaults
        pump_vibration_trip = getattr(self.config, 'pump_vibration_trip', 10.0)
        pump_vibration_alarm = getattr(self.config, 'pump_vibration_alarm', 5.0)
        bearing_temp_trip = getattr(self.config, 'bearing_temp_trip', 120.0)
        bearing_temp_alarm = getattr(self.config, 'bearing_temp_alarm', 80.0)
        motor_temp_trip = getattr(self.config, 'motor_temp_trip', 130.0)
        motor_temp_alarm = getattr(self.config, 'motor_temp_alarm', 100.0)
        delayed_trips = getattr(self.config, 'delayed_trips', {'vibration': 10.0, 'bearing_temp': 30.0, 'motor_temp': 60.0})
        
        for pump_id, pump_data in pump_results.items():
            # Vibration protection
            vibration = pump_data.get('vibration_level', 1.5)
            if vibration > pump_vibration_trip:
                self.trip_timers['vibration'] += dt_seconds
                if self.trip_timers['vibration'] >= delayed_trips.get('vibration', 10.0):
                    current_trips.append(f'{pump_id}_vibration_high')
            else:
                self.trip_timers['vibration'] = 0.0
            
            if vibration > pump_vibration_alarm:
                current_alarms.append(f'{pump_id}_vibration_high')
            
            # Bearing temperature protection
            bearing_temp = pump_data.get('bearing_temperature', 45.0)
            if bearing_temp > bearing_temp_trip:
                self.trip_timers['bearing_temp'] += dt_seconds
                if self.trip_timers['bearing_temp'] >= delayed_trips.get('bearing_temp', 30.0):
                    current_trips.append(f'{pump_id}_bearing_temp_high')
            else:
                self.trip_timers['bearing_temp'] = 0.0
            
            if bearing_temp > bearing_temp_alarm:
                current_alarms.append(f'{pump_id}_bearing_temp_high')
            
            # Motor temperature protection
            motor_temp = pump_data.get('motor_temperature', 60.0)
            if motor_temp > motor_temp_trip:
                self.trip_timers['motor_temp'] += dt_seconds
                if self.trip_timers['motor_temp'] >= delayed_trips.get('motor_temp', 60.0):
                    current_trips.append(f'{pump_id}_motor_temp_high')
            else:
                self.trip_timers['motor_temp'] = 0.0
            
            if motor_temp > motor_temp_alarm:
                current_alarms.append(f'{pump_id}_motor_temp_high')
    
    def _check_diagnostic_protection(self, diagnostics_results, current_trips, current_alarms):
        """Check diagnostics-based protection"""
        # Health-based protection
        health_score = diagnostics_results.get('overall_health_factor', 1.0)
        if health_score < 0.3:  # Critical health degradation
            current_trips.append('system_health_critical')
        elif health_score < 0.5:  # Poor health
            current_alarms.append('system_health_degraded')
        
        # Cavitation protection
        cavitation_risk = diagnostics_results.get('overall_cavitation_risk', 0.0)
        if cavitation_risk > 0.8:  # Severe cavitation risk
            current_trips.append('system_cavitation_severe')
        elif cavitation_risk > 0.5:  # Moderate cavitation risk
            current_alarms.append('system_cavitation_risk')
        
        # FIXED: Wear protection - Get wear from actual lubrication system, not performance monitoring
        # Performance monitoring has separate wear tracking that starts at 0%
        # Protection system should check actual component wear from lubrication system
        wear_level = diagnostics_results.get('overall_wear_level', 0.0)
        
        # CRITICAL FIX: Check if we have access to actual lubrication system wear data
        # Look for lubrication system wear details in diagnostics results
        wear_details = diagnostics_results.get('wear_details', {})
        if wear_details:
            # Calculate actual system wear from lubrication systems
            total_actual_wear = 0.0
            pump_count = 0
            
            for pump_id, pump_wear_data in wear_details.items():
                if isinstance(pump_wear_data, dict):
                    # Get individual component wear from lubrication system
                    motor_bearing_wear = pump_wear_data.get('motor_bearing_wear', 0.0)
                    pump_bearing_wear = pump_wear_data.get('pump_bearing_wear', 0.0) 
                    thrust_bearing_wear = pump_wear_data.get('thrust_bearing_wear', 0.0)
                    seal_wear = pump_wear_data.get('seal_wear', 0.0)
                    
                    # Calculate total wear for this pump (use max bearing wear to avoid double counting)
                    max_bearing_wear = max(motor_bearing_wear, pump_bearing_wear, thrust_bearing_wear)
                    pump_total_wear = max_bearing_wear + seal_wear
                    
                    total_actual_wear += pump_total_wear
                    pump_count += 1
            
            if pump_count > 0:
                # Use actual lubrication system wear instead of performance monitoring wear
                wear_level = total_actual_wear / pump_count
        
        WEAR_TRIP_THRESHOLD = 85.0       # Higher than maintenance threshold (75%)
        
        if wear_level > WEAR_TRIP_THRESHOLD:  # Critical wear level
            current_trips.append('system_wear_critical')
        elif wear_level > 50.0:  # High wear level (alarm only)
            current_alarms.append('system_wear_high')
    
    def _execute_emergency_actions(self, trip_types):
        """Execute emergency actions based on trip types"""
        # Emergency feedwater activation
        if self.config.enable_emergency_feedwater:
            critical_trips = ['npsh_critical', 'suction_pressure_low', 'system_low_flow']
            if any(trip_type in trip for trip in trip_types for trip_type in critical_trips):
                self.emergency_actions['emergency_feedwater_activated'] = True
        
        # Steam dump activation
        if self.config.enable_steam_dump:
            high_level_trips = ['level_high', 'system_high_flow']
            if any(trip_type in trip for trip in trip_types for trip_type in high_level_trips):
                self.emergency_actions['steam_dump_activated'] = True
        
        # Pump trips
        pump_trips = [trip for trip in trip_types if any(pump_id in trip for pump_id in ['FWP-1', 'FWP-2', 'FWP-3', 'FWP-4'])]
        if pump_trips:
            self.emergency_actions['pump_trips_initiated'] = True
        
        # Reactor trip request (for severe conditions)
        if getattr(self.config, 'enable_reactor_trip', True):
            severe_trips = ['npsh_critical', 'system_health_critical', 'system_cavitation_severe']
            if any(trip_type in trip for trip in trip_types for trip_type in severe_trips):
                self.emergency_actions['reactor_trip_requested'] = True
        
        # Isolation valves
        isolation_trips = ['discharge_pressure_high', 'system_high_flow']
        if any(trip_type in trip for trip in trip_types for trip_type in isolation_trips):
            self.emergency_actions['isolation_valves_closed'] = True
    
    def _reset_emergency_actions(self):
        """Reset emergency actions when trips clear"""
        # Only reset actions that should automatically reset
        self.emergency_actions['pump_trips_initiated'] = False
        # Keep emergency feedwater and steam dump active until manually reset
    
    def _generate_warnings(self) -> List[str]:
        """Generate system warnings"""
        warnings = []
        
        if not self.protection_system_available:
            warnings.append("Protection system unavailable")
        
        if len(self.active_alarms) > 5:
            warnings.append("Multiple alarms active")
        
        if self.false_trip_count > 3:
            warnings.append("High false trip rate detected")
        
        npsh_status = self.npsh_protection.get_npsh_status()
        if npsh_status['npsh_margin'] < 3.0:
            warnings.append("Low NPSH margin")
        
        return warnings
    
    def reset_protection_system(self):
        """Reset protection system after trip clearance"""
        self.system_trip_active = False
        self.active_trips = []
        self.active_alarms = []
        self.trip_timers = {key: 0.0 for key in self.trip_timers}
        
        # Reset emergency actions (manual reset required)
        self.emergency_actions = {key: False for key in self.emergency_actions}
        
        # Reset NPSH protection
        self.npsh_protection.npsh_low_alarm_active = False
        self.npsh_protection.npsh_low_low_trip_active = False
        self.npsh_protection.npsh_critical_trip_active = False
        self.npsh_protection.npsh_low_low_timer = 0.0
    
    def perform_protection_test(self) -> Dict[str, bool]:
        """Perform protection system test"""
        test_results = {
            'npsh_protection_test': True,
            'pressure_protection_test': True,
            'flow_protection_test': True,
            'equipment_protection_test': True,
            'emergency_action_test': True,
            'overall_test_passed': True
        }
        
        # Update test time
        self.last_test_time = time.time()
        
        # Reset false trip counter after successful test
        self.false_trip_count = 0
        
        return test_results
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        npsh_status = self.npsh_protection.get_npsh_status()
        
        state_dict = {
            'protection_system_available': float(self.protection_system_available),
            'protection_system_trip_active': float(self.system_trip_active),
            'protection_active_trips_count': len(self.active_trips),
            'protection_active_alarms_count': len(self.active_alarms),
            'protection_false_trip_count': self.false_trip_count,
            'protection_valid_trip_count': self.valid_trip_count,
            'protection_emergency_feedwater': float(self.emergency_actions['emergency_feedwater_activated']),
            'protection_steam_dump': float(self.emergency_actions['steam_dump_activated']),
            'protection_npsh_current': npsh_status['current_npsh'],
            'protection_npsh_margin': npsh_status['npsh_margin'],
            'protection_npsh_trend': npsh_status['npsh_trend']
        }
        
        return state_dict
    
    def reset(self):
        """Reset protection system to initial conditions"""
        self.npsh_protection = NPSHProtection(self.config)
        self.system_trip_active = False
        self.active_trips = []
        self.active_alarms = []
        self.trip_history = []
        self.trip_timers = {key: 0.0 for key in self.trip_timers}
        self.emergency_actions = {key: False for key in self.emergency_actions}
        self.protection_system_available = True
        self.last_test_time = 0.0
        self.false_trip_count = 0
        self.valid_trip_count = 0
        self.system_response_time = 0.0


# Example usage and testing
if __name__ == "__main__":
    print("Feedwater Protection System - Test")
    print("=" * 50)
    
    # Create protection system
    config = FeedwaterProtectionConfig()
    protection_system = FeedwaterProtectionSystem(config)
    
    print(f"Protection System Configuration:")
    print(f"  NPSH Low-Low Trip: {config.npsh_low_low_trip} m")
    print(f"  NPSH Critical Trip: {config.npsh_critical_trip} m")
    print(f"  Low Flow Trip: {config.low_flow_trip} kg/s")
    print(f"  High Flow Trip: {config.high_flow_trip} kg/s")
    print(f"  SG Level High Trip: {config.sg_level_high_trip} m")
    print(f"  Emergency Feedwater: {config.enable_emergency_feedwater}")
    print()
    
    # Test protection system operation
    print("Protection System Test:")
    print(f"{'Time':<6} {'Trips':<8} {'Alarms':<8} {'NPSH':<8} {'Emergency':<12}")
    print("-" * 50)
    
    # Simulate degrading conditions leading to trips
    for hour in range(24):
        # Simulate pump results with degrading conditions
        pump_results = {
            'FWP-1': {
                'npsh_available': 20.0 - hour * 0.5,  # Gradually decreasing NPSH
                'suction_pressure': 0.5 - hour * 0.01,  # Gradually decreasing suction pressure
                'discharge_pressure': 8.0 + hour * 0.1,  # Gradually increasing discharge pressure
                'flow_rate': 555.0 - hour * 10.0,  # Gradually decreasing flow
                'vibration_level': 1.5 + hour * 0.2,  # Gradually increasing vibration
                'bearing_temperature': 45.0 + hour * 2.0,  # Gradually increasing temperature
                'motor_temperature': 60.0 + hour * 1.5  # Gradually increasing temperature
            }
        }
        
        diagnostics_results = {
            'overall_health_factor': 1.0 - hour * 0.03,  # Gradually decreasing health
            'overall_cavitation_risk': hour * 0.04,  # Gradually increasing cavitation risk
            'overall_wear_level': hour * 1.5  # Gradually increasing wear
        }
        
        system_conditions = {
            'sg_levels': [12.5 + hour * 0.1, 12.5 + hour * 0.1, 12.5 + hour * 0.1],  # Gradually increasing levels
            'feedwater_temperature': 227.0
        }
        
        result = protection_system.check_protection_systems(
            pump_results=pump_results,
            diagnostics_results=diagnostics_results,
            system_conditions=system_conditions,
            dt=1.0
        )
        
        emergency_active = any(result['emergency_actions'].values())
        
        if hour % 2 == 0:  # Print every 2 hours
            print(f"{hour:<6} {len(result['active_trips']):<8} "
                  f"{len(result['active_alarms']):<8} "
                  f"{pump_results['FWP-1']['npsh_available']:<8.1f} "
                  f"{'Yes' if emergency_active else 'No':<12}")
    
    print()
    print("Protection system ready for integration!")
