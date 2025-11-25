
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
    """
    v: float = 0.0 
    A: float = 5.0 
    M: float = 1000.0
    gamma: float = 100.0
    energy_output: float = 0.0

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
            flows:  MaterialExchange with mass and energy flow rates.
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

        # Compute pressure drive force
        F_pressure = (P_src - P_tgt) * self.A                 # [N]  Pressure drive

        # Save old velocity for energy accounting
        v_old = self.v

        # Update turbine velocity with exact linear-drag solution
        if self.gamma > 0:
            tau = self.M / self.gamma                         # [s]  Drag time constant
            v_inf = F_pressure / self.gamma                   # [m/s] Steady-state velocity
            v_new = v_inf + (v_old - v_inf) * math.exp(-dt / tau)
        else:
            v_new = v_old + (F_pressure / self.M) * dt

        # Average velocity over step (for work / flow)
        v_avg = 0.5 * (v_old + v_new)

        # Pressure work extracted from fluid this step
        work_pressure = F_pressure * v_avg * dt              # [J]

        # Calculate mass flow rate based on velocity
        rho = (fluid_src.rho + fluid_tgt.rho) / 2
        m_dot = rho * self.A * v_avg

        # Calculate energy flow from mass flow minus pressure work
        if m_dot >= 0:
            U_dot_flow = m_dot * (fluid_src.U / fluid_src.m)
        else:
            U_dot_flow = m_dot * (fluid_tgt.U / fluid_tgt.m)

        # Calculate energy from mass flow minus work per time step
        U_dot = U_dot_flow - work_pressure / dt

        # Create liquid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Compute energy output
        K_old = 0.5 * self.M * v_old**2
        K_new = 0.5 * self.M * v_new**2
        dK = K_new - K_old
        energy_output = max(work_pressure - dK, 0.0)

        # Update turbine state
        self.v = v_new
        self.energy_output = energy_output
        
        # Return output
        return fluid_flow


class LiquidTurbine(TurbineEdge):
    """A Turbine for liquids."""

class GasTurbine(TurbineEdge):
    """A Turbine for gases."""


# four roses
# woodford reserve
# wild turkey
# bardstown
# *stitzel-weller
# makers mark
# limestone branch
# preservation
# bulleit
# jeptha creed 
# *willet
# *buffalo trace
