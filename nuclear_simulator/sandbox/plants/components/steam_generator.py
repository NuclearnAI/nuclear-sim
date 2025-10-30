
# Import libraries
from nuclear_simulator.sandbox.plants.thermograph import ThermoNode
from nuclear_simulator.sandbox.plants.physics import calc_pipe_mass_flow


class SGHotLeg(ThermoNode):
    """
    Small control volume representing the hot outlet header from the reactor.
    """
    coolant_P: float = 15.4e6       # [Pa]        Pressure in hot leg
    coolant_T: float = 580.0        # [K]         Coolant temperature
    coolant_m: float = 500.0        # [kg]        Coolant mass
    coolant_cp: float = 4_200.0     # [J/(kg·K)]  Specific heat capacity
    coolant_U: float | None = None  # [J]         Internal energy (set in __init__)
    coolant_K: float = 2.2e9        # [Pa]        Bulk modulus of water
    coolant_alpha: float = 5e-4     # [1/K]       Thermal expansion coefficient


class SGPrimHot(ThermoNode):
    """
    Steam generator primary-side inlet plenum (hot header).
    """
    coolant_P: float = 15.3e6       # [Pa]        Pressure in SG primary inlet
    coolant_T: float = 575.0        # [K]         Coolant temperature
    coolant_m: float = 600.0        # [kg]        Coolant mass
    coolant_cp: float = 4_200.0     # [J/(kg·K)]  Specific heat capacity
    coolant_U: float | None = None  # [J]         Internal energy (set in __init__)
    coolant_K: float = 2.2e9        # [Pa]        Bulk modulus of water
    coolant_alpha: float = 5e-4     # [1/K]       Thermal expansion coefficient


class SGPrimCold(ThermoNode):
    """
    Steam generator primary-side outlet plenum (cold header).
    """
    coolant_P: float = 15.1e6       # [Pa]        Pressure in SG primary outlet
    coolant_T: float = 540.0        # [K]         Coolant temperature
    coolant_m: float = 700.0        # [kg]        Coolant mass
    coolant_cp: float = 4_200.0     # [J/(kg·K)]  Specific heat capacity
    coolant_U: float | None = None  # [J]         Internal energy (set in __init__)
    coolant_K: float = 2.2e9        # [Pa]        Bulk modulus of water
    coolant_alpha: float = 5e-4     # [1/K]       Thermal expansion coefficient


class SGColdLeg(ThermoNode):
    """
    Small control volume representing the return header to the reactor.
    """
    coolant_P: float = 15.0e6       # [Pa]        Pressure in cold leg
    coolant_T: float = 545.0        # [K]         Coolant temperature
    coolant_m: float = 500.0        # [kg]        Coolant mass
    coolant_cp: float = 4_200.0     # [J/(kg·K)]  Specific heat capacity
    coolant_U: float | None = None  # [J]         Internal energy (set in __init__)
    coolant_K: float = 2.2e9        # [Pa]        Bulk modulus of water
    coolant_alpha: float = 5e-4     # [1/K]       Thermal expansion coefficient