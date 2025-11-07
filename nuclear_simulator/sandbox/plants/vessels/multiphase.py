
# Define exports
__all__ = [
    "GasLiquidVessel"
]

# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.physics import calc_pressure_ideal_gas
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
        # Set volume if not provided
        if self.V is None:
            self.V = self.gas.V + self.liquid.V
        # Test
        self.update_from_state(dt=1)
        # Validate
        self.gas.validate()
        self.liquid.validate()
        # Done
        return
    
    @classmethod
    def from_temperature_pressure(
            cls,
            *,
            m_gas: float,
            m_liq: float,
            T: float,
            P: float,
            gas_cls: type[Gas] = Gas,
            liq_cls: type[Liquid] = Liquid,
            **data,
        ) -> GasLiquidVessel:
        """
        Construct a GasLiquidVessel from pressure, temperature, and mass inputs.

        Args:
            m_gas:      [kg]    Mass of gas
            m_liq:      [kg]    Mass of liquid
            T:          [K]     Common temperature of gas and liquid
            P:          [Pa]    Total pressure
            data:       [-]     Additional data for GasLiquidVessel constructor
        Returns:
            GasLiquidVessel instance
        """
        # Create gas and liquid materials
        gas = gas_cls.from_temperature_pressure(m=m_gas, T=T, P=P)
        liquid = liq_cls.from_temperature(m=m_liq, T=T)
        V = gas.V + liquid.V

        # Create vessel
        return cls(V=V, P=P, gas=gas, liquid=liquid, **data)

    # Add validation to update
    def update(self, dt):
        """
        Update method with validation.
        Args:
            dt: Time step size (s).
        """
        super().update(dt)
        self.gas.validate()
        self.liquid.validate()
        return

    def update_from_state(self, dt: float, steps: int = 1) -> None:
        """
        Advance the gas-liquid vessel by dt seconds.

        Converts any excess internal energy into phase change between liquid and gas.
        Uses a forward Euler sub-stepping approach to ensure stability.

        Args:
            dt: Time step size (s).
            steps: Number of sub-steps for integration.

        Modifies:
            Updates the gas and liquid internal energies and masses.
        """

        # Get constants
        V_tot   = self.V
        M_gas   = self.gas.MOLECULAR_WEIGHT
        rho_liq = self.liquid.DENSITY
        L       = self.liquid.LATENT_HEAT

        # Get materials
        gas: Gas = self.gas
        liq: Liquid = self.liquid

        # Step loop
        for i in range(steps):

            # Get current state
            P = self.P
            m_liq = liq.m
            U_liq = liq.U
            V_liq = liq.V
            m_gas = gas.m
            U_gas = gas.U
            V_gas = gas.V

            # Gas EOS and saturation
            T_sat     = liq.T_saturation(P)
            u_sat_liq = liq.u_saturation(T=T_sat)
            u_sat_gas = gas.u_saturation(T=T_sat)

            # Get energy excess / deficit relative to saturation
            E_boil = max(U_liq - m_liq * u_sat_liq, 0.0)  # J available to boil
            E_cond = max(m_gas * u_sat_gas - U_gas, 0.0)  # J available to condense

            # Compute mass to evaporate/condense this step
            alpha = 1.0 / steps
            dm_evap = alpha * (E_boil / L)
            dm_cond = alpha * (E_cond / L)

            # Update states
            m_liq = m_liq - dm_evap + dm_cond
            m_gas = m_gas + dm_evap - dm_cond
            # Energy transfer accounts for saturation energies, not just latent heat
            U_liq = U_liq - dm_evap * u_sat_liq + dm_cond * u_sat_gas
            U_gas = U_gas + dm_evap * u_sat_gas - dm_cond * u_sat_liq
            V_liq = m_liq / rho_liq
            V_gas = V_tot - V_liq

            # Recreate material states
            liq = self.liquid.__class__(m=m_liq, U=U_liq, V=V_liq)
            gas = self.gas.__class__(m=m_gas, U=U_gas, V=V_gas)
            liq.validate()
            gas.validate()

            # Update pressure
            P = gas.P_saturation(liq.T)

            # Check if T and P are physical
            if not (P > 0.0) or not (liq.T > 0.0) or not (gas.T > 0.0):
                raise ValueError(
                    f"{type(self).__name__}: Non-physical state reached during update: P={P:.3e} Pa."
                )

        # Set new states
        P_final_ideal = calc_pressure_ideal_gas(gas.m / M_gas, gas.T, gas.V)
        self.P      = P_final_ideal
        self.gas    = gas
        self.liquid = liq

        # Done
        return


# Test
def test_file():
    # Import libraries
    import math
    from nuclear_simulator.sandbox.materials.nuclear import PWRSecondaryWater, PWRSecondarySteam
    # Local dummy materials
    # Initial conditions
    m_liq   = 5000
    m_gas   = 500
    T       = PWRSecondarySteam.T0
    P       = PWRSecondarySteam.P0
    liq     = PWRSecondaryWater.from_temperature(m=m_liq, T=T)
    gas     = PWRSecondarySteam.from_temperature_pressure(m=m_gas, T=T, P=P)
    V_tot   = liq.V + gas.V
    # Build vessel
    vessel = GasLiquidVessel(V=V_tot, P=1.0e5, gas=gas, liquid=liq)
    # Conserved totals (before)
    m_tot_before = vessel.gas.m + vessel.liquid.m
    U_tot_before = vessel.gas.U + vessel.liquid.U
    V_tot_before = vessel.V
    # Run update
    dt = 1.0
    steps = 20
    vessel.update_from_state(dt=dt, steps=steps)
    # Check conserved totals (after)
    m_tot_after = vessel.gas.m + vessel.liquid.m
    U_tot_after = vessel.gas.U + vessel.liquid.U
    V_check     = vessel.gas.V + vessel.liquid.V
    P_check     = calc_pressure_ideal_gas(
        vessel.gas.m / vessel.gas.MOLECULAR_WEIGHT, vessel.gas.T, vessel.gas.V
    )
    # Assertions (tolerances generous for simple arithmetic)
    assert abs(m_tot_after - m_tot_before) < 1e-9, "Total mass not conserved"
    assert abs(U_tot_after - U_tot_before) < 1e-6, "Total energy not conserved"
    assert abs(V_check - V_tot_before)     < 1e-12, "Total volume not conserved"
    assert vessel.P > 0.0 and P_check > 0.0, "Pressure should be positive"
    for x in (vessel.gas.m, vessel.liquid.m, vessel.gas.U, vessel.liquid.U, vessel.P):
        assert math.isfinite(x)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

