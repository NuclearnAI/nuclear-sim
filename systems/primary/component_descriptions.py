"""
Primary Systems Component Descriptions for Metadata

This module provides comprehensive descriptions for all components in the nuclear plant
primary systems, organized by subsystem. These descriptions are designed to be used
with the ComponentMetadata system for runtime introspection and documentation.

The descriptions focus on:
- Nuclear physics and reactor safety
- Primary function and purpose
- Key capabilities and features
- Integration with other systems
- Performance characteristics
- Operational significance for nuclear safety

Organization:
- Main Primary System Descriptions
- Reactor Physics Component Descriptions
- Reactor Control Component Descriptions
- Reactor Thermal Component Descriptions
- Primary Coolant Component Descriptions
- Heat Source Component Descriptions
- Support System Descriptions
- Integration Components
"""

from typing import Dict, List

# Main Primary Systems Descriptions
PRIMARY_SYSTEM_DESCRIPTIONS = {
    "primary_reactor_physics": (
        "Main primary system coordinator that orchestrates all reactor physics calculations "
        "including neutronics, reactivity control, thermal hydraulics, and safety systems. "
        "Manages reactor criticality control, power level regulation, and safety system "
        "coordination. Provides integrated monitoring and control for the complete primary "
        "side of the nuclear plant with emphasis on nuclear safety and reactor physics."
    ),
    
    "reactor_state_manager": (
        "Central reactor state management system that maintains and coordinates all reactor "
        "parameters including neutron flux, temperatures, pressures, and control positions. "
        "Provides state validation, parameter bounds checking, and historical data management "
        "for reactor operations. Essential for reactor safety monitoring and operational control."
    )
}

# Reactor Physics Component Descriptions
REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS = {
    "reactivity_model": (
        "Comprehensive PWR reactivity model accounting for all major reactivity effects "
        "including control rod worth, boron concentration, temperature feedback, fission "
        "product poisoning, fuel depletion, and burnable poisons. Calculates total system "
        "reactivity with detailed component breakdown for reactor criticality control and "
        "safety analysis. Provides equilibrium state calculations and critical boron determination."
    ),
    
    "neutronics_model": (
        "Nuclear reactor neutronics calculation system providing neutron flux management, "
        "power level calculations, and control rod reactivity effects. Performs neutron "
        "physics calculations including flux-to-power conversions, reactivity assessments, "
        "and neutron flux validation. Essential for reactor power control and nuclear "
        "safety monitoring."
    ),
    
    "point_kinetics": (
        "Point kinetics model for reactor neutron dynamics including delayed neutron "
        "precursor tracking, reactivity feedback, and transient analysis. Calculates "
        "neutron flux evolution during power changes, reactor startups, and transient "
        "conditions. Provides fundamental reactor dynamics modeling for safety analysis "
        "and control system design."
    ),
    
    "thermal_hydraulics": (
        "Primary system thermal hydraulics model calculating coolant flow, heat transfer, "
        "and temperature distributions throughout the reactor core and primary loops. "
        "Integrates with neutronics for coupled physics calculations and provides thermal "
        "limits monitoring. Essential for reactor safety analysis and thermal margin assessment."
    ),
    
    "reactor_config": (
        "Reactor configuration management system containing all reactor-specific parameters "
        "including control rod worth, temperature coefficients, fuel properties, and "
        "neutron cross-sections. Provides centralized configuration for reactor physics "
        "calculations and ensures consistent parameter usage across all models."
    )
}

# Reactor Control Component Descriptions
REACTOR_CONTROL_COMPONENT_DESCRIPTIONS = {
    "scram_logic": (
        "Reactor protection system implementing automatic reactor shutdown (SCRAM) logic "
        "with multiple independent trip channels and safety system actuation. Monitors "
        "critical reactor parameters including power level, coolant temperature, pressure, "
        "and neutron flux for automatic safety system activation. Provides fail-safe "
        "reactor shutdown capability for nuclear safety."
    ),
    
    "control_rod_system": (
        "Reactor control rod drive system managing control rod positioning for reactivity "
        "control and reactor shutdown. Provides precise rod positioning, automatic control "
        "logic, and emergency insertion capability. Integrates with reactor protection "
        "system for SCRAM actuation and maintains reactor criticality control during "
        "normal and emergency operations."
    ),
    
    "reactor_protection_system": (
        "Comprehensive reactor protection system coordinating all safety-related automatic "
        "actions including SCRAM, emergency core cooling, and containment isolation. "
        "Monitors reactor safety parameters with redundant channels and provides automatic "
        "protective actions to prevent fuel damage and maintain reactor safety boundaries."
    ),
    
    "safety_system_coordinator": (
        "Safety system integration coordinator managing interactions between reactor "
        "protection, emergency core cooling, containment systems, and other safety-related "
        "equipment. Provides system-level safety logic, priority management, and coordinated "
        "response to accident conditions for comprehensive nuclear safety."
    )
}

# Reactor Thermal Component Descriptions
REACTOR_THERMAL_COMPONENT_DESCRIPTIONS = {
    "heat_transfer_model": (
        "Reactor heat transfer model calculating heat removal from fuel to coolant with "
        "flow-dependent heat transfer coefficients and thermal coupling between components. "
        "Provides fuel-to-coolant heat transfer calculations, thermal resistance modeling, "
        "and heat removal validation for reactor thermal analysis and safety assessment."
    ),
    
    "temperature_feedback": (
        "Reactor temperature feedback system calculating reactivity effects from fuel "
        "and moderator temperature changes. Implements Doppler feedback, moderator "
        "temperature coefficient, and thermal reactivity effects for reactor stability "
        "and self-regulating behavior. Essential for reactor physics and safety analysis."
    ),
    
    "thermal_coupling_system": (
        "Thermal coupling coordinator managing heat transfer between reactor components "
        "including fuel, cladding, coolant, and structural materials. Provides integrated "
        "thermal modeling with temperature distribution calculations and thermal stress "
        "analysis for reactor thermal performance assessment."
    ),
    
    "fuel_temperature_model": (
        "Fuel temperature calculation system modeling heat generation, conduction, and "
        "removal in reactor fuel elements. Calculates fuel centerline temperatures, "
        "thermal gradients, and fuel performance parameters. Critical for fuel integrity "
        "monitoring and thermal margin assessment."
    )
}

# Primary Coolant Component Descriptions
PRIMARY_COOLANT_COMPONENT_DESCRIPTIONS = {
    "reactor_coolant_pump": (
        "Individual reactor coolant pump with comprehensive performance modeling including "
        "flow control, speed regulation, and protection systems. Features realistic startup "
        "and shutdown dynamics, cavitation protection, and mechanical wear tracking. "
        "Provides primary coolant circulation with integrated safety systems for reactor "
        "cooling and heat removal."
    ),
    
    "coolant_pump_system": (
        "Complete reactor coolant pump system managing multiple pumps with automatic flow "
        "control, pump sequencing, and system protection. Provides total system flow "
        "regulation, pump coordination, and N-1 redundancy for reliable primary coolant "
        "circulation. Essential for reactor heat removal and thermal hydraulic performance."
    ),
    
    "base_pump": (
        "Foundation pump class providing common functionality for all nuclear plant pumps "
        "including speed control, protection systems, and performance monitoring. Implements "
        "standard pump dynamics, trip logic, and control interfaces for consistent pump "
        "behavior across primary and secondary systems."
    ),
    
    "pump_protection_system": (
        "Integrated pump protection system monitoring flow rates, pressures, temperatures, "
        "and mechanical conditions for automatic pump trip and equipment protection. "
        "Provides low flow protection, cavitation monitoring, and system pressure protection "
        "to prevent pump damage during abnormal conditions."
    ),
    
    "flow_control_system": (
        "Primary coolant flow control system managing total system flow through coordinated "
        "pump speed control and automatic flow regulation. Provides flow setpoint control, "
        "flow distribution optimization, and integration with reactor power control for "
        "optimal thermal hydraulic performance."
    )
}

# Heat Source Component Descriptions
HEAT_SOURCE_COMPONENT_DESCRIPTIONS = {
    "reactor_heat_source": (
        "Primary reactor heat source model calculating nuclear heat generation from fission "
        "reactions with power distribution, decay heat, and transient heat generation. "
        "Integrates with neutronics for power-dependent heat generation and provides "
        "realistic reactor thermal power for thermal hydraulic calculations."
    ),
    
    "constant_heat_source": (
        "Simplified constant heat source model for testing and steady-state analysis "
        "providing fixed heat generation rates. Used for system testing, component "
        "validation, and simplified thermal analysis when detailed reactor physics "
        "modeling is not required."
    ),
    
    "heat_source_interface": (
        "Abstract interface defining standard heat source behavior for all reactor heat "
        "generation models. Ensures consistent heat source integration with thermal "
        "hydraulic systems and provides standardized heat generation calculations "
        "across different heat source implementations."
    ),
    
    "decay_heat_model": (
        "Post-shutdown decay heat calculation system modeling fission product decay "
        "and actinide decay heat generation. Provides time-dependent decay heat curves "
        "following reactor shutdown for emergency cooling system design and safety "
        "analysis. Critical for loss-of-coolant accident analysis."
    )
}

# Support System Component Descriptions
SUPPORT_COMPONENT_DESCRIPTIONS = {
    "reactor_state": (
        "Comprehensive reactor state data structure containing all reactor parameters "
        "including neutron flux, temperatures, pressures, control positions, and fission "
        "product concentrations. Provides centralized state management with parameter "
        "validation and bounds checking for reactor operations."
    ),
    
    "physics_constants": (
        "Nuclear physics constants and parameters including neutron cross-sections, "
        "decay constants, fission yields, and material properties. Provides standardized "
        "nuclear data for reactor physics calculations and ensures consistent parameter "
        "usage across all reactor models."
    ),
    
    "thermal_properties": (
        "Thermal and material property calculations for reactor components including "
        "fuel, cladding, coolant, and structural materials. Provides temperature-dependent "
        "properties, thermal conductivity, and heat capacity data for thermal analysis "
        "and heat transfer calculations."
    ),
    
    "safety_parameters": (
        "Nuclear safety parameter definitions including safety limits, operating limits, "
        "and protection system setpoints. Provides centralized safety parameter management "
        "for reactor protection systems and ensures consistent safety system operation "
        "across all reactor conditions."
    )
}

# Integration Component Descriptions
INTEGRATION_COMPONENT_DESCRIPTIONS = {
    "primary_secondary_interface": (
        "Interface system managing heat transfer and parameter exchange between primary "
        "and secondary systems through steam generators. Coordinates primary coolant "
        "conditions with secondary system requirements and provides integrated plant "
        "operation with proper thermal coupling."
    ),
    
    "reactor_control_interface": (
        "Control system interface coordinating reactor control systems with plant-wide "
        "control including turbine control, feedwater control, and load following. "
        "Provides integrated plant control with reactor physics constraints and safety "
        "system coordination for optimal plant operation."
    ),
    
    "safety_system_interface": (
        "Safety system interface coordinating reactor protection systems with plant "
        "safety systems including emergency core cooling, containment systems, and "
        "emergency power systems. Ensures integrated safety system response and "
        "coordinated emergency actions for comprehensive nuclear safety."
    ),
    
    "plant_state_coordinator": (
        "Plant-wide state coordination system managing interactions between primary "
        "systems, secondary systems, and plant control systems. Provides system-level "
        "state management, parameter validation, and coordinated plant operation for "
        "integrated nuclear plant simulation."
    )
}

# Complete component descriptions dictionary
ALL_PRIMARY_COMPONENT_DESCRIPTIONS = {
    **PRIMARY_SYSTEM_DESCRIPTIONS,
    **REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS,
    **REACTOR_CONTROL_COMPONENT_DESCRIPTIONS,
    **REACTOR_THERMAL_COMPONENT_DESCRIPTIONS,
    **PRIMARY_COOLANT_COMPONENT_DESCRIPTIONS,
    **HEAT_SOURCE_COMPONENT_DESCRIPTIONS,
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
    if normalized_name in ALL_PRIMARY_COMPONENT_DESCRIPTIONS:
        return ALL_PRIMARY_COMPONENT_DESCRIPTIONS[normalized_name]
    
    # Try partial matches
    for key, description in ALL_PRIMARY_COMPONENT_DESCRIPTIONS.items():
        if normalized_name in key or key in normalized_name:
            return description
    
    return f"Primary system component: {component_name} (description not available)"

def get_system_descriptions() -> Dict[str, List[str]]:
    """
    Get component descriptions organized by system
    
    Returns:
        Dictionary with system names as keys and lists of component descriptions as values
    """
    systems = {
        "Main Primary Systems": list(PRIMARY_SYSTEM_DESCRIPTIONS.values()),
        "Reactor Physics": list(REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS.values()),
        "Reactor Control": list(REACTOR_CONTROL_COMPONENT_DESCRIPTIONS.values()),
        "Reactor Thermal": list(REACTOR_THERMAL_COMPONENT_DESCRIPTIONS.values()),
        "Primary Coolant": list(PRIMARY_COOLANT_COMPONENT_DESCRIPTIONS.values()),
        "Heat Sources": list(HEAT_SOURCE_COMPONENT_DESCRIPTIONS.values()),
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
    return list(ALL_PRIMARY_COMPONENT_DESCRIPTIONS.keys())

def generate_component_summary() -> str:
    """
    Generate a summary report of all primary system components
    
    Returns:
        Formatted summary string
    """
    systems = get_system_descriptions()
    
    summary = "Primary Systems Component Summary\n"
    summary += "=" * 50 + "\n\n"
    
    total_components = 0
    for system_name, descriptions in systems.items():
        component_count = len(descriptions)
        total_components += component_count
        summary += f"{system_name}: {component_count} components\n"
    
    summary += f"\nTotal Primary System Components: {total_components}\n\n"
    
    summary += "Component Categories:\n"
    summary += "-" * 20 + "\n"
    for system_name, descriptions in systems.items():
        summary += f"\n{system_name}:\n"
        for i, description in enumerate(descriptions, 1):
            # Extract first sentence for summary
            first_sentence = description.split('.')[0] + '.'
            summary += f"  {i}. {first_sentence}\n"
    
    return summary

def generate_safety_focused_summary() -> str:
    """
    Generate a summary focused on nuclear safety components
    
    Returns:
        Formatted safety summary string
    """
    safety_systems = [
        "Reactor Control",
        "Reactor Physics", 
        "Integration Components"
    ]
    
    systems = get_system_descriptions()
    
    summary = "Nuclear Safety Systems Summary\n"
    summary += "=" * 40 + "\n\n"
    
    for system_name in safety_systems:
        if system_name in systems:
            summary += f"{system_name}:\n"
            summary += "-" * len(system_name) + "\n"
            for i, description in enumerate(systems[system_name], 1):
                # Extract safety-relevant information
                first_sentence = description.split('.')[0] + '.'
                summary += f"{i}. {first_sentence}\n"
            summary += "\n"
    
    return summary

def get_reactor_physics_components() -> Dict[str, str]:
    """
    Get all reactor physics related components
    
    Returns:
        Dictionary with reactor physics component descriptions
    """
    return REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS.copy()

def get_safety_critical_components() -> Dict[str, str]:
    """
    Get all safety-critical components
    
    Returns:
        Dictionary with safety-critical component descriptions
    """
    safety_components = {}
    safety_components.update(REACTOR_CONTROL_COMPONENT_DESCRIPTIONS)
    safety_components.update({k: v for k, v in REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS.items() 
                            if 'safety' in v.lower() or 'protection' in v.lower()})
    safety_components.update({k: v for k, v in INTEGRATION_COMPONENT_DESCRIPTIONS.items() 
                            if 'safety' in v.lower()})
    
    return safety_components

# Example usage and validation
if __name__ == "__main__":
    print("Primary Systems Component Descriptions")
    print("=" * 50)
    
    # Test component lookup
    test_components = [
        "reactivity_model",
        "reactor_coolant_pump", 
        "scram_logic",
        "heat_transfer_model"
    ]
    
    print("\nSample Component Descriptions:")
    print("-" * 30)
    for component in test_components:
        description = get_component_description(component)
        print(f"\n{component}:")
        print(f"  {description}")
    
    # Generate summary
    print("\n" + generate_component_summary())
    
    # Generate safety summary
    print("\n" + generate_safety_focused_summary())
    
    print(f"\nTotal components with descriptions: {len(get_all_component_names())}")
    print(f"Safety-critical components: {len(get_safety_critical_components())}")
