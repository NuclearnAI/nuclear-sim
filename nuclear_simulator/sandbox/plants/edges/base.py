
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
from abc import abstractmethod
from nuclear_simulator.sandbox.graphs.edges import Edge


# Heat exchange edge
class TransferEdge(Edge):
    """
    Exchanges material between two node materials.

    Attributes:
        tag_material:       [-]    Tag of the material on each node to exchange between
        monodirectional:    [-]    If True, flow is only allowed from source to target.
        max_flow_fraction:  [-]    Maximum fraction of the material mass that can flow per time step
    """
    tag_material: str = "contents"
    monodirectional: bool = False
    max_flow_fraction: float = 0.05

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag_material",
        ]
    
    def get_contents_source(self) -> Material:
        """Get material from source node."""
        return self.get_field_source(self.tag_material)
    
    def get_contents_target(self) -> Material:
        """Get material from target node."""
        return self.get_field_target(self.tag_material)

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates material exchange between node_source and node_target.

        Args:
            dt:  [s]  Time step

        Returns:
            flows: Dict with flows keyed by tag_material
        """

        # Calculate material flow
        mat_flow = self.calculate_material_flow(dt)
        m_dot = mat_flow.m
        U_dot = mat_flow.U
        V_dot = mat_flow.V

        # Get materials
        mat_src: Material = self.get_contents_source()
        mat_tgt: Material = self.get_contents_target()

        # Get max allowable flows for m, U, V
        if m_dot >= 0:
            m_dot_max = mat_src.m / dt * self.max_flow_fraction
        else:
            m_dot_max = -mat_tgt.m / dt * self.max_flow_fraction
        if U_dot >= 0:
            U_dot_max = mat_src.U / dt * self.max_flow_fraction
        else:
            U_dot_max = -mat_tgt.U / dt * self.max_flow_fraction
        if V_dot >= 0:
            V_dot_max = mat_src.V / dt * self.max_flow_fraction
        else:
            V_dot_max = -mat_tgt.V / dt * self.max_flow_fraction

        # Enforce mono-directional flow if specified
        if self.monodirectional:
            m_dot_max = max(m_dot_max, 0.0)
            U_dot_max = max(U_dot_max, 0.0)
            V_dot_max = max(V_dot_max, 0.0)

        # Get scaling factor for max allowable flows
        scale = 1.0
        if abs(m_dot) > abs(m_dot_max):
            scale = min(scale, abs(m_dot_max / m_dot))
        if abs(U_dot) > abs(U_dot_max):
            scale = min(scale, abs(U_dot_max / U_dot))
        if abs(V_dot) > abs(V_dot_max):
            scale = min(scale, abs(V_dot_max / V_dot))

        # Scale flows if needed
        if scale < 1.0:
            mat_flow = mat_flow * scale

        # Package flows
        flows = {
            self.tag_material: mat_flow
        }

        # Return flows
        return flows

    @abstractmethod
    def calculate_material_flow(self, dt: float) -> Material:
        """
        Calculates material transfer between node_source and node_target.

        Args:
            dt:  [s]  Time step

        Returns:
            transfer: Material-like object carrying mass, U, V transferred
        """
        raise NotImplementedError("calculate_transfer must be implemented in subclasses.")

    