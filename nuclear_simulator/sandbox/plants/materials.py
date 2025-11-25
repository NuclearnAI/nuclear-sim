
# Import libraries
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.materials.phases import BoilingProperties


class UraniumDioxide(Solid):
    """
    Uranium dioxide (UO₂) fuel with structural materials.
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Effective specific heat capacity
        DENSITY:       [kg/m³]    Effective density
        P0:            [Pa]       Reference state pressure
        T0:            [K]        Reference state temperature
        u0:            [J/kg]     Reference internal specific energy at T0
    """
    HEAT_CAPACITY = 300.0
    DENSITY = 10_970.0
    P0 = 15.5e6
    T0 = 600.0
    u0 = 200_000.0


class PWRPrimaryWater(Liquid):
    """
    Pressurized water reactor (PWR) primary coolant.
    Water at ~15.5 MPa and ~300-320 °C (≈575 K).
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Specific heat of water
        DENSITY:       [kg/m³]    Pressurized water density
        P0:            [Pa]       Reference state pressure
        T0:            [K]        Reference state temperature
        u0:            [J/kg]     Reference internal specific energy at T0
    """
    HEAT_CAPACITY = 5000.0
    DENSITY = 720.0
    P0 = 15.5e6
    T0 = 550.0
    u0 = 1_500_000.0  # Approximate internal energy at operating point


class PWRSecondaryBoilingProperties(BoilingProperties):
    """
    Boiling properties for PWR secondary-side water/steam.
    Attributes:
        HEAT_CAPACITY_BOUND:    [J/(kg·K)]  Specific heat capacity of bound phase
        HEAT_CAPACITY_UNBOUND:  [J/(kg·K)]  Specific heat capacity of unbound phase
        MOLECULAR_WEIGHT:       [kg/mol]    Molecular weight (for ideal gas calculations)
        T0:                     [K]    Reference temperature
        P0:                     [Pa]   Reference pressure
        u0_BOUND:               [J/kg] Reference internal specific energy of bound phase at T0
        u0_UNBOUND:             [J/kg] Reference internal specific energy of unbound phase at T0
    """
    HEAT_CAPACITY_BOUND = 5000.0
    HEAT_CAPACITY_UNBOUND = 2100.0
    MOLECULAR_WEIGHT = 0.01801528  # (H₂O)
    T0 = 500.0
    P0 = 7e6
    u0_BOUND = 1_380_000.0
    u0_UNBOUND = 2_700_000.0


class PWRSecondaryWater(Liquid):
    """
    PWR secondary-side feedwater / liquid.
    Water near saturation at ~7 MPa (~285.8 °C, 559 K).
    Attributes:
        BOILING_PROPERTIES: [-]        Boiling properties for PWR secondary-side water/steam
        MOLECULAR_WEIGHT:   [kg/mol]   Molecular weight of water
        HEAT_CAPACITY:      [J/(kg·K)] Specific heat of water
        DENSITY:            [kg/m³]    Saturated liquid density (~7 MPa, 559 K)
        P0:                 [Pa]       Reference state pressure
        T0:                 [K]        Reference state temperature
        u0:                 [J/kg]     Reference internal specific energy at T0
    """
    DENSITY = 740.0
    BOILING_PROPERTIES = PWRSecondaryBoilingProperties()
    MOLECULAR_WEIGHT = PWRSecondaryBoilingProperties.MOLECULAR_WEIGHT
    HEAT_CAPACITY = PWRSecondaryBoilingProperties.HEAT_CAPACITY_BOUND
    P0 = PWRSecondaryBoilingProperties.P0
    T0 = PWRSecondaryBoilingProperties.T0
    u0 = PWRSecondaryBoilingProperties.u0_BOUND


class PWRSecondarySteam(Gas):
    """
    PWR secondary-side steam.
    Steam at ~7 MPa and ~559-600 K (saturated to slightly superheated).
    Attributes:
        BOILING_PROPERTIES: [-]        Boiling properties for PWR secondary-side water/steam
        MOLECULAR_WEIGHT:   [kg/mol]   Molecular weight of water
        HEAT_CAPACITY:      [J/(kg·K)] Specific heat of water
        P0:                 [Pa]       Reference state pressure
        T0:                 [K]        Reference state temperature
        u0:                 [J/kg]     Reference internal specific energy at T0
    """
    BOILING_PROPERTIES = PWRSecondaryBoilingProperties()
    MOLECULAR_WEIGHT = PWRSecondaryBoilingProperties.MOLECULAR_WEIGHT
    HEAT_CAPACITY = PWRSecondaryBoilingProperties.HEAT_CAPACITY_UNBOUND
    P0 = PWRSecondaryBoilingProperties.P0
    T0 = PWRSecondaryBoilingProperties.T0
    u0 = PWRSecondaryBoilingProperties.u0_UNBOUND
