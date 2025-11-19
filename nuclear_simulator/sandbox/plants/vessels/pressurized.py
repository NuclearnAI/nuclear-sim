
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials import Gas, Liquid
from nuclear_simulator.sandbox.physics.gases import calc_volume_ideal_gas


# Define pressurizer node
class PressurizerVessel(Node):
    """
    A node with controllable pressure.
    Attributes:
        contents:   [-]   Fluid stored in the pressurizer
        P_setpoint: [Pa]  Desired pressure setpoint
        P:          [Pa]  Current pressure
    """
    contents: Liquid
    P: float | None = None
    P_setpoint: float | None = None

    def __init__(self, **data) -> None:
        """Initialize pressurizer vessel node."""

        # Call super init
        super().__init__(**data)

        # Set initial pressure if not set
        if (self.P is None) and (self.P_setpoint is None):
            raise ValueError("PressurizerVessel requires P or P_setpoint to be set.")
        elif self.P is None:
            self.P = self.P_setpoint
        elif self.P_setpoint is None:
            self.P_setpoint = self.P

        # Done
        return
    
    def update_from_state(self, dt):
        self.P = self.P_setpoint
        return


# Define pressurized liquid vessel node
class PressurizedLiquidVessel(Node):
    """
    A node representing a pressurized vessel containing a liquid.
    Attributes:
        contents: [-]      Liquid stored in the vessel
        P:        [Pa]     Current pressure
        V0:       [m^3]    Optional reference volume for pressure calculation
        P0:       [Pa]     Optional reference pressure for pressure calculation
        dP_dV:    [Pa/m^3] Optional reference stiffness for pressure calculation
    """
    contents: Liquid
    P: float
    V0: float | None = None
    P0: float | None = None
    dP_dV: float | None = None

    def __init__(self, **data) -> None:
        """Initialize pressurized vessel node."""

        # Call super init
        super().__init__(**data)

        # Set derived attributes
        if self.P0 is None:
            # Default reference pressure to initial pressure
            self.P0 = self.P
        if self.V0 is None:
            # Default reference volume to initial volume
            self.V0 = self.contents.V
        if self.dP_dV is None:
            # Default stiffness to 1% change in volume -> 10% change in pressure
            self.dP_dV = 10.0 * self.P0 / self.V0

        # Done
        return

    def update_from_state(self, dt: float) -> None:
        """
        Advance the vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the vessel pressure `P`.
        """
        self.P = self.P0 + self.dP_dV * (self.contents.V - self.V0)
        return


# Define pressurized gas vessel node
class PressurizedGasVessel(Node):
    """
    A node representing a pressurized vessel containing a gas.
    Attributes:
        contents: [-]      Gas stored in the vessel
        P:        [Pa]     Current pressure
        V0:       [m^3]    Optional reference volume for pressure calculation
    """
    contents: Gas
    P: float
    V0: float | None = None

    def __init__(self, **data) -> None:
        """Initialize pressurized vessel node."""

        # Call super init
        super().__init__(**data)

        # Set derived attributes
        if self.V0 is None:
            # Calculate reference volume from initial pressure
            self.V0 = calc_volume_ideal_gas(
                n=self.contents.mols,
                T=self.contents.T,
                P=self.P
            )

        # Done
        return

    def update_from_state(self, dt: float) -> None:
        """
        Advance the vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the vessel pressure `P`.
        """
        try:
            self.P = self.contents.P
        except Exception as e:
            raise ValueError("Failed to compute gas pressure during vessel update.") from e
        return


# Test
def test_file():
    # Create liquid
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 500.0
        DENSITY = 8000.0
    liquid = DummyLiquid(m=1000.0, U=1e6)
    # Create vessel
    vessel = PressurizedLiquidVessel(contents=liquid, P=2e7)
    # Update
    vessel.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

