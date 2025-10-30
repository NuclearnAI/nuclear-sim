
# Annotation imports
from typing import Any, Optional

# Import libraries
import copy
from nuclear_simulator.sandbox.graphs import Node, Edge, Controller, Signal, Graph
from nuclear_simulator.sandbox.plants.physics import (
    calc_energy_from_temperature, 
    calc_temperature_from_energy,
    calc_pressure_change_from_mass_energy,
)

# Expose classes for easy import
__all__ = ["ThermoNode", "Node", "Edge", "Controller", "Signal", "Graph"]


# Create node class for thermodynamic simulations
class ThermoNode(Node):
    """
    Node that will automatically convert temperature into energy.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize ThermoNode attributes.
        Args:
            **kwargs: Keyword arguments for base Node class.
        Modifies:
            Initializes Node as normal. Also automatically initializes any
            state variables ending in _U (internal energy) based on corresponding
            _T (temperature), _m (mass), and _cp (specific heat) variables.
        """

        # Initialize base Node attributes
        super().__init__(**kwargs)

        # Loop over fields
        for field in self.get_fields():

            # Check if ends in _U
            if field.endswith("_U"):

                # Get base name
                base_name = field[:-2]

                # Check for corresponding _T, m, cp fields
                T_field = f"{base_name}_T"
                m_field = f"{base_name}_m"
                cp_field = f"{base_name}_cp"

                # Check if all exist
                if all(f in self.get_fields() for f in [T_field, m_field, cp_field]):
                    # Initialize U based on T, m, cp
                    T = getattr(self, T_field)
                    m = getattr(self, m_field)
                    cp = getattr(self, cp_field)
                    U = calc_energy_from_temperature(T=T, m=m, cv=cp)
                    setattr(self, field, U)

        # Done
        return
    
    def update_from_state(self, dt: float) -> None:
        """
        Update all thermodynamic fields.
            - Update T based on corresponding energy.
            - Update P based on corresponding flows.
        Args:
            dt: Time step size (s).
        Modifies:
            Updates all thermodynamic state variables in place.
        """
        
        # Loop over fields
        for field in self.get_fields():

            # Update temperature fields to match energy
            if field.endswith("_T"):
                # Get base name
                base_name = field[:-2]
                # Get corresponding field names
                U_field = f"{base_name}_U"
                m_field = f"{base_name}_m"
                cp_field = f"{base_name}_cp"
                # Get variables
                U = getattr(self, U_field)
                m = getattr(self, m_field)
                cp = getattr(self, cp_field)
                # Update temperature
                T = calc_temperature_from_energy(
                    U=U, m=m, cv=cp
                )
                setattr(self, field, T)

            # Update pressure fields based on flows
            if field.endswith("_P"):
                # Get base name
                base_name = field[:-2]
                # Get corresponding field names
                m_field = f"{base_name}_m"
                U_field = f"{base_name}_U"
                T_field = f"{base_name}_T"
                K_field = f"{base_name}_K"
                cp_field = f"{base_name}_cp"
                alpha_field = f"{base_name}_alpha"
                # Get variables
                P_old = getattr(self, field)  # Current pressure
                m = getattr(self, m_field)
                U = getattr(self, U_field)
                T = getattr(self, T_field)
                K = getattr(self, K_field)
                cp = getattr(self, cp_field)
                alpha = getattr(self, alpha_field)
                dm = self.flows.get(m_field, 0.0) * dt
                dU = self.flows.get(U_field, 0.0) * dt
                m_old = m - dm
                U_old = U - dU
                T_old = calc_temperature_from_energy(U_old, m_old, cp)
                dT = T - T_old
                # Update pressure
                dP = calc_pressure_change_from_mass_energy(
                    m=m_old,
                    dm=dm,
                    dT=dT,
                    K=K,
                    alpha=alpha,
                )
                P = P_old + dP
                setattr(self, field, P)

        # Done
        return
    
