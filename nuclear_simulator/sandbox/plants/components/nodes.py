
# Annotation imports
from __future__ import annotations

# Import libraries
from nuclear_simulator.sandbox.plants.thermograph import ThermoNode


class CoreFuel(ThermoNode):
    """
    Fuel solid thermal mass (no fluid here).
    States: T, U, dQ, dW, dH  (+ m, cp)
    """
    m: float = 1_000.0        # [kg]       Effective fuel thermal mass
    cp: float = 300.0         # [J/(kg·K)] Effective solid cp (ballpark for UO2/structure)
    P: float = 1.55e7         # [Pa]       Pressure (155 bar)


class CoreCoolant(ThermoNode):
    """
    Primary-loop coolant control volume (in core/loop).
    """
    m: float = 10_000.0       # [kg]       Coolant mass in core/loop
    cp: float = 4_200.0       # [J/(kg·K)] Effective solid cp (water-ish)
    P: float = 1.55e7         # [Pa]       Pressure (155 bar)


class Pressurizer(ThermoNode):
    """
    Pressurizer lumped thermal mass (liquid + metal + some vapor).
    Using a single effective m and cp for first pass.
    """
    m: float = 3_000.0        # [kg]       Effective thermal mass
    cp: float = 4_000.0       # [J/(kg·K)] Effective thermal capacity
    P: float = 1.55e7         # [Pa]       Pressure (155 bar)


class SGPrimary(ThermoNode):
    """
    Steam Generator primary-side inventory (tube side).
    """
    m: float = 8_000.0        # [kg]       Coolant mass in SG primary side
    cp: float = 4_200.0       # [J/(kg·K)] Effective solid cp (water-ish)
    P: float = 1.55e7         # [Pa]       Pressure (155 bar)


class SGSecondary(ThermoNode):
    """
    Steam Generator secondary-side inventory (shell side).
    Includes steam quality x for convenience (0-1).
    """
    m: float = 6_000.0        # [kg]       Coolant mass in SG secondary side
    cp: float = 3_500.0       # [J/(kg·K)] Effective cp for mix (placeholder)
    P: float = 6.0e6          # [Pa]       Pressure (60 bar)
    x: float = 0.0            # [unitless] Steam quality


class SteamHeader(ThermoNode):
    """
    Main steam header/plenum upstream of the turbine.
    """
    m: float = 1_000.0        # [kg]       Steam mass in header
    cp: float = 2_500.0       # [J/(kg·K)] Steam-ish effective cp
    P: float = 6.0e6          # [Pa]       Pressure (60 bar)
    x: float = 1.0            # [unitless] Steam quality


class CondenserShell(ThermoNode):
    """
    Condenser shell side (steam condensing on tubes).
    """
    m: float = 5_000.0        # [kg]       Steam mass in condenser shell
    cp: float = 4_200.0       # [J/(kg·K)] Effective cp for mix (placeholder)
    P: float = 0.06e6         # [Pa]       Pressure (0.06 MPa)


class FeedwaterHeader(ThermoNode):
    """
    Feedwater collection header (liquid water).
    """
    m: float = 2_000.0        # [kg]       Water mass in feedwater header
    cp: float = 4_200.0       # [J/(kg·K)] Effective cp for water
    P: float = 7.0e6          # [Pa]       Pressure (70 bar)


class CoolingReservoir(ThermoNode):
    """
    Ultimate heat sink (cooling water basin/river loop).
    """
    m: float = 100_000.0      # [kg]       Large thermal mass
    cp: float = 4_200.0       # [J/(kg·K)] Effective cp for water
    P: float = 1.01e5         # [Pa]       Pressure (atmospheric)

