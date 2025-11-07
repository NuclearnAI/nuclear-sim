
# Import libraries
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.liquids import Liquid


class UraniumDioxide(Solid):
    """
    Uranium dioxide (UO₂) fuel with structural materials.
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Effective specific heat capacity
        DENSITY:       [kg/m³]    Effective density
    """
    HEAT_CAPACITY = 300.0
    DENSITY = 10_970.0


class PWRPrimaryWater(Liquid):
    """
    Pressurized water reactor (PWR) primary coolant.
    Water at ~15.5 MPa and ~300–320 °C (≈575 K).
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Specific heat of water
        DENSITY:       [kg/m³]    Pressurized water density (~15.5 MPa, 575 K)
    """
    HEAT_CAPACITY = 5000.0
    DENSITY = 720.0


class PWRSecondaryWater(Liquid):
    """
    PWR secondary-side feedwater / liquid.
    Water near saturation at ~7 MPa (~285.8 °C, 559 K).
    Attributes:
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight of water
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat of water
        DENSITY:          [kg/m³]    Saturated liquid density (~7 MPa, 559 K)
        LATENT_HEAT:      [J/kg]     Enthalpy of vaporization (~7 MPa)
        P0:               [Pa]       Reference state pressure
        T0:               [K]        Reference state temperature
        u0:               [J/kg]    Reference internal specific energy at T0
    """
    MOLECULAR_WEIGHT = 0.01801528  # (H₂O)
    HEAT_CAPACITY = 5000.0
    LATENT_HEAT = 1_500_000.0
    DENSITY = 740.0
    P0 = 7e6
    T0 = 559.0
    u0 = 1_380_000.0  # Approximate internal energy at saturation point


class PWRSecondarySteam(Gas):
    """
    PWR secondary-side steam.
    Steam at ~7 MPa and ~559-600 K (saturated to slightly superheated).
    Attributes:
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight of water
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat of water
        DENSITY:          [kg/m³]    Saturated liquid density (~7 MPa, 559 K)
        LATENT_HEAT:      [J/kg]     Enthalpy of vaporization (~7 MPa)
        P0:               [Pa]       Reference state pressure
        T0:               [K]        Reference state temperature
        u0:               [J/kg]     Reference internal specific energy at T0
    """
    MOLECULAR_WEIGHT = 0.01801528  # (H₂O)
    HEAT_CAPACITY = 2100.0
    LATENT_HEAT = 1_500_000.0
    DENSITY = 36.5
    P0 = 7e6
    T0 = 559.0
    u0 = 2_700_000.0  # Approximate internal energy at saturation point


