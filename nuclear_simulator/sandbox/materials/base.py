
# Annotation imports
from __future__ import annotations

# Import libraries
from numbers import Number
from nuclear_simulator.sandbox.physics import (
    calc_temperature_from_energy,
    calc_energy_from_temperature,
    calc_saturation_temperature,
    calc_saturation_pressure,
)


# Define base Material class
class Material:
    """
    Base class for all materials.
    Attributes:
        m:                [kg]       Mass
        U:                [J]        Internal energy, referenced to 0K
        V:                [m³]       Volume
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat capacity
        P0:               [Pa]       Reference pressure for calculations
        T0:               [K]        Reference temperature for calculations
        u0:               [J/kg]     Reference internal specific energy at T0
        LATENT_HEAT:      [J/kg]     Latent heat of vaporization at reference T0 and P0
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight

    """
    
    # Class variables - Material constants (must be set by subclasses)
    HEAT_CAPACITY: float | None = None

    # Optional attributes for saturation calculations
    P0: float | None = None
    T0: float | None = None
    u0: float | None = None
    LATENT_HEAT: float | None = None
    MOLECULAR_WEIGHT: float | None = None
    
    def __init__(self, m: float, U: float, V: float) -> None:
        """
        Initialize material with extrinsic properties directly.
        Args:
            m:        [kg]  Mass
            U:        [J]   Internal energy, referenced to 0K
            V:        [m³]  Volume
        """
        self.m = m
        self.U = U
        self.V = V
    
    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(m={self.m:.3e} kg, U={self.U:.3e} J, V={self.V:.3e} m³)"
        )
    
    def __add__(self, other) -> Material:
        if (type(self) == type(other)) or isinstance(other, Energy):
            m = self.m + other.m
            U = self.U + other.U
            V = self.V + other.V
            return type(self)(m=m, U=U, V=V)
        else:
            return NotImplemented
        
    def __radd__(self, other):
        if isinstance(other, Material):
            return self.__add__(other)
        elif isinstance(other, Number) and (other == 0):
            return self
        else:
            return NotImplemented
    
    def __sub__(self, other: Material) -> Material:
        if isinstance(other, Material):
            return self.__add__(-other)
        else:
            return NotImplemented
        
    def __rsub__(self, other):
        if isinstance(other, Material):
            return other.__add__(-self)
        else:
            return NotImplemented

    def __mul__(self, other) -> Material:
        if isinstance(other, Number):
            m = self.m * other
            U = self.U * other
            V = self.V * other
            return type(self)(m=m, U=U, V=V)
        else:
            return NotImplemented
    
    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other) -> Material:
        if isinstance(other, Number):
            return self.__mul__(1.0 / other)
        else:
            return NotImplemented

    def __neg__(self) -> Material:
        m = - self.m
        U = - self.U
        V = - self.V
        return type(self)(m=m, U=U, V=V)
    
    def __pos__(self) -> Material: 
        m = self.m
        U = self.U
        V = self.V
        return type(self)(m=m, U=U, V=V)
    
    def __abs__(self) -> Material: 
        m = abs(self.m)
        U = abs(self.U)
        V = abs(self.V)
        return type(self)(m=m, U=U, V=V)
    
    def validate(self) -> None:
        """
        Ensure all base properties are physically reasonable.
        """
        if self.m < 0:
            raise ValueError(f"Mass must be positive: {self.m:.2f} kg")
        if self.U < 0:
            raise ValueError(f"Internal energy must be non-negative: {self.U:.2f} J")
        if self.V < 0:
            raise ValueError(f"Volume must be positive: {self.V:.2f} m³")
        if any(x==0 for x in [self.m, self.U, self.V]) and any(x!=0 for x in [self.m, self.U, self.V]):
            raise ValueError(
                f"Mass, internal energy, and volume must all be zero or all be positive: "
                f"m={self.m:.2f} kg, U={self.U:.2f} J, V={self.V:.6f} m³"
            )
        return
    
    def _validate_saturation(self) -> None:
        """
        Ensure saturation calculation parameters are set.
        """
        if self.HEAT_CAPACITY is None:
            raise ValueError(f"{type(self).__name__}: HEAT_CAPACITY must be set by subclass")
        if self.LATENT_HEAT is None:
            raise ValueError(f"{type(self).__name__}: LATENT_HEAT must be set.")
        if self.P0 is None:
            raise ValueError(f"{type(self).__name__}: P0 must be set.")
        if self.T0 is None:
            raise ValueError(f"{type(self).__name__}: T0 must be set.")
        if self.u0 is None:
            raise ValueError(f"{type(self).__name__}: u0 must be set.")
        if self.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{type(self).__name__}: MOLECULAR_WEIGHT must be set.")
        return

    @classmethod
    def from_temperature(cls, m: float, T: float, **kwargs) -> Material:
        """
        Initialize from temperature instead of energy.
        
        Args:
            m:      [kg] Mass
            T:      [K]  Temperature
            kwargs: [-]  Additional arguments for subclass constructor
        
        Returns:
            Material: New material instance initialized from temperature
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set.")
        cv = cls.HEAT_CAPACITY
        T0 = cls.T0 or 0.0
        u0 = cls.u0 or 0.0
        U = calc_energy_from_temperature(T=T, m=m, cv=cv, T0=T0, u0=u0)
        return cls(m, U, **kwargs)
    
    @property
    def cv(self) -> float:
        """
        Specific heat capacity [J/(kg·K)].
        
        Returns:
            float: Specific heat capacity of the material
        """
        if self.HEAT_CAPACITY is None:
            raise ValueError(f"{type(self).__name__}: HEAT_CAPACITY must be set.")
        return self.HEAT_CAPACITY

    @property
    def T(self) -> float:
        """
        Temperature [K], computed from internal energy.
        
        Returns:
            float: Temperature computed from U, m, and cp
        """
        U = self.U
        m = self.m
        cv = self.cv
        T0 = self.T0 or 0.0
        u0 = self.u0 or 0.0
        T = calc_temperature_from_energy(U, m, cv, T0=T0, u0=u0)
        return T

    @property
    def rho(self) -> float:
        """
        Density [kg/m³], computed from mass and volume.
        
        Returns:
            float: Density computed from m and V
        """
        return self.m / self.V
    
    @property
    def MW(self) -> float:
        """
        Molecular weight [kg/mol].
        Returns:
            float: Molecular weight
        """
        if self.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{type(self).__name__}: MOLECULAR_WEIGHT must be set.")
        return self.MOLECULAR_WEIGHT
    
    def T_saturation(self, P: float) -> float:
        """
        Saturation temperature [K] at current pressure.
        Args:
            P: Pressure [Pa]
        Returns:
            float: Saturation temperature
        """
        self._validate_saturation()
        T_sat = calc_saturation_temperature(
            P=P,
            L=self.LATENT_HEAT,
            P0=self.P0,
            T0=self.T0,
            M=self.MOLECULAR_WEIGHT,
        )
        return T_sat
    
    def P_saturation(self, T: float) -> float:
        """
        Saturation pressure [Pa] at current temperature.
        Args:
            T: Temperature [K]
        Returns:
            float: Saturation pressure
        """
        self._validate_saturation()
        P_sat = calc_saturation_pressure(
            T=T,
            L=self.LATENT_HEAT,
            P0=self.P0,
            T0=self.T0,
            M=self.MOLECULAR_WEIGHT,
        )
        return P_sat

    def u_saturation(self, T: float) -> float:
        """
        Specific internal energy [J/kg] at given T.
        Args:
            T: Temperature [K]
        Returns:
            float: Specific internal energy [J/kg]
        """
        u_sat = calc_energy_from_temperature(
            T=T,
            m=1.0,  # unit mass for specific energy
            cv=self.cv,
            T0=self.T0 or 0.0,
            u0=self.u0 or 0.0,
        )
        return u_sat


# Define Energy material class
class Energy(Material):
    """
    Material that carries only internal energy (no mass or volume).
    """

    def __init__(self, U: float, **_) -> None:
        """
        Initialize energy-only material.

        Args:
            U: [J] Internal energy
        """
        super().__init__(m=0.0, U=U, V=0.0)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(U={self.U:.3e} J)"
    
    def __neg__(self):
        return Energy(U=-self.U)
    
    def __pos__(self):
        return Energy(U=+self.U)
    
    def __abs__(self):
        return Energy(U=abs(self.U))

    def __add__(self, other):
        if isinstance(other, Energy):
            return Energy(U=self.U + other.U)
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, Energy):
            return Energy(U=self.U + other.U)
        elif isinstance(other, Number) and (other == 0):
            return self
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Energy):
            return Energy(U=self.U - other.U)
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, Energy):
            return Energy(U=other.U - self.U)
        elif isinstance(other, Number) and (other == 0):
            return Energy(U=-self.U)
        else:
            return NotImplemented

    def __mul__(self, k): 
        if isinstance(k, Number):
            return Energy(U=self.U * k)
        else:
            return NotImplemented
        
    def __rmul__(self, k):
        return self.__mul__(k)

    def __truediv__(self, k):
        if isinstance(k, Number):
            return Energy(U=self.U / k)
        else:
            return NotImplemented
    



# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyMaterial(Material):
        HEAT_CAPACITY = 1000.0
    # Instantiate
    mata = DummyMaterial(m=10.0, U=1e6, V=0.01)
    matb = DummyMaterial(m=10.0, U=2e6, V=0.02)
    # Test addition
    matc = mata + matb
    assert matc.m == 20.0
    assert matc.U == 3e6
    assert matc.V == 0.03
    # Test subtraction
    matd = matc - mata
    assert matd.m == 10.0
    assert matd.U == 2e6
    # Test multiplication
    mate = mata * 2.0
    assert mate.m == 20.0
    assert mate.U == 2e6
    # Test division
    matf = mate / 2.0
    assert matf.m == 10.0
    assert matf.U == 1e6
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

