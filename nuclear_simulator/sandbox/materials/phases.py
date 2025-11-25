
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials.base import Material
    from nuclear_simulator.sandbox.materials.gases import Gas
    from nuclear_simulator.sandbox.materials.solids import Solid
    from nuclear_simulator.sandbox.materials.liquids import Liquid

# Import libraries
import math
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


# Define phase behavior base class
class PhaseChangeProperties:
    """
    Base class for defining phase change behavior of materials.
    Attributes:
        T0:                     [K]    Reference temperature
        P0:                     [Pa]   Reference pressure
        u0_BOUND:               [J/kg] Reference internal specific energy of bound phase at T0
        u0_UNBOUND:             [J/kg] Reference internal specific energy of unbound phase at T0
        HEAT_CAPACITY_BOUND:    [J/(kg·K)]  Specific heat capacity of bound phase
        HEAT_CAPACITY_UNBOUND:  [J/(kg·K)]  Specific heat capacity of unbound phase
    """
    T0: float
    P0: float
    u0_BOUND: float
    u0_UNBOUND: float
    HEAT_CAPACITY_BOUND: float
    HEAT_CAPACITY_UNBOUND: float | None = None

    def latent_heat(self, T) -> float:
        """
        Latent heat of phase change at reference point.
        Args:
            T:  [K]  Temperature
        Returns:
            L:  [J/kg]  Latent heat
        """
        return self.u0_UNBOUND - self.u0_BOUND
    
    def T_saturation(self, P: float) -> float:
        """
        Calculate saturation temperature at given pressure.
        Args:
            P:  [Pa]  Pressure
        Returns:
            T_sat:  [K]  Saturation temperature
        """
        raise NotImplementedError("T_saturation method must be implemented in subclass.")


    def P_saturation(self, T: float) -> float:
        """
        Calculate saturation pressure at given temperature.
        Args:
            T:  [K]  Temperature
        Returns:
            P_sat:  [Pa]  Saturation pressure
        """
        raise NotImplementedError("P_saturation method must be implemented in subclass.")

    def u_saturation_bound(self, T: float) -> float:
        """
        Calculate internal specific energy of bound phase at saturation.
        Args:
            T:  [K]  Temperature
        Returns:
            u_bound:  [J/kg]  Internal specific energy of bound phase
        """
        u_bound = self.u0_BOUND + self.HEAT_CAPACITY_BOUND * (T - self.T0)
        return u_bound
    
    def u_saturation_unbound(self, T: float) -> float:
        """
        Calculate internal specific energy of unbound phase at saturation.
        Args:
            T:  [K]  Temperature
        Returns:
            u_unbound:  [J/kg]  Internal specific energy of unbound phase
        """
        u_unbound = self.latent_heat(T) + self.u_saturation_bound(T)
        return u_unbound


# Define boiling properties class
class BoilingProperties(PhaseChangeProperties):
    """
    Defines boiling phase change behavior.
    Attributes:
        T0:                     [K]    Reference temperature
        P0:                     [Pa]   Reference pressure
        u0_BOUND:               [J/kg] Reference internal specific energy of bound phase at T0
        u0_UNBOUND:             [J/kg] Reference internal specific energy of unbound phase at T0
        MOLECULAR_WEIGHT:       [kg/mol]    Molecular weight (for ideal gas calculations)
        HEAT_CAPACITY_BOUND:    [J/(kg·K)]  Specific heat capacity of bound phase
        HEAT_CAPACITY_UNBOUND:  [J/(kg·K)]  Specific heat capacity of unbound phase
    """
    MOLECULAR_WEIGHT: float
    
    @property
    def HEAT_CAPACITY_GAS(self):
        return self.HEAT_CAPACITY_UNBOUND
    
    @property
    def HEAT_CAPACITY_LIQUID(self):
        return self.HEAT_CAPACITY_BOUND

    def T_saturation(self, P: float) -> float:
        """
        Calculate saturation temperature at given pressure using Clausius-Clapeyron relation.
        Args:
            P:      [Pa] Pressure
        Returns:
            T_sat:  [K]  Saturation temperature
        """
        T0 = self.T0
        P0 = self.P0
        L = self.latent_heat(T0)
        R = UNIVERSAL_GAS_CONSTANT / self.MOLECULAR_WEIGHT
        T_sat = 1 / ((1 / T0) - (R / L) * math.log(P / P0))
        return T_sat
    
    def P_saturation(self, T: float) -> float:
        """
        Calculate saturation pressure at given temperature using Clausius-Clapeyron relation.
        Args:
            T:      [K]   Temperature
        Returns:
            P_sat:  [Pa]  Saturation pressure
        """
        T0 = self.T0
        P0 = self.P0
        L = self.latent_heat(T0)
        R = UNIVERSAL_GAS_CONSTANT / self.MOLECULAR_WEIGHT
        P_sat = P0 * math.exp((L / R) * ((1 / T0) - (1 / T)))
        return P_sat

    def u_saturation_liquid(self, T):
        """
        Calculate internal specific energy of saturated liquid at temperature T.
        Args:
            T:  [K]  Temperature
        Returns:
            u_liquid:  [J/kg]  Internal specific energy of saturated liquid"""
        return self.u_saturation_bound(T)
    
    def u_saturation_gas(self, T):
        """
        Calculate internal specific energy of saturated gas at temperature T.
        Args:
            T:  [K]  Temperature
        Returns:
            u_gas:  [J/kg]  Internal specific energy of saturated gas
        """
        return self.u_saturation_unbound(T)
    
    