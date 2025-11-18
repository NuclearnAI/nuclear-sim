
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
        tag_material:  [-]    Tag of the material on each node to exchange between
    """
    tag_material: str = "contents"

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
        transfer = self.calculate_material_flow(dt)
        flows = {
            self.tag_material: transfer
        }
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

    