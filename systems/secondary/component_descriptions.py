"""
Secondary Systems Component Descriptions for Metadata

This module provides comprehensive descriptions for all components in the nuclear plant
secondary systems, organized by subsystem. These descriptions are designed to be used
with the ComponentMetadata system for runtime introspection and documentation.

The descriptions focus on:
- Primary function and purpose
- Key capabilities and features
- Integration with other systems
- Performance characteristics
- Operational significance

Organization:
- Main System Descriptions
- Individual Component Descriptions
- Support System Descriptions
- Integration Components
"""

from typing import Dict, List

# Main Secondary Systems Descriptions
SECONDARY_SYSTEM_DESCRIPTIONS = {
    "secondary_reactor_physics": (
        "Main secondary system coordinator that orchestrates all secondary systems including "
        "steam generators, turbine, condenser, and feedwater systems. Manages system-wide "
        "energy balance, load following operations, and steady-state initialization. Provides "
        "integrated control and monitoring for the complete secondary side of the nuclear plant."
    ),
    
    "heat_flow_tracker": (
        "System-wide energy balance monitor that tracks heat and enthalpy flows between all "
        "secondary components. Validates thermodynamic consistency, calculates system heat flows, "
        "and maintains historical energy balance data. Essential for performance monitoring and "
        "system optimization."
    ),

    "water_chemistry": (
        "Unified water chemistry analysis system serving as the single source of truth for "
        "all secondary system water chemistry parameters. Provides consistent chemistry data "
        "for TSP fouling (iron, copper, silica, pH, dissolved oxygen), feedwater pump "
        "degradation (water aggressiveness, hardness, chloride), and condenser performance "
        "modeling. Calculates composite aggressiveness factors, manages chemical treatment "
        "effectiveness, and tracks scaling/corrosion indices. Eliminates duplicate water "
        "chemistry modeling across components while ensuring consistent chemistry effects."
    )
}

# Condenser System Component Descriptions
CONDENSER_COMPONENT_DESCRIPTIONS = {
    "enhanced_condenser_physics": (
        "Advanced condenser model integrating heat transfer physics with tube degradation, "
        "multi-component fouling, unified water chemistry effects, and vacuum system control. "
        "Tracks tube plugging, biofouling, scale formation, and corrosion products. Uses the "
        "unified water chemistry system for consistent chemistry parameters across all secondary "
        "components, eliminating duplicate water quality modeling."
    ),
    
    "tube_degradation_model": (
        "Specialized model tracking condenser tube failures through vibration damage, corrosion, "
        "and water chemistry effects. Monitors tube wall thickness, leak rates, and plugging "
        "requirements. Calculates performance impacts from reduced heat transfer area and "
        "increased pressure drop in remaining tubes."
    ),
    
    "advanced_fouling_model": (
        "Multi-component fouling system modeling biofouling growth, mineral scale formation, "
        "and corrosion product deposition. Tracks fouling thickness, thermal resistance, and "
        "distribution patterns. Supports various cleaning strategies including chemical, "
        "mechanical, and hydroblast methods."
    ),
    
    
    "vacuum_system": (
        "Integrated vacuum maintenance system using steam jet ejectors for air removal. "
        "Provides automatic control logic, ejector rotation, performance monitoring, and "
        "alarm management. Maintains optimal condenser vacuum for maximum turbine efficiency."
    ),
    
    "steam_ejector": (
        "Individual steam jet ejector for condenser air removal with multistage performance "
        "modeling. Tracks degradation, nozzle fouling, and cleaning requirements. Calculates "
        "steam consumption and air removal capacity based on motive steam conditions."
    )
}

# Feedwater System Component Descriptions
FEEDWATER_COMPONENT_DESCRIPTIONS = {
    "enhanced_feedwater_physics": (
        "Comprehensive feedwater system coordinator managing multi-pump operations, three-element "
        "control, unified water chemistry integration, performance diagnostics, and protection "
        "systems. Uses the unified water chemistry system for consistent pump degradation "
        "modeling and provides automatic level control with steam quality compensation and "
        "load following capabilities for optimal steam generator water level management."
    ),
    
    "feedwater_pump_system": (
        "Multi-pump feedwater delivery system with automatic pump selection, flow distribution, "
        "and performance optimization. Manages pump startup/shutdown sequences, cavitation "
        "protection, and mechanical wear tracking. Provides redundant pumping capacity with "
        "N-1 reliability for continuous steam generator water supply."
    ),
    
    "feedwater_pump": (
        "Individual centrifugal feedwater pump with advanced performance modeling including "
        "cavitation monitoring, mechanical wear tracking, and efficiency degradation. Features "
        "integrated protection systems for NPSH, vibration, temperature, and flow conditions."
    ),
    
    "three_element_control": (
        "Advanced steam generator level control system using feedwater flow, steam flow, and "
        "water level signals. Includes steam quality compensation, load following logic, and "
        "individual steam generator control. Provides both automatic and manual control modes "
        "with calibration capabilities."
    ),
    
    "steam_quality_compensator": (
        "Specialized control component that adjusts feedwater flow based on steam quality "
        "variations to maintain accurate steam generator level control. Compensates for "
        "density changes in the steam generator downcomer and provides enhanced control "
        "stability during transients."
    ),
    
    "performance_diagnostics": (
        "Comprehensive pump performance monitoring system tracking cavitation risk, mechanical "
        "wear, vibration levels, and thermal stress. Provides predictive maintenance "
        "recommendations, health scoring, and system cleaning optimization for maximum "
        "feedwater system reliability."
    ),
    
    "cavitation_model": (
        "Advanced cavitation monitoring system tracking NPSH conditions, vapor formation, "
        "and damage accumulation. Monitors suction conditions, calculates cavitation risk, "
        "and provides early warning of potential pump damage from insufficient NPSH."
    ),
    
    "wear_tracking_model": (
        "Mechanical wear prediction system monitoring impeller, bearing, and seal degradation "
        "based on operating conditions. Tracks environmental factors, calculates wear rates, "
        "and predicts performance impacts from mechanical component degradation."
    ),
    
    "feedwater_protection_system": (
        "Integrated protection system monitoring pump conditions, system pressures, flow rates, "
        "and steam generator levels. Provides automatic trip logic, emergency actions, and "
        "equipment protection to prevent damage during abnormal operating conditions."
    ),
    
    "npsh_protection": (
        "Specialized protection system monitoring Net Positive Suction Head conditions to "
        "prevent pump cavitation damage. Calculates available NPSH, compares to required "
        "values, and initiates protective actions when cavitation risk is detected."
    ),
    
    "feedwater_pump_lubrication": (
        "Dedicated lubrication system for feedwater pump bearings and mechanical components. "
        "Monitors oil quality, temperature, flow rates, and contamination levels. Provides "
        "predictive maintenance scheduling and performance impact assessment."
    ),
    
    "feedwater_water_chemistry": (
        "Water quality management system for feedwater chemistry control including pH, "
        "dissolved oxygen, and chemical treatment. Manages chemical dosing systems and "
        "monitors water quality impacts on pump performance and system corrosion."
    ),
    
    
}

# Steam Generator System Component Descriptions
STEAM_GENERATOR_COMPONENT_DESCRIPTIONS = {
    "enhanced_steam_generator_physics": (
        "Multi-unit steam generator system coordinator providing load balancing, performance "
        "optimization, and system-level control. Manages individual steam generator coordination, "
        "automatic load distribution based on primary flow availability, and system availability "
        "monitoring with N-1 redundancy logic."
    ),
    
    "steam_generator": (
        "Individual U-tube steam generator with comprehensive heat transfer modeling, secondary "
        "side dynamics, water level control, and integrated TSP fouling simulation using unified "
        "water chemistry. Calculates heat transfer based on primary coolant conditions, manages "
        "steam production, and tracks tube support plate fouling progression with consistent "
        "chemistry parameters. Includes automatic shutdown protection for critical fouling "
        "conditions and realistic multi-component deposit formation modeling."
    ),
    
    "tsp_fouling_model": (
        "Comprehensive Tube Support Plate (TSP) fouling model for PWR steam generators tracking "
        "multi-component deposit formation, flow restriction, heat transfer degradation, and "
        "automatic shutdown protection. Models magnetite, copper, silica, and biological fouling "
        "using the unified water chemistry system for consistent iron, copper, silica, pH, and "
        "dissolved oxygen parameters. Provides realistic fouling progression over 40+ year "
        "plant lifetime with cleaning effectiveness simulation and replacement decision logic."
    )
}

# Turbine System Component Descriptions
TURBINE_COMPONENT_DESCRIPTIONS = {
    "enhanced_turbine_physics": (
        "Comprehensive steam turbine system integrating multi-stage expansion, rotor dynamics, "
        "thermal stress monitoring, and protection systems. Coordinates stage-by-stage steam "
        "expansion with extraction flows, mechanical modeling with bearing interactions, and "
        "thermal analysis with material property considerations."
    ),
    
    "turbine_stage_system": (
        "Multi-stage turbine expansion system managing high-pressure and low-pressure turbine "
        "sections with extraction capabilities. Provides stage-by-stage steam expansion "
        "calculations, extraction flow control, and performance optimization across all "
        "turbine stages for maximum efficiency."
    ),
    
    "turbine_stage": (
        "Individual turbine stage with detailed thermodynamic expansion modeling, efficiency "
        "calculations, and degradation tracking. Performs isentropic expansion calculations, "
        "blade wear monitoring, and maintenance scheduling for optimal stage performance."
    ),
    
    "turbine_stage_control_logic": (
        "Advanced control system for turbine stage loading optimization including optimal "
        "loading control, uniform loading distribution, and extraction flow management. "
        "Provides dynamic pressure ratio calculations and stage coordination for maximum "
        "turbine system efficiency."
    ),
    
    "rotor_dynamics_model": (
        "Comprehensive rotor mechanical modeling system including bearing interactions, "
        "vibration monitoring, and thermal expansion effects. Tracks rotor speed dynamics, "
        "calculates bearing loads, monitors vibration levels, and manages thermal growth "
        "for safe turbine operation."
    ),
    
    "bearing_model": (
        "Individual turbine bearing model with load calculations, temperature monitoring, "
        "lubrication state tracking, and wear prediction. Provides bearing performance "
        "assessment, maintenance scheduling, and failure prediction for reliable turbine "
        "operation."
    ),
    
    "vibration_monitor": (
        "Advanced vibration monitoring system tracking rotor displacement, velocity, and "
        "acceleration across multiple measurement points. Provides critical speed monitoring, "
        "alarm management, and vibration trend analysis for predictive maintenance."
    ),
    
    "metal_temperature_tracker": (
        "Thermal monitoring system tracking rotor, casing, and blade temperatures with "
        "thermal gradient calculations and stress analysis. Monitors thermal shock risk, "
        "temperature rates, and thermal stress levels to prevent thermal damage."
    ),
    
    "turbine_protection_system": (
        "Integrated turbine protection system monitoring overspeed, vibration, bearing "
        "temperatures, thrust displacement, vacuum conditions, and thermal stress. Provides "
        "automatic trip logic, emergency action sequences, and safety system coordination "
        "for turbine protection."
    ),
    
    "turbine_governor_system": (
        "Steam turbine governor system providing speed and load control through steam valve "
        "positioning. Includes governor valve modeling, hydraulic system control, and "
        "protection logic integration for precise turbine control and safe operation."
    ),
    
    "governor_valve_model": (
        "Individual governor valve with dynamic response modeling, steam flow calculations, "
        "and valve wear tracking. Provides valve positioning control, flow characteristic "
        "calculations, and maintenance scheduling for reliable steam flow control."
    ),
    
    "turbine_bearing_lubrication": (
        "Specialized lubrication system for turbine bearings with oil quality monitoring, "
        "temperature control, and performance impact assessment. Manages oil circulation, "
        "contamination tracking, and bearing lubrication effectiveness for optimal turbine "
        "bearing performance."
    ),
    
    "governor_lubrication_system": (
        "Hydraulic lubrication system for turbine governor components including oil pumps, "
        "filters, and hydraulic actuators. Monitors hydraulic system performance, oil "
        "quality, and component wear for reliable governor operation."
    )
}

# Support System Component Descriptions
SUPPORT_COMPONENT_DESCRIPTIONS = {
    "thermodynamic_properties": (
        "Utility class providing steam and water property calculations including enthalpy, "
        "temperature, pressure relationships, and saturation properties. Essential for all "
        "thermodynamic calculations throughout the secondary systems."
    ),
    
    "heat_flow_state": (
        "Data structure for organizing heat flow information across secondary systems "
        "including component-level flows, system totals, and energy balance validation. "
        "Provides structured heat flow data for analysis and monitoring."
    ),
    
    "heat_flow_provider": (
        "Abstract interface for components that provide heat flow information to the "
        "system-wide heat flow tracking system. Ensures consistent heat flow reporting "
        "across all secondary system components."
    )
}

# Integration Component Descriptions
INTEGRATION_COMPONENT_DESCRIPTIONS = {
    "lubrication_base": (
        "Base lubrication system framework providing common lubrication functionality "
        "including oil quality monitoring, component wear tracking, maintenance scheduling, "
        "and performance impact assessment. Foundation for all specialized lubrication systems."
    ),
    
    "lubrication_component": (
        "Individual lubricated component model tracking oil requirements, wear rates, "
        "temperature effects, and maintenance needs. Provides component-specific lubrication "
        "modeling for pumps, turbines, and rotating equipment."
    )
}

# Complete component descriptions dictionary
ALL_SECONDARY_COMPONENT_DESCRIPTIONS = {
    **SECONDARY_SYSTEM_DESCRIPTIONS,
    **CONDENSER_COMPONENT_DESCRIPTIONS,
    **FEEDWATER_COMPONENT_DESCRIPTIONS,
    **STEAM_GENERATOR_COMPONENT_DESCRIPTIONS,
    **TURBINE_COMPONENT_DESCRIPTIONS,
    **SUPPORT_COMPONENT_DESCRIPTIONS,
    **INTEGRATION_COMPONENT_DESCRIPTIONS
}

def get_component_description(component_name: str) -> str:
    """
    Get description for a specific component
    
    Args:
        component_name: Name of the component (case-insensitive)
        
    Returns:
        Component description string, or default message if not found
    """
    # Normalize component name
    normalized_name = component_name.lower().replace('_', '_').replace('-', '_')
    
    # Try exact match first
    if normalized_name in ALL_SECONDARY_COMPONENT_DESCRIPTIONS:
        return ALL_SECONDARY_COMPONENT_DESCRIPTIONS[normalized_name]
    
    # Try partial matches
    for key, description in ALL_SECONDARY_COMPONENT_DESCRIPTIONS.items():
        if normalized_name in key or key in normalized_name:
            return description
    
    return f"Secondary system component: {component_name} (description not available)"

def get_system_descriptions() -> Dict[str, List[str]]:
    """
    Get component descriptions organized by system
    
    Returns:
        Dictionary with system names as keys and lists of component descriptions as values
    """
    systems = {
        "Main Systems": list(SECONDARY_SYSTEM_DESCRIPTIONS.values()),
        "Condenser System": list(CONDENSER_COMPONENT_DESCRIPTIONS.values()),
        "Feedwater System": list(FEEDWATER_COMPONENT_DESCRIPTIONS.values()),
        "Steam Generator System": list(STEAM_GENERATOR_COMPONENT_DESCRIPTIONS.values()),
        "Turbine System": list(TURBINE_COMPONENT_DESCRIPTIONS.values()),
        "Support Systems": list(SUPPORT_COMPONENT_DESCRIPTIONS.values()),
        "Integration Components": list(INTEGRATION_COMPONENT_DESCRIPTIONS.values())
    }
    
    return systems

def get_all_component_names() -> List[str]:
    """
    Get list of all component names that have descriptions
    
    Returns:
        List of component names
    """
    return list(ALL_SECONDARY_COMPONENT_DESCRIPTIONS.keys())

def generate_component_summary() -> str:
    """
    Generate a summary report of all secondary system components
    
    Returns:
        Formatted summary string
    """
    systems = get_system_descriptions()
    
    summary = "Secondary Systems Component Summary\n"
    summary += "=" * 50 + "\n\n"
    
    total_components = 0
    for system_name, descriptions in systems.items():
        component_count = len(descriptions)
        total_components += component_count
        summary += f"{system_name}: {component_count} components\n"
    
    summary += f"\nTotal Secondary System Components: {total_components}\n\n"
    
    summary += "Component Categories:\n"
    summary += "-" * 20 + "\n"
    for system_name, descriptions in systems.items():
        summary += f"\n{system_name}:\n"
        for i, description in enumerate(descriptions, 1):
            # Extract first sentence for summary
            first_sentence = description.split('.')[0] + '.'
            summary += f"  {i}. {first_sentence}\n"
    
    return summary

# Example usage and validation
if __name__ == "__main__":
    print("Secondary Systems Component Descriptions")
    print("=" * 50)
    
    # Test component lookup
    test_components = [
        "enhanced_condenser_physics",
        "feedwater_pump_system", 
        "turbine_stage_system",
        "steam_generator"
    ]
    
    print("\nSample Component Descriptions:")
    print("-" * 30)
    for component in test_components:
        description = get_component_description(component)
        print(f"\n{component}:")
        print(f"  {description}")
    
    # Generate summary
    print("\n" + generate_component_summary())
    
    print(f"\nTotal components with descriptions: {len(get_all_component_names())}")
