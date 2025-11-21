
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional

# Import libraries
import math
import numpy as np
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.edges.base import TransferEdge



# Class for pipes
class TurbineEdge(TransferEdge):
    """
    A Turbine that converts fluid kinetic energy into electrical energy based on pressure difference.
    Attributes:
        v:                  [m/s]  Velocity of the fluid through the turbine
        A:                  [m²]   Effective cross-sectional area of the turbine blades
        M:                  [kg]   Effective mass of the turbine
        gamma:              [1/s]  Effective drag coefficient (converts kinetic energy to electrical energy)
        energy_output:      [J]    Total energy output produced by the turbine at this time step
        max_flow_fraction:  [1]    Maximum fraction of the fluid mass that can flow per time step
    """
    v: float = 0.0              # [m/s] Velocity of the fluid through the turbine
    A: float = 5.0              # [m²]  Effective cross-sectional area of the turbine blades
    M: float = 1000.0           # [kg]  Effective mass of the turbine
    gamma: float = 0.1          # [1/s] Effective drag coefficient (converts kinetic energy to electrical energy)
    _F: float = 0.0             # [N]   Force exerted by the fluid on the turbine this time step
    energy_output: float = 0.0  # [J]   Total energy output produced by the turbine
    max_flow_fraction: float = 0.1

    def __init__(self, m_dot=None, **data: Any) -> None:
        """
        Initialize turbine and set initial velocity based on mass flow rate if provided.
        Args:
            m_dot:  [kg/s] Initial mass flow rate through the turbine
        """

        # Call super init
        super().__init__(**data)

        # Set initial velocity if mass flow rate provided
        if m_dot is not None:
            fluid_src: Gas | Liquid = self.get_contents_source()
            fluid_tgt: Gas | Liquid = self.get_contents_target()
            rho = (fluid_src.rho + fluid_tgt.rho) / 2
            self.v = m_dot / (rho * self.A)

        # Done
        return

    def calculate_material_flow(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update.
        Returns:
            flows:  Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        fluid_src: Gas | Liquid = self.get_contents_source()
        fluid_tgt: Gas | Liquid = self.get_contents_target()
        P_src = self.get_field_source("P")
        P_tgt = self.get_field_target("P")

        # Get fluid properties
        if isinstance(fluid_src, Gas):
            fluid_type = Gas
        elif isinstance(fluid_src, Liquid):
            fluid_type = Liquid
        else:
            raise TypeError("Pipe material must be Gas or Liquid.")
        fluid_class = type(fluid_src)

        # Get effective force and workon fluid due to pressure difference
        F = (P_src - P_tgt) * self.A  # F = dP * A
        work = F * self.v * dt        # W = F * d = F * v * dt

        # Calculate mass flow rate based on velocity
        rho = (fluid_src.rho + fluid_tgt.rho ) / 2
        m_dot = rho * self.A * self.v

        # Calculate energy flow from mass flow minus work
        if m_dot >= 0:
            m_dot = min(m_dot, self.max_flow_fraction * fluid_src.m / dt)
            U_dot_flow = m_dot * (fluid_src.U / fluid_src.m)
        else:
            m_dot = max(m_dot, -self.max_flow_fraction * fluid_tgt.m / dt)
            U_dot_flow = m_dot * (fluid_tgt.U / fluid_tgt.m)

        # Calculate energy from mass flow minus work per time step
        U_dot = U_dot_flow - work / dt

        # Create liquid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Stash force for next update
        self._F = F

        # Return output
        return fluid_flow
    
    def update_from_state(self, dt: float) -> None:
        """
        Converts some of the turbine kinetic energy into energy output.
        Args:
            dt:     [s] Time step for the update.
        """

        # Update velocity based on force from fluid
        v = self.v + (self._F / self.M) * dt

        # Calculate kinetic energy
        K = 0.5 * self.M * v**2

        # Calculate energy converted this time step
        dU = K * (1 - np.exp(-self.gamma * dt))

        # Slow down turbine based on energy extracted
        K_new = K - dU
        v = math.copysign(math.sqrt(2 * K_new / self.M), v)

        # Update state
        self.v = v
        self.energy_output = dU

        # Done
        return



class LiquidTurbine(TurbineEdge):
    """A Turbine for liquids."""

class GasTurbine(TurbineEdge):
    """A Turbine for gases."""

