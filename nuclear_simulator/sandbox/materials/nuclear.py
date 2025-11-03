

# Import libraries
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.liquids import Liquid


# Class for nuclear fuel material
class Fuel(Solid):
    """
    Uranium dioxide (UO₂) fuel with structural materials.
    
    This class models nuclear fuel as a solid material with effective properties
    that account for both the UO₂ pellets and surrounding structural components
    (cladding, spacer grids, etc.). The properties represent a homogenized fuel
    assembly suitable for thermal-hydraulic analysis.
    
    Physical Properties:
        - HEAT_CAPACITY = 300.0 J/(kg·K): Effective specific heat capacity
            * UO₂ has Cv ≈ 235-330 J/(kg·K) depending on temperature
            * Value includes thermal mass of cladding and structural materials
            * Appropriate for PWR fuel assembly thermal analysis

        - DENSITY = 10970.0 kg/m³: UO₂ theoretical density
            * Pure UO₂ theoretical density is 10960-10970 kg/m³
            * Actual fuel density is lower (~95% theoretical) due to porosity
            * This reference represents solid UO₂ material density
    
    Typical Operating Conditions:
        - Temperature range: 500-1500 K (fuel centerline temperatures)
        - Fuel pellet diameter: ~8-9 mm
        - Cladding: Zircaloy-4, ~0.6 mm thick
    
    References:
        - IAEA-TECDOC-1496: Thermophysical Properties of Materials for Nuclear Engineering
        - Nuclear Systems I, Todreas & Kazimi
    """
    HEAT_CAPACITY = 300.0  # [J/(kg·K)] Effective specific heat (fuel + structure)
    DENSITY = 10970.0      # [kg/m³]    UO₂ theoretical density


# Class for PWR coolant material
class Coolant(Liquid):
    """
    Pressurized water reactor (PWR) coolant.
    
    This class models pressurized light water used as coolant and moderator in PWR
    reactors. The water operates in a subcooled liquid state at high pressure to
    prevent boiling, with properties that vary with temperature and pressure changes.
    
    Physical Properties:
        - HEAT_CAPACITY = 4200.0 J/(kg·K): Specific heat capacity of water
            * Water at 550 K and 15.5 MPa has Cv ≈ 4200-4500 J/(kg·K)
            * Value represents typical PWR operating conditions
            * Weakly dependent on pressure in liquid phase
        
        - DENSITY = 700.0 kg/m³: Pressurized water density
            * Water at 550 K and 15.5 MPa has ρ ≈ 700-750 kg/m³
            * Significantly lower than ambient water (997 kg/m³) due to thermal expansion
            * Representative of PWR primary coolant conditions
    
    Typical Operating Conditions:
        - Temperature range: 550-600 K (inlet ~550 K, outlet ~593 K)
        - Pressure: 15.0-16.0 MPa (maintained by pressurizer)
        - Flow rate: ~15,000-20,000 kg/s per loop (4-loop plant)
        - Subcooling margin: ~20-40 K below saturation temperature
    
    References:
        - IAPWS-IF97: Industrial Formulation of Thermodynamic Properties of Water
        - Nuclear Systems I, Todreas & Kazimi, Chapter 3
        - ASME Steam Tables
    """
    HEAT_CAPACITY = 4200.0  # [J/(kg·K)] Specific heat of water
    DENSITY = 700.0         # [kg/m³]    Pressurized water density (~15.5 MPa, 550K)


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Instantiate fuel and coolant
    fuel = Fuel(m=1000.0, U=1e8)
    coolant = Coolant(m=5000.0, U=2e9)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")




