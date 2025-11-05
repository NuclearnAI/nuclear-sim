

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
    DENSITY = 10970.0


class PWRPrimaryWater(Liquid):
    """
    Pressurized water reactor (PWR) coolant. Water at 15-16 MPa and 550-600 K.
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Specific heat of water
        DENSITY:       [kg/m³]    Pressurized water density (~15.5 MPa, 550K)
    """
    HEAT_CAPACITY = 4200.0
    DENSITY = 700.0


class PWRSecondaryWater(Liquid):
    """
    Pressurized water reactor (PWR) secondary side water. Water at ~7 MPa and 500-550 K.
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Specific heat of water
        DENSITY:       [kg/m³]    Pressurized water density (~7 MPa, 525K)
    """
    HEAT_CAPACITY = 4200.0
    DENSITY = 720.0


class PWRSecondarySteam(Gas):
    """
    Pressurized water reactor (PWR) secondary side steam. Steam at ~7 MPa and 550-600 K.
    Attributes:
        HEAT_CAPACITY: [J/(kg·K)] Specific heat of steam
        DENSITY:       [kg/m³]    Steam density (~7 MPa, 575K)
    """
    HEAT_CAPACITY = 2100.0
    DENSITY = 30.0

    