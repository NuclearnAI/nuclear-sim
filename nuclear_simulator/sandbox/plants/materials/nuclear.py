

# Import libraries
from nuclear_simulator.sandbox.plants.materials.solids import Solid
from nuclear_simulator.sandbox.plants.materials.liquids import IsovolumetricLiquid


# Class for nuclear fuel material
class Fuel(Solid):
    """
    Uranium dioxide (UO₂) fuel with structural materials.
    
    This class models nuclear fuel as a solid material with effective properties
    that account for both the UO₂ pellets and surrounding structural components
    (cladding, spacer grids, etc.). The properties represent a homogenized fuel
    assembly suitable for thermal-hydraulic analysis.
    
    Physical Properties:
        - cp = 300.0 J/(kg·K): Effective specific heat capacity
            * UO₂ has cp ≈ 235-330 J/(kg·K) depending on temperature
            * Value includes thermal mass of cladding and structural materials
            * Appropriate for PWR fuel assembly thermal analysis
        
        - rho = 10970.0 kg/m³: UO₂ theoretical density
            * Pure UO₂ theoretical density is 10960-10970 kg/m³
            * Actual fuel density is lower (~95% theoretical) due to porosity
            * This reference represents solid UO₂ material density
    
    Typical Operating Conditions:
        - Temperature range: 500-1500 K (fuel centerline temperatures)
        - Fuel pellet diameter: ~8-9 mm
        - Cladding: Zircaloy-4, ~0.6 mm thick
    
    Usage:
        >>> fuel = Fuel.from_temperature(m=80000.0, T=600.0)
        >>> print(f"Fuel: {fuel.T:.1f} K, {fuel.rho:.1f} kg/m³")
    
    References:
        - IAEA-TECDOC-1496: Thermophysical Properties of Materials for Nuclear Engineering
        - Nuclear Systems I, Todreas & Kazimi
    """
    
    CP = 300.0        # [J/(kg·K)] Effective specific heat (fuel + structure)
    DENSITY = 10970.0 # [kg/m³] UO₂ theoretical density


# Class for PWR coolant material
class Coolant(IsovolumetricLiquid):
    """
    Pressurized water reactor (PWR) coolant.
    
    This class models pressurized light water used as coolant and moderator in PWR
    reactors. The water operates in a subcooled liquid state at high pressure to
    prevent boiling, with properties that vary with temperature and pressure changes.
    
    Physical Properties:
        - cp = 4200.0 J/(kg·K): Specific heat capacity of water
            * Water at 550 K and 15.5 MPa has cp ≈ 4200-4500 J/(kg·K)
            * Value represents typical PWR operating conditions
            * Weakly dependent on pressure in liquid phase
        
        - rho = 700.0 kg/m³: Pressurized water density
            * Water at 550 K and 15.5 MPa has ρ ≈ 700-750 kg/m³
            * Significantly lower than ambient water (997 kg/m³) due to thermal expansion
            * Representative of PWR primary coolant conditions
        
        - bulk_modulus = 2.2e9 Pa: Bulk modulus of water
            * Water bulk modulus is 2.0-2.4 GPa depending on temperature
            * Determines pressure response to density changes
            * Enables modeling of pressure surges and density variations
        
        - alpha = 0.00073 K⁻¹: Volumetric thermal expansion coefficient
            * Water at 550 K and 15.5 MPa has α ≈ 0.0007-0.0008 K⁻¹
            * Controls volume/pressure change with temperature
            * Critical for modeling thermal expansion effects
    
    Typical Operating Conditions:
        - Temperature range: 550-600 K (inlet ~550 K, outlet ~593 K)
        - Pressure: 15.0-16.0 MPa (maintained by pressurizer)
        - Flow rate: ~15,000-20,000 kg/s per loop (4-loop plant)
        - Subcooling margin: ~20-40 K below saturation temperature
    
    Usage:
        >>> coolant = Coolant.from_temperature_pressure(
        ...     m=10000.0,
        ...     T=550.0,
        ...     V=14.286,  # m³
        ...     P=15.5e6   # Pa
        ... )
        >>> print(f"Coolant: {coolant.T:.1f} K, {coolant.P/1e6:.1f} MPa")
    
    References:
        - IAPWS-IF97: Industrial Formulation of Thermodynamic Properties of Water
        - Nuclear Systems I, Todreas & Kazimi, Chapter 3
        - ASME Steam Tables
    """
    
    CP = 4200.0           # [J/(kg·K)] Specific heat of water
    DENSITY = 700.0       # [kg/m³]    Pressurized water density (~15.5 MPa, 550K)
    BULK_MODULUS = 2.2e9  # [Pa]       Bulk modulus of water
    ALPHA = 0.00073       # [1/K]      Volumetric thermal expansion coefficient
    ALPHA_T = 550.0       # [K]        Reference temperature for expansion
    



# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    ...
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")




