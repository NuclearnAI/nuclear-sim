
# Import libraries
from nuclear_simulator.sandbox.plants.materials.base import Material
from nuclear_simulator.sandbox.plants.physics import (
    calc_volume_isobaric,
    calc_pressure_change_from_mass_energy,
    calc_temperature_from_energy,
    calc_energy_from_temperature
)



# Class for liquid at constant pressure
class IsobaricLiquid(Material):
    """
    Liquid at constant pressure with thermal expansion.
    """

    # Set class attributes
    ALPHA: float = None        # [1/K] Thermal expansion coefficient
    ALPHA_T: float = 273.15    # [K]   Reference temperature for expansion
    PRESSURE: float = None     # [Pa]  Constant reference pressure
    
    def __init__(self, m: float, U: float) -> None:
        """
        Initialize isobaric liquid with thermal expansion.
        
        Args:
            m: [kg] Mass
            U: [J]  Internal energy, referenced to 0K
            P: [Pa] Constant pressure
        
        Raises:
            ValueError: If required class variables not set or properties invalid
        """
        if self.ALPHA is None:
            raise ValueError(f"{type(self).__name__}: ALPHA must be set by subclass")
        if self.ALPHA_T is None:
            raise ValueError(f"{type(self).__name__}: ALPHA_T must be set by subclass")
        if self.PRESSURE is None:
            raise ValueError(f"{type(self).__name__}: PRESSURE must be set by subclass")
        T = calc_temperature_from_energy(U=U, m=m, cv=self.CP)
        V = calc_volume_isobaric(m=m, T=T, rho=self.rho, alpha=self.ALPHA, T_ref=self.ALPHA_T)
        super().__init__(m, U, V)
        return
    
    @classmethod
    def from_temperature(cls, m: float, T: float) -> 'IsobaricLiquid':
        """
        Initialize isobaric liquid from mass and temperature.
        Args:
            m: [kg] Mass
            T: [K] Temperature
        Returns:
            IsobaricLiquid: New isobaric liquid instance
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set by subclass")
        U = calc_energy_from_temperature(T=T, m=m, cv=cls.HEAT_CAPACITY)
        return cls(m, U)
    
    @property
    def alpha(self) -> float:
        """
        Thermal expansion coefficient [1/K].
        
        Returns:
            float: Thermal expansion coefficient of the liquid
        """
        return self.ALPHA
    
    @property
    def alpha_T(self) -> float:
        """
        Reference temperature for thermal expansion [K].
        
        Returns:
            float: Reference temperature for expansion
        """
        return self.ALPHA_T
    
    @property
    def P(self) -> float:
        """
        Pressure is constant for isobaric liquids.
        
        Returns:
            float: Constant reference pressure p_ref
        """
        return self.PRESSURE
    
    def __add__(self, other: 'IsobaricLiquid') -> 'IsobaricLiquid':
        """
        Add two isobaric liquids together. Conserves mass and energy.
        Args:
            other: Another isobaric liquid instance
        Returns:
            IsobaricLiquid: New liquid with combined properties
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot add materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        m_new = self.m + other.m
        U_new = self.U + other.U
        return type(self)(m_new, U_new)


# Class for liquid at constant volume
class IsovolumetricLiquid(Material):
    """
    Liquid with fixed volume and variable pressure.
    """
    
    ALPHA: float = None         # [1/K] Thermal expansion coefficient
    ALPHA_T: float = 273.15     # [K]   Reference temperature for expansion
    BULK_MODULUS: float = None  # [Pa]  Bulk modulus
    
    def __init__(self, m: float, U: float, P: float) -> None:
        """
        Initialize isovolumetric liquid with pressure tracking.
        
        Args:
            m: [kg] Mass
            U: [J] Internal energy, referenced to 0K
            V: [m³] Volume (fixed)
            P: [Pa] Initial pressure
        
        Raises:
            ValueError: If required class variables not set or properties invalid
        """
        if self.ALPHA is None:
            raise ValueError(f"{type(self).__name__}: ALPHA must be set by subclass")
        if self.ALPHA_T is None:
            raise ValueError(f"{type(self).__name__}: ALPHA_T must be set by subclass")
        if self.BULK_MODULUS is None:
            raise ValueError(f"{type(self).__name__}: BULK_MODULUS must be set by subclass")
        V = ...  # Calculate volume from m, U, P
        super().__init__(m, U, V)
    
    @classmethod
    def from_temperature_pressure(
            cls,
            m: float,
            T: float,
            P: float
        ) -> 'IsovolumetricLiquid':
        """
        Initialize isovolumetric liquid from temperature and pressure.
        
        Args:
            m: [kg] Mass
            T: [K] Temperature
            V: [m³] Volume (fixed)
            P: [Pa] Initial pressure
        
        Returns:
            IsovolumetricLiquid: New isovolumetric liquid instance
        
        Raises:
            ValueError: If required class variables not set
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set by subclass")
        U = calc_energy_from_temperature(T=T, m=m, cv=cls.HEAT_CAPACITY)
        return cls(m, U, V, P)
    
    def __add__(self, other: 'IsovolumetricLiquid') -> 'IsovolumetricLiquid':
        """
        Add two isovolumetric liquids with pressure update.
        
        Conserves mass and energy. Volume remains fixed (from left operand).
        Pressure is updated based on mass and temperature changes using the
        bulk modulus relationship.
        
        Args:
            other: Another isovolumetric liquid instance
        
        Returns:
            IsovolumetricLiquid: New liquid with updated pressure
        
        Raises:
            TypeError: If attempting to add incompatible material types
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot add materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        
        # Sum extrinsic properties
        m_new = self.m + other.m
        U_new = self.U + other.U
        V_new = self.V  # Volume stays fixed (left operand)
        
        # Calculate temperature change
        T_old = self.T
        T_new = calc_temperature_from_energy(U=U_new, m=m_new, cv=self.cp)
        dT = T_new - T_old
        
        # Calculate mass change
        dm = other.m
        
        # Calculate pressure change using bulk modulus
        dP = calc_pressure_change_from_mass_energy(
            m=self.m, dm=dm, dT=dT, K=self.BULK_MODULUS, alpha=self.ALPHA
        )
        P_new = self.P + dP
        
        # Return new instance with updated pressure
        return type(self)(m_new, U_new, V_new, P_new)
    



# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    ...
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")




  