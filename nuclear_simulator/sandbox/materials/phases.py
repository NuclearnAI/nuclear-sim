
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
from nuclear_simulator.sandbox.physics.thermodynamics import (
    calc_energy_from_temperature,
    calc_temperature_from_energy,
)
from nuclear_simulator.sandbox.physics.boiling import (
    calc_boiling_temperature,
    calc_boiling_temperature_from_pressure,
    calc_boiling_pressure_from_temperature,
    calc_boiling_specific_energy_gas,
    calc_boiling_specific_energy_liquid,
    calc_boiling_mass_fraction_liquid,
    calc_boiling_energy_fraction_liquid,
    calc_boiling_volume_fraction_liquid,
)


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
        # u_bound = self.u0_BOUND + self.HEAT_CAPACITY_BOUND * (T - self.T0)
        u_bound = calc_energy_from_temperature(
            T=T,
            m=1.0,  # Unit mass for specific energy
            cv=self.HEAT_CAPACITY_BOUND,
            T0=self.T0,
            u0=self.u0_BOUND,
        )
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
    
    def calc_saturation_temperature(
            self, 
            m: float, 
            U: float, 
            V: float,
        ) -> float:
        """
        Calculate saturation temperature given mass, internal energy, and volume.
        Args:
            m:  [kg]      Total mass
            U:  [J]       Total internal energy
            V:  [m^3]     Total volume
        """
        raise NotImplementedError("calc_saturation_temperature method must be implemented in subclass.")


# Define boiling properties class
class BoilingProperties(PhaseChangeProperties):
    """
    Defines boiling phase change behavior.
    Attributes:
        T0:                     [K]         Reference temperature
        P0:                     [Pa]        Reference pressure
        u0_BOUND:               [J/kg]      Reference internal specific energy of bound phase at T0
        u0_UNBOUND:             [J/kg]      Reference internal specific energy of unbound phase at T0
        DENSITY_BOUND:          [kg/m^3]    Density of the bound state
        MOLECULAR_WEIGHT:       [kg/mol]    Molecular weight (for ideal gas calculations)
        HEAT_CAPACITY_BOUND:    [J/(kg·K)]  Specific heat capacity of bound phase
        HEAT_CAPACITY_UNBOUND:  [J/(kg·K)]  Specific heat capacity of unbound phase
    """
    DENSITY_BOUND: float
    MOLECULAR_WEIGHT: float

    @property
    def DENSITY_LIQUID(self):
        return self.DENSITY_BOUND

    @property
    def u0_LIQUID(self):
        return self.u0_BOUND

    @property
    def u0_GAS(self):
        return self.u0_UNBOUND
    
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
        # T0 = self.T0
        # P0 = self.P0
        # L = self.latent_heat(T0)
        # R = UNIVERSAL_GAS_CONSTANT / self.MOLECULAR_WEIGHT
        # T_sat = 1 / ((1 / T0) - (R / L) * math.log(P / P0))
        T_sat = calc_boiling_temperature_from_pressure(
            P=P,
            T0=self.T0,
            P0=self.P0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return T_sat
    
    def P_saturation(self, T: float) -> float:
        """
        Calculate saturation pressure at given temperature using Clausius-Clapeyron relation.
        Args:
            T:      [K]   Temperature
        Returns:
            P_sat:  [Pa]  Saturation pressure
        """
        # T0 = self.T0
        # P0 = self.P0
        # L = self.latent_heat(T0)
        # R = UNIVERSAL_GAS_CONSTANT / self.MOLECULAR_WEIGHT
        # P_sat = P0 * math.exp((L / R) * ((1 / T0) - (1 / T)))
        P_sat = calc_boiling_pressure_from_temperature(
            T=T,
            T0=self.T0,
            P0=self.P0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return P_sat

    def u_saturation_liquid(self, T):
        """
        Calculate internal specific energy of saturated liquid at temperature T.
        Args:
            T:  [K]  Temperature
        Returns:
            u_liquid:  [J/kg]  Internal specific energy of saturated liquid"""
        u_liq = calc_boiling_specific_energy_liquid(
            T=T,
            T0=self.T0,
            u0_liquid=self.u0_LIQUID,
            cv_liquid=self.HEAT_CAPACITY_LIQUID,
        )
        return u_liq
    
    def u_saturation_gas(self, T):
        """
        Calculate internal specific energy of saturated gas at temperature T.
        Args:
            T:  [K]  Temperature
        Returns:
            u_gas:  [J/kg]  Internal specific energy of saturated gas
        """
        u_gas = calc_boiling_specific_energy_gas(
            T=T,
            T0=self.T0,
            u0_gas=self.u0_GAS,
            cv_gas=self.HEAT_CAPACITY_GAS,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return u_gas
    
    def calc_saturation_temperature(
            self, 
            m: float, 
            U: float, 
            V: float,
        ) -> float:
        """
        Calculate liquid fraction given mass, internal energy, and volume.
        Args:
            m:  [kg]      Total mass
            U:  [J]       Total internal energy
            V:  [m^3]     Total volume
        Returns:
            liq_frac:  [-] Liquid mass fraction
        """
        T_eq = calc_boiling_temperature(
            m=m,
            U=U,
            V=V,
            T0=self.T0,
            P0=self.P0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            cv_liquid=self.HEAT_CAPACITY_LIQUID,
            rho_liquid=self.DENSITY_LIQUID,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return T_eq
    
    def calculate_mass_fraction_liquid(
            self,
            m: float,
            U: float,
            V: float,
            T_eq: float | None = None,
        ) -> float:
        """
        Calculate mass fraction of liquid phase given mass, internal energy, and volume.
        Args:
            m:     [kg]   Total mass
            U:     [J]    Total internal energy
            V:     [m^3]  Total volume
            T_eq:  [K]    Optional pre-computed saturation temperature
        Returns:
            xm:  [-]  Mass fraction of liquid phase
        """
        if T_eq is None:
            T_eq = self.calc_saturation_temperature(m=m, U=U, V=V)
        xm = calc_boiling_mass_fraction_liquid(
            T=T_eq,
            T0=self.T0,
            P0=self.P0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            rho_liquid=self.DENSITY_LIQUID,
            rho_average=m / V,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return xm
    
    def calculate_energy_fraction_liquid(
            self,
            m: float,
            U: float,
            V: float,
            T_eq: float | None = None,
        ) -> float:
        """
        Calculate energy fraction of liquid phase given mass, internal energy, and volume.
        Args:
            m:     [kg]   Total mass
            U:     [J]    Total internal energy
            V:     [m^3]  Total volume
            T_eq:  [K]    Optional pre-computed saturation temperature
        Returns:
            xe:  [-]  Energy fraction of liquid phase
        """
        if T_eq is None:
            T_eq = self.calc_saturation_temperature(m=m, U=U, V=V)
        xe = calc_boiling_energy_fraction_liquid(
            T=T_eq,
            T0=self.T0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            u_average=U / m,
            cv_liquid=self.HEAT_CAPACITY_LIQUID,
        )
        return xe
    
    def calculate_volume_fraction_liquid(
            self,
            m: float,
            U: float,
            V: float,
            T_eq: float | None = None,
        ) -> float:
        """
        Calculate volume fraction of liquid phase given mass, internal energy, and volume.
        Args:
            m:     [kg]   Total mass
            U:     [J]    Total internal energy
            V:     [m^3]  Total volume
            T_eq:  [K]    Optional pre-computed saturation temperature
        Returns:
            xv:  [-]  Volume fraction of liquid phase
        """
        if T_eq is None:
            T_eq = self.calc_saturation_temperature(m=m, U=U, V=V)
        xv = calc_boiling_volume_fraction_liquid(
            T=T_eq,
            T0=self.T0,
            P0=self.P0,
            u0_gas=self.u0_GAS,
            u0_liquid=self.u0_LIQUID,
            rho_liquid=self.DENSITY_LIQUID,
            rho_average=m / V,
            molecular_weight=self.MOLECULAR_WEIGHT,
        )
        return xv