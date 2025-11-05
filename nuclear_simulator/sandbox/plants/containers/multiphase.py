
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid


# Define gas-liquid vessel node
class GasLiquidVessel(Node):
    """
    A node representing a fixed volume vessel containing a gas-liquid mixture.
    Attributes:
        V:      [m^3]   Baseline volume for pressure calculation
        P:      [Pa]    Baseline pressure for pressure calculation
        gas:    [-]     Gas stored in the vessel
        liquid: [-]     Liquid stored in the vessel
    """
    V: float | None = None
    P: float
    gas: Gas
    liquid: Liquid

    def __init__(self, **data) -> None:
        """Initialize gas-liquid vessel node."""
        # Call super init
        super().__init__(**data)
        # Set baseline volume if not provided
        if self.V is None:
            self.V = self.gas.V + self.liquid.V
        # Done
        return
    
    def update_from_state(self, dt: float) -> None:
        """
        Advance the gas-liquid vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates nothing by default.
        """
        # By default, do nothing
        return


# Pressure controlled gas-liquid vessel
class PressureControlledGasLiquidVessel(GasLiquidVessel):
    """
    A gas-liquid vessel node with pressure control.
    Attributes:
        P: float  [Pa] Pressure maintained in the vessel
    """

    P: float

    def update_from_state(self, dt: float) -> None:
        """
        Advance the gas-liquid vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the gas and liquid internal energies to maintain saturation.
        """

        # Get saturation properties
        P = self.P
        T_sat = self.liquid.T_saturation(P)
        u_liq = self.liquid.u_sie(T=T_sat, P=P)
        u_gas = self.gas.u_sie(T=T_sat, P=P)

        # Get total mass and energy
        m_total = self.gas.m + self.liquid.m
        U_total = self.gas.U + self.liquid.U
        if m_total <= 0 or U_total <= 0:
            raise ValueError("Total mass and internal energy must be positive.")

        # Get gas-liquid mass fractions
        frac_gas = ((U_total / m_total) - u_liq) / (u_gas - u_liq)

        # Clamp between 0 and 1
        frac_gas = max(0.0, min(1.0, frac_gas))
        frac_liq = 1.0 - frac_gas

        # Update liquid and gas properties
        m_liq = frac_liq * m_total
        m_gas = frac_gas * m_total
        U_liq = m_liq * u_liq
        U_gas = m_gas * u_gas

        # Set new material states
        self.liquid = self.liquid.__class__(m=m_liq, U=U_liq)
        self.gas = self.gas.__class__.from_pressure(m=m_gas, U=U_gas, P=P)

        # Done
        return
    
    @classmethod
    def from_temperature_pressure_mass(
            cls,
            T: float,
            P: float,
            m: float,
            gas_type: type[Gas],
            liquid_type: type[Liquid],
        ) -> PressureControlledGasLiquidVessel:
        """
        Create a PressureControlledGasLiquidVessel from temperature, pressure, and total mass.
        Args:
            T: Temperature (K)
            P: Pressure (Pa)
            m: Total mass (kg)
            liquid_type: Type of liquid to use
            gas_type: Type of gas to use
        Returns:
            PressureControlledGasLiquidVessel: Initialized vessel
        """
        
        # Create liquid and gas at half mass each
        liq = liquid_type.from_temperature(m=m/2, T=T)
        gas = gas_type.from_temperature_pressure(m=m/2, T=T)

        # Initialize vessel
        vessel = cls(P=P, gas=gas, liquid=liq)

        # Update to correct state
        vessel.update_from_state(dt=0.0)

        # Return vessel
        return vessel
        



# Test
def test_file():
    # Import libraries
    ...
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

