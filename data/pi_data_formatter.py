"""
PI Data Formatter

Converts nuclear plant simulation data to industry-standard PI (Plant Information) format
used in real power plants. This module provides PI tag naming conventions, data quality
indicators, and export formats that match what operators see in control rooms.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import json
import warnings


class PIDataQuality(Enum):
    """PI Data Quality indicators matching OSIsoft PI standards"""
    GOOD = "Good"
    BAD = "Bad" 
    UNCERTAIN = "Uncertain"
    QUESTIONABLE = "Questionable"
    SUBSTITUTED = "Substituted"


class PIAlarmState(Enum):
    """PI Alarm states for process variables"""
    NORMAL = "Normal"
    WARNING = "Warning"
    ALARM = "Alarm"
    CRITICAL = "Critical"
    ACKNOWLEDGED = "Acknowledged"


class PITagConfig:
    """Configuration for a PI tag including metadata and limits"""
    
    def __init__(self, tag_name: str, description: str, units: str, 
                 data_type: str = "Float32", 
                 low_limit: Optional[float] = None,
                 high_limit: Optional[float] = None,
                 warning_low: Optional[float] = None,
                 warning_high: Optional[float] = None,
                 alarm_low: Optional[float] = None,
                 alarm_high: Optional[float] = None,
                 system: str = "NUCLEAR",
                 subsystem: str = "GENERAL"):
        self.tag_name = tag_name
        self.description = description
        self.units = units
        self.data_type = data_type
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.warning_low = warning_low
        self.warning_high = warning_high
        self.alarm_low = alarm_low
        self.alarm_high = alarm_high
        self.system = system
        self.subsystem = subsystem


class PIDataFormatter:
    """
    Converts nuclear plant simulation data to PI format with industry-standard
    tag naming conventions and data quality indicators.
    """
    
    def __init__(self, plant_code: str = "NPP", unit_number: int = 1):
        """
        Initialize PI data formatter.
        
        Args:
            plant_code: Plant identifier code (e.g., "NPP", "PWR1")
            unit_number: Unit number for multi-unit plants
        """
        self.plant_code = plant_code
        self.unit_number = unit_number
        self.tag_configs = {}
        self.tag_mapping = {}
        
        # Initialize standard power plant PI tag configurations
        self._initialize_standard_tags()
    
    def _initialize_standard_tags(self):
        """Initialize standard PI tags for nuclear power plant systems"""
        
        # Reactor System Tags
        reactor_tags = [
            PITagConfig(f"{self.plant_code}_RX_PWR_THRM", "Reactor Thermal Power", "MW", 
                       low_limit=0, high_limit=3500, warning_high=3200, alarm_high=3300,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_PWR_ELEC", "Reactor Electrical Power", "MWe",
                       low_limit=0, high_limit=1200, warning_high=1100, alarm_high=1150,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_TEMP_FUEL", "Reactor Fuel Temperature", "°C",
                       low_limit=200, high_limit=800, warning_high=650, alarm_high=700,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_TEMP_COOL", "Reactor Coolant Temperature", "°C",
                       low_limit=250, high_limit=350, warning_high=330, alarm_high=340,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_PRESS_COOL", "Reactor Coolant Pressure", "MPa",
                       low_limit=10, high_limit=18, warning_low=14, alarm_low=13,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_FLOW_COOL", "Reactor Coolant Flow", "kg/s",
                       low_limit=15000, high_limit=25000, warning_low=17000, alarm_low=16000,
                       system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_ROD_POS", "Control Rod Position", "%",
                       low_limit=0, high_limit=100, system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_FLUX_NEUT", "Neutron Flux", "n/cm²/s",
                       low_limit=1e10, high_limit=1e15, system="PRIMARY", subsystem="REACTOR"),
            PITagConfig(f"{self.plant_code}_RX_REACT_TOT", "Total Reactivity", "pcm",
                       low_limit=-5000, high_limit=5000, system="PRIMARY", subsystem="REACTOR"),
        ]
        
        # Steam Generator Tags (3 steam generators)
        sg_tags = []
        for i in range(1, 4):
            sg_tags.extend([
                PITagConfig(f"{self.plant_code}_SG{i:02d}_PRESS_PRI", f"SG-{i} Primary Pressure", "MPa",
                           low_limit=10, high_limit=18, system="PRIMARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_PRESS_SEC", f"SG-{i} Secondary Pressure", "MPa",
                           low_limit=5, high_limit=8, system="SECONDARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_TEMP_PRI_IN", f"SG-{i} Primary Inlet Temp", "°C",
                           low_limit=280, high_limit=330, system="PRIMARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_TEMP_PRI_OUT", f"SG-{i} Primary Outlet Temp", "°C",
                           low_limit=250, high_limit=300, system="PRIMARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_TEMP_SEC", f"SG-{i} Secondary Steam Temp", "°C",
                           low_limit=250, high_limit=300, system="SECONDARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_FLOW_STM", f"SG-{i} Steam Flow", "kg/s",
                           low_limit=0, high_limit=800, system="SECONDARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_FLOW_FW", f"SG-{i} Feedwater Flow", "kg/s",
                           low_limit=0, high_limit=800, system="SECONDARY", subsystem="STEAM_GEN"),
                PITagConfig(f"{self.plant_code}_SG{i:02d}_LVL_WTR", f"SG-{i} Water Level", "%",
                           low_limit=0, high_limit=100, warning_low=20, alarm_low=15,
                           system="SECONDARY", subsystem="STEAM_GEN"),
            ])
        
        # Turbine System Tags
        turbine_tags = [
            PITagConfig(f"{self.plant_code}_TB_PWR_ELEC", "Turbine Electrical Power", "MWe",
                       low_limit=0, high_limit=1200, system="SECONDARY", subsystem="TURBINE"),
            PITagConfig(f"{self.plant_code}_TB_SPEED", "Turbine Speed", "rpm",
                       low_limit=0, high_limit=1900, warning_high=1850, alarm_high=1880,
                       system="SECONDARY", subsystem="TURBINE"),
            PITagConfig(f"{self.plant_code}_TB_PRESS_HP_IN", "HP Turbine Inlet Pressure", "MPa",
                       low_limit=5, high_limit=8, system="SECONDARY", subsystem="TURBINE"),
            PITagConfig(f"{self.plant_code}_TB_PRESS_LP_OUT", "LP Turbine Outlet Pressure", "kPa",
                       low_limit=5, high_limit=15, system="SECONDARY", subsystem="TURBINE"),
            PITagConfig(f"{self.plant_code}_TB_TEMP_HP_IN", "HP Turbine Inlet Temperature", "°C",
                       low_limit=250, high_limit=300, system="SECONDARY", subsystem="TURBINE"),
            PITagConfig(f"{self.plant_code}_TB_EFF_THRM", "Turbine Thermal Efficiency", "%",
                       low_limit=25, high_limit=40, system="SECONDARY", subsystem="TURBINE"),
        ]
        
        # Feedwater System Tags
        feedwater_tags = [
            PITagConfig(f"{self.plant_code}_FW_FLOW_TOT", "Total Feedwater Flow", "kg/s",
                       low_limit=1000, high_limit=2500, warning_low=1200, alarm_low=1100,
                       system="SECONDARY", subsystem="FEEDWATER"),
            PITagConfig(f"{self.plant_code}_FW_PRESS_DISCH", "Feedwater Discharge Pressure", "MPa",
                       low_limit=8, high_limit=12, system="SECONDARY", subsystem="FEEDWATER"),
            PITagConfig(f"{self.plant_code}_FW_TEMP", "Feedwater Temperature", "°C",
                       low_limit=180, high_limit=230, system="SECONDARY", subsystem="FEEDWATER"),
            PITagConfig(f"{self.plant_code}_FW_PH", "Feedwater pH", "pH",
                       low_limit=8.5, high_limit=9.5, warning_low=8.8, warning_high=9.2,
                       system="SECONDARY", subsystem="FEEDWATER"),
            PITagConfig(f"{self.plant_code}_FW_O2_DISS", "Feedwater Dissolved Oxygen", "ppb",
                       low_limit=0, high_limit=10, warning_high=5, alarm_high=8,
                       system="SECONDARY", subsystem="FEEDWATER"),
        ]
        
        # Feedwater Pump Tags (3 pumps)
        pump_tags = []
        for i in range(1, 4):
            pump_tags.extend([
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_FLOW", f"Feedwater Pump {i} Flow", "kg/s",
                           low_limit=0, high_limit=1000, system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_PRESS_DISCH", f"FW Pump {i} Discharge Pressure", "MPa",
                           low_limit=0, high_limit=12, system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_PWR_ELEC", f"FW Pump {i} Electrical Power", "MW",
                           low_limit=0, high_limit=15, system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_SPEED", f"FW Pump {i} Speed", "rpm",
                           low_limit=0, high_limit=3600, system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_TEMP_BRG", f"FW Pump {i} Bearing Temperature", "°C",
                           low_limit=20, high_limit=80, warning_high=65, alarm_high=75,
                           system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_VIB", f"FW Pump {i} Vibration", "mm/s",
                           low_limit=0, high_limit=20, warning_high=10, alarm_high=15,
                           system="SECONDARY", subsystem="FEEDWATER"),
                PITagConfig(f"{self.plant_code}_FWP{i:02d}_STATUS", f"FW Pump {i} Status", "bool",
                           data_type="Boolean", system="SECONDARY", subsystem="FEEDWATER"),
            ])
        
        # Condenser System Tags
        condenser_tags = [
            PITagConfig(f"{self.plant_code}_CD_PRESS", "Condenser Pressure", "kPa",
                       low_limit=3, high_limit=15, warning_high=10, alarm_high=12,
                       system="SECONDARY", subsystem="CONDENSER"),
            PITagConfig(f"{self.plant_code}_CD_TEMP_COOL_IN", "Condenser Cooling Water Inlet Temp", "°C",
                       low_limit=10, high_limit=35, system="SECONDARY", subsystem="CONDENSER"),
            PITagConfig(f"{self.plant_code}_CD_TEMP_COOL_OUT", "Condenser Cooling Water Outlet Temp", "°C",
                       low_limit=15, high_limit=45, system="SECONDARY", subsystem="CONDENSER"),
            PITagConfig(f"{self.plant_code}_CD_FLOW_COOL", "Condenser Cooling Water Flow", "m³/s",
                       low_limit=20, high_limit=50, system="SECONDARY", subsystem="CONDENSER"),
            PITagConfig(f"{self.plant_code}_CD_LVL_HOTWELL", "Condenser Hotwell Level", "%",
                       low_limit=0, high_limit=100, warning_low=25, alarm_low=15,
                       system="SECONDARY", subsystem="CONDENSER"),
        ]
        
        # Store all tag configurations
        all_tags = reactor_tags + sg_tags + turbine_tags + feedwater_tags + pump_tags + condenser_tags
        
        for tag_config in all_tags:
            self.tag_configs[tag_config.tag_name] = tag_config
    
    def create_tag_mapping(self, simulation_variables: List[str]) -> Dict[str, str]:
        """
        Create mapping from simulation variable names to PI tag names.
        
        Args:
            simulation_variables: List of simulation variable names
            
        Returns:
            Dictionary mapping simulation names to PI tag names
        """
        mapping = {}
        
        # Define mapping patterns
        mapping_patterns = {
            # Reactor mappings
            'primary.reactor.thermal_power_mw': f'{self.plant_code}_RX_PWR_THRM',
            'primary.reactor.thermal_power': f'{self.plant_code}_RX_PWR_THRM',
            'primary.reactor.thermal_fuel_temperature': f'{self.plant_code}_RX_TEMP_FUEL',
            'primary.reactor.thermal_coolant_temperature': f'{self.plant_code}_RX_TEMP_COOL',
            'primary.reactor.thermal_coolant_pressure': f'{self.plant_code}_RX_PRESS_COOL',
            'primary.reactor.thermal_coolant_flow_rate': f'{self.plant_code}_RX_FLOW_COOL',
            'primary.reactor.control_control_rod_position': f'{self.plant_code}_RX_ROD_POS',
            'primary.reactor.neutronics_neutron_flux': f'{self.plant_code}_RX_FLUX_NEUT',
            'primary.reactor.total_reactivity_pcm': f'{self.plant_code}_RX_REACT_TOT',
            'primary.reactor.neutronics_reactivity_pcm': f'{self.plant_code}_RX_REACT_TOT',
            
            # Steam Generator mappings (pattern matching)
            'secondary.steam_generator_SG-1.primary_inlet_temp': f'{self.plant_code}_SG01_TEMP_PRI_IN',
            'secondary.steam_generator_SG-2.primary_inlet_temp': f'{self.plant_code}_SG02_TEMP_PRI_IN',
            'secondary.steam_generator_SG-3.primary_inlet_temp': f'{self.plant_code}_SG03_TEMP_PRI_IN',
            
            # Turbine mappings
            'secondary.reactor.system_electrical_power': f'{self.plant_code}_TB_PWR_ELEC',
            'secondary.turbine_HP-3.inlet_pressure': f'{self.plant_code}_TB_PRESS_HP_IN',
            'secondary.turbine_LP-2.outlet_pressure': f'{self.plant_code}_TB_PRESS_LP_OUT',
            
            # Feedwater mappings
            'secondary.feedwater.feedwater_total_flow': f'{self.plant_code}_FW_FLOW_TOT',
            'secondary.feedwater_system.total_feedwater_flow': f'{self.plant_code}_FW_FLOW_TOT',
            'secondary.feedwater.water_chemistry_ph': f'{self.plant_code}_FW_PH',
            'secondary.feedwater.water_chemistry_dissolved_oxygen': f'{self.plant_code}_FW_O2_DISS',
            
            # Condenser mappings
            'secondary.condenser.pressure': f'{self.plant_code}_CD_PRESS',
            'secondary.condenser.hotwell_level': f'{self.plant_code}_CD_LVL_HOTWELL',
        }
        
        # Apply direct mappings
        for sim_var in simulation_variables:
            if sim_var in mapping_patterns:
                mapping[sim_var] = mapping_patterns[sim_var]
                continue
            
            # Pattern-based mapping for steam generators
            if 'steam_generator_SG-' in sim_var:
                sg_num = sim_var.split('SG-')[1].split('.')[0]
                if sg_num.isdigit():
                    sg_id = f"{int(sg_num):02d}"
                    if 'primary_inlet_temp' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_SG{sg_id}_TEMP_PRI_IN'
                    elif 'secondary_pressure' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_SG{sg_id}_PRESS_SEC'
                    elif 'steam_flow' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_SG{sg_id}_FLOW_STM'
                    elif 'water_level' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_SG{sg_id}_LVL_WTR'
            
            # Pattern-based mapping for feedwater pumps
            elif 'feedwater_FWP-' in sim_var:
                pump_num = sim_var.split('FWP-')[1].split('.')[0].split('-')[0]
                if pump_num.isdigit():
                    pump_id = f"{int(pump_num):02d}"
                    if 'flow_rate' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_FLOW'
                    elif 'discharge_pressure' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_PRESS_DISCH'
                    elif 'electrical_power' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_PWR_ELEC'
                    elif 'speed' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_SPEED'
                    elif 'bearing_temperature' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_TEMP_BRG'
                    elif 'vibration' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_VIB'
                    elif 'status' in sim_var:
                        mapping[sim_var] = f'{self.plant_code}_FWP{pump_id}_STATUS'
        
        self.tag_mapping = mapping
        return mapping
    
    def determine_data_quality(self, value: Any, tag_config: PITagConfig) -> PIDataQuality:
        """
        Determine data quality based on value and tag configuration.
        
        Args:
            value: Data value
            tag_config: PI tag configuration
            
        Returns:
            PIDataQuality enum value
        """
        if pd.isna(value) or value is None:
            return PIDataQuality.BAD
        
        if not isinstance(value, (int, float, bool)):
            return PIDataQuality.GOOD
        
        # Check if value is within valid range
        if tag_config.low_limit is not None and value < tag_config.low_limit:
            return PIDataQuality.QUESTIONABLE
        
        if tag_config.high_limit is not None and value > tag_config.high_limit:
            return PIDataQuality.QUESTIONABLE
        
        # Add some realistic sensor noise/uncertainty
        if isinstance(value, (int, float)):
            # Simulate occasional sensor issues (1% chance)
            if np.random.random() < 0.01:
                return PIDataQuality.UNCERTAIN
        
        return PIDataQuality.GOOD
    
    def determine_alarm_state(self, value: Any, tag_config: PITagConfig) -> PIAlarmState:
        """
        Determine alarm state based on value and tag limits.
        
        Args:
            value: Data value
            tag_config: PI tag configuration
            
        Returns:
            PIAlarmState enum value
        """
        if pd.isna(value) or value is None or not isinstance(value, (int, float)):
            return PIAlarmState.NORMAL
        
        # Check alarm limits
        if tag_config.alarm_low is not None and value <= tag_config.alarm_low:
            return PIAlarmState.ALARM
        if tag_config.alarm_high is not None and value >= tag_config.alarm_high:
            return PIAlarmState.ALARM
        
        # Check warning limits
        if tag_config.warning_low is not None and value <= tag_config.warning_low:
            return PIAlarmState.WARNING
        if tag_config.warning_high is not None and value >= tag_config.warning_high:
            return PIAlarmState.WARNING
        
        return PIAlarmState.NORMAL
    
    def convert_to_pi_format(self, simulation_data: pd.DataFrame) -> pd.DataFrame:
        """
        Convert simulation data to PI format.
        
        Args:
            simulation_data: DataFrame with simulation data
            
        Returns:
            DataFrame in PI format with columns: TagName, Timestamp, Value, Quality, Units, Description, AlarmState
        """
        if self.tag_mapping is None or len(self.tag_mapping) == 0:
            # Auto-create mapping if not exists
            sim_vars = [col for col in simulation_data.columns if col != 'time']
            self.create_tag_mapping(sim_vars)
        
        pi_records = []
        
        for _, row in simulation_data.iterrows():
            timestamp = pd.to_datetime(row['time'], unit='s').strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            for sim_var, pi_tag in self.tag_mapping.items():
                if sim_var in simulation_data.columns:
                    value = row[sim_var]
                    tag_config = self.tag_configs.get(pi_tag)
                    
                    if tag_config is None:
                        # Create default config for unmapped tags
                        tag_config = PITagConfig(pi_tag, f"Unmapped variable {sim_var}", "units")
                    
                    quality = self.determine_data_quality(value, tag_config)
                    alarm_state = self.determine_alarm_state(value, tag_config)
                    
                    pi_records.append({
                        'TagName': pi_tag,
                        'Timestamp': timestamp,
                        'Value': value,
                        'Quality': quality.value,
                        'Units': tag_config.units,
                        'Description': tag_config.description,
                        'AlarmState': alarm_state.value,
                        'System': tag_config.system,
                        'Subsystem': tag_config.subsystem
                    })
        
        return pd.DataFrame(pi_records)
    
    def export_pi_data(self, simulation_data: pd.DataFrame, filename: str, 
                      format_type: str = "csv") -> None:
        """
        Export simulation data in PI format.
        
        Args:
            simulation_data: DataFrame with simulation data
            filename: Output filename
            format_type: Export format ("csv", "json", "parquet")
        """
        pi_data = self.convert_to_pi_format(simulation_data)
        
        if format_type.lower() == "csv":
            pi_data.to_csv(filename, index=False)
        elif format_type.lower() == "json":
            pi_data.to_json(filename, orient='records', date_format='iso', indent=2)
        elif format_type.lower() == "parquet":
            pi_data.to_parquet(filename, index=False)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"Exported {len(pi_data)} PI data points to {filename}")
    
    def export_tag_database(self, filename: str) -> None:
        """
        Export PI tag database configuration.
        
        Args:
            filename: Output filename for tag database
        """
        tag_db = []
        
        for tag_name, config in self.tag_configs.items():
            tag_db.append({
                'TagName': tag_name,
                'Description': config.description,
                'Units': config.units,
                'DataType': config.data_type,
                'LowLimit': config.low_limit,
                'HighLimit': config.high_limit,
                'WarningLow': config.warning_low,
                'WarningHigh': config.warning_high,
                'AlarmLow': config.alarm_low,
                'AlarmHigh': config.alarm_high,
                'System': config.system,
                'Subsystem': config.subsystem
            })
        
        tag_db_df = pd.DataFrame(tag_db)
        tag_db_df.to_csv(filename, index=False)
        print(f"Exported {len(tag_db)} PI tag configurations to {filename}")
    
    def generate_pi_summary_report(self, pi_data: pd.DataFrame) -> str:
        """
        Generate a summary report of PI data.
        
        Args:
            pi_data: DataFrame with PI formatted data
            
        Returns:
            Summary report string
        """
        report = []
        report.append("=" * 60)
        report.append("PI DATA SUMMARY REPORT")
        report.append("=" * 60)
        report.append(f"Plant: {self.plant_code} Unit {self.unit_number}")
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Data overview
        report.append("DATA OVERVIEW:")
        report.append(f"  Total Data Points: {len(pi_data):,}")
        report.append(f"  Unique Tags: {pi_data['TagName'].nunique()}")
        report.append(f"  Time Range: {pi_data['Timestamp'].min()} to {pi_data['Timestamp'].max()}")
        report.append("")
        
        # Quality summary
        quality_counts = pi_data['Quality'].value_counts()
        report.append("DATA QUALITY SUMMARY:")
        for quality, count in quality_counts.items():
            percentage = (count / len(pi_data)) * 100
            report.append(f"  {quality}: {count:,} ({percentage:.1f}%)")
        report.append("")
        
        # Alarm summary
        alarm_counts = pi_data['AlarmState'].value_counts()
        report.append("ALARM STATE SUMMARY:")
        for alarm, count in alarm_counts.items():
            percentage = (count / len(pi_data)) * 100
            report.append(f"  {alarm}: {count:,} ({percentage:.1f}%)")
        report.append("")
        
        # System breakdown
        system_counts = pi_data['System'].value_counts()
        report.append("SYSTEM BREAKDOWN:")
        for system, count in system_counts.items():
            percentage = (count / len(pi_data)) * 100
            report.append(f"  {system}: {count:,} ({percentage:.1f}%)")
        report.append("")
        
        # Active alarms
        active_alarms = pi_data[pi_data['AlarmState'].isin(['WARNING', 'ALARM', 'CRITICAL'])]
        if len(active_alarms) > 0:
            report.append("ACTIVE ALARMS:")
            alarm_summary = active_alarms.groupby(['TagName', 'AlarmState']).size().reset_index(name='Count')
            for _, alarm in alarm_summary.head(10).iterrows():
                report.append(f"  {alarm['TagName']}: {alarm['AlarmState']} ({alarm['Count']} occurrences)")
            if len(alarm_summary) > 10:
                report.append(f"  ... and {len(alarm_summary) - 10} more")
        else:
            report.append("ACTIVE ALARMS: None")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def create_pi_formatter_for_simulation(state_manager, plant_code: str = "NPP") -> PIDataFormatter:
    """
    Create a PI formatter configured for a specific simulation's state manager.
    
    Args:
        state_manager: StateManager instance from simulation
        plant_code: Plant identifier code
        
    Returns:
        Configured PIDataFormatter instance
    """
    formatter = PIDataFormatter(plant_code=plant_code)
    
    # Get available variables from state manager
    available_vars = state_manager.get_available_variables()
    
    # Create tag mapping
    formatter.create_tag_mapping(available_vars)
    
    return formatter
