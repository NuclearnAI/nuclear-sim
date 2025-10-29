
# Import libraries
from typing import Any, Optional
from nuclear_simulator.sandbox.graphs import Node, Edge, Controller, Signal, Graph

# Expose classes for easy import
__all__ = ["ThermoNode", "ThermoEdge", "Controller", "Signal", "Graph"]


# Create node class for thermodynamic simulations
class ThermoNode(Node):
    """
    Node with methods for updating thermodynamic state variables.
    State variables:
        T: Temperature
        U: Internal energy
        dQ: Heat transferred in/out at an instantaneous time step
        dW: Work done on/by system at an instantaneous time step
        dH: Enthalpy increase/decrease at an instantaneous time step
    """

    # Define instance attributes
    m: float  # Mass / Effective mass for temperature calculation
    cp: float  # Specific heat capacity
    T: float  # Temperature
    U: float  # Internal energy

    # Define flow attributes (for use during updates)
    dQ: float  # Heat transferred in/out
    dW: float  # Work done on/by system
    dH: float  # Enthalpy increase/decrease

    def __init__(
            self,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: Any
        ) -> None:
        # Add thermodynamic state variables to required fields
        kwargs['dQ'] = 0.0
        kwargs['dW'] = 0.0
        kwargs['dH'] = 0.0
        kwargs.setdefault('U', None)  # Temporary default to None
        # Initialize base Node attributes
        super().__init__(id=id, name=name, **kwargs)
        # Set internal energy
        if self.U is None:
            self.U = self.calculate_energy_from_temperature(self.T)
        # Done
        return

    def update(self, dt: float) -> None:
        """
        Update the node's state based on flows from incoming edges.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's state variables in place.
        """
        self.update_from_signals(dt)
        self.update_from_edges(dt)
        self.update_from_flows(dt)  # <-- Update from flows between updates from edges and state
        self.update_from_state(dt)
        return

    def update_from_flows(self, dt: float) -> None:
        """
        Update temperature based on energy.
        Args:
            dt: Time step for the update.
        Modifies:
            Updates the node's temperature state variable in place.
        """
        # Get energy flows
        dQ = self.dQ
        dW = self.dW
        dH = self.dH
        # Update internal energy
        dU = dQ - dW + dH
        self.U += dU * dt
        # Update temperature from internal energy
        self.T = self.calculate_temperature_from_energy(self.U)
        # Reset flows for next tick
        self.dQ = 0.0
        self.dW = 0.0
        self.dH = 0.0
        return
    
    def calculate_temperature_from_energy(self, U: float) -> float:
        """
        Calculate temperature from internal energy.
            T = U / (m * cp)
        Args:
            U: Internal energy.
        Returns:
            Temperature corresponding to internal energy U.
        """
        return U / (max(self.m, 1e-6) * max(self.cp, 1e-6))
    
    def calculate_energy_from_temperature(self, T: float) -> float:
        """
        Calculate internal energy from temperature.
            U = T * m * cp
        Args:
            T: Temperature.
        Returns:
            Internal energy corresponding to temperature T.
        """
        return T * max(self.m, 1e-6) * max(self.cp, 1e-6)


# Make edge class for thermodynamic simulations
class ThermoEdge(Edge):

    # Ensure that flows do not include thermodynamic quantities
    def update(self, dt: float) -> None:
        """
        Update the edge's internal state (if any) and compute flows for this tick.
        Args:
            dt: Time step size (s).
        Modifies:
            Updates self.flows with calculated flow values.
        """
        # Update as normal
        super().update(dt)
        # Validate flows
        if self.flows is None:
            # Ensure flows is not None
            raise ValueError("ThermoEdge flows have not been calculated")
        if ('T' in self.flows.keys()) or ('U' in self.flows.keys()):
            # Ensure no thermodynamic flows are set directly
            raise ValueError("Thermodynamic flows (U & T) cannot be set directly on ThermoEdge")
        # Done
        return
    
