
# Import libraries
from abc import abstractmethod
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
    T: float  # Temperature
    U: float  # Internal energy
    dQ: float  # Heat transferred in/out
    dW: float  # Work done on/by system
    dH: float  # Enthalpy increase/decrease

    def __init__(
            self,
            id: Optional[int] = None,
            name: Optional[str] = None,
            **kwargs: dict[str, Any]
        ) -> None:
        # Add thermodynamic state variables to required fields
        kwargs['dQ'] = 0.0
        kwargs['dW'] = 0.0
        kwargs['dH'] = 0.0
        # Initialize base Node attributes
        super().__init__(id=id, name=name, **kwargs)
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
        self.T = self.calculate_temperature_from_U(self.U)
        # Reset flows for next tick
        self.dQ = 0.0
        self.dW = 0.0
        self.dH = 0.0
        return
    
    @abstractmethod
    def calculate_temperature_from_U(self, U: float) -> float:
        """
        Calculate temperature from internal energy.
        Args:
            U: Internal energy.
        Returns:
            Temperature corresponding to internal energy U.
        """
        raise NotImplementedError("Subclasses must implement calculate_temperature_from_U method")


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
        # Ensure no thermodynamic flows are set directly
        if ('T' in self.flows.keys()) or ('U' in self.flows.keys()):
            raise ValueError("Thermodynamic flows (U & T) cannot be set directly on ThermoEdge")
        # Done
        return
    
