
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
    Material constants:
        DENSITY:          [kg/m³]    Density (optional, can be computed from m/V)
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat capacity
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight
        LATENT_HEAT:      [J/kg]     Latent heat of vaporization at reference T0 and P0
        P0:               [Pa]       Reference pressure for calculations
        T0:               [K]        Reference temperature for calculations
        u0:               [J/kg]     Reference internal specific energy at T0
    """
    
    # Material constants
    DENSITY: float | None = None
    HEAT_CAPACITY: float | None = None
    MOLECULAR_WEIGHT: float | None = None
    LATENT_HEAT: float | None = None
    P0: float | None = None
    T0: float | None = None
    u0: float | None = None
    
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
        if (type(self) == type(other)) or isinstance(other, MaterialExchange):
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
            # return other.__add__(-self)
            return (-self).__add__(other)
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
        cv = self.HEAT_CAPACITY
        if cv is None:
            raise ValueError(f"{type(self).__name__}: HEAT_CAPACITY must be set.")
        return cv
    
    @property
    def cp(self) -> float:
        """
        Specific heat capacity [J/(kg·K)].
        
        Returns:
            float: Specific heat capacity of the material
        """
        cv = self.cv
        return cv  # Default: cp ~= cv; override in subclasses if needed

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
        if T <= 0.0:
            raise ValueError(f"Temperature must be positive: {T:.2f} K")
        return T

    @property
    def rho(self) -> float:
        """
        Density [kg/m³], computed from mass and volume.
        
        Returns:
            float: Density computed from m and V
        """
        if self.DENSITY is None:
            rho = self.m / self.V
        else:
            rho = self.DENSITY
        if rho <= 0.0:
            raise ValueError(f"Density must be positive: {rho:.2f} kg/m³")
        return rho
    
    @property
    def MW(self) -> float:
        """
        Molecular weight [kg/mol].
        Returns:
            float: Molecular weight
        """
        MW = self.MOLECULAR_WEIGHT
        if MW is None:
            raise ValueError(f"{type(self).__name__}: MOLECULAR_WEIGHT must be set.")
        return MW
    
    @property
    def mols(self) -> float:
        """
        Number of moles [mol].
        Returns:
            float: Number of moles
        """
        n = self.m / self.MW
        if n < 0.0:
            raise ValueError(f"Number of moles must be non-negative: {n:.2f} mol")
        return n
    
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
            MW=self.MOLECULAR_WEIGHT,
        )
        if T_sat <= 0.0:
            raise ValueError(f"Saturation temperature must be positive: {T_sat:.2f} K")
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
            MW=self.MOLECULAR_WEIGHT,
        )
        if P_sat <= 0.0:
            raise ValueError(f"Saturation pressure must be positive: {P_sat:.2f} Pa")
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
        if u_sat <= 0.0:
            raise ValueError(
                f"Saturation specific internal energy must be positive: {u_sat:.2f} J/kg"
            )
        return u_sat
    
    def v_saturation(self, T: float) -> float:
        """
        Specific volume [m³/kg] at given T.
        Args:
            T: Temperature [K]
        Returns:
            float: Specific volume [m³/kg]
        """
        rho = self.rho
        v_sat = 1.0 / rho
        if v_sat <= 0.0:
            raise ValueError(
                f"Saturation specific volume must be positive: {v_sat:.6f} m³/kg"
            )
        return v_sat


# Define Energy material class
class MaterialExchange(Material):
    """
    Material used for energy/mass/volume exchanges between materials.
    """

    # Override init to default properties to zero
    def __init__(self, m: float=0.0, U: float=0.0, V: float=0.0) -> None:
        """
        Initialize material exchange.
        Args:
            m:        [kg]  Mass
            U:        [J]   Internal energy
            V:        [m³]  Volume
        """
        self.m = m
        self.U = U
        self.V = V

    # Override addition to only sum like types
    def __add__(self, other):
        if type(self) == type(other):
            return type(self)(
                m=self.m + other.m,
                U=self.U + other.U,
                V=self.V + other.V
            )
        elif isinstance(other, MaterialExchange):
            # Allow addition of different MaterialExchange types
            return MaterialExchange(
                m=self.m + other.m,
                U=self.U + other.U,
                V=self.V + other.V
            )
        else:
            return NotImplemented
        
class Energy(MaterialExchange):
    """
    Material with only internal energy (no mass or volume).
    """
    def __init__(self, U: float, **_) -> None:
        """
        Initialize energy exchange material.
        Args:
            U:        [J]   Internal energy, referenced to 0K
        """
        super().__init__(m=0.0, U=U, V=0.0)
    def __repr__(self) -> str:
        return f"{type(self).__name__}(U={self.U:.3e} J)"
    
class Mass(MaterialExchange):
    """
    Material with only mass (no internal energy or volume).
    """
    def __init__(self, m: float, **_) -> None:
        """
        Initialize mass exchange material.
        Args:
            m:        [kg]  Mass
        """
        super().__init__(m=m, U=0.0, V=0.0)
    def __repr__(self) -> str:
        return f"{type(self).__name__}(m={self.m:.3e} kg)"
    
class Volume(MaterialExchange):
    """
    Material with only volume (no internal energy or mass).
    """
    def __init__(self, V: float, **_) -> None:
        """
        Initialize volume exchange material.
        Args:
            V:        [m³]  Volume
        """
        super().__init__(m=0.0, U=0.0, V=V)
    def __repr__(self) -> str:
        return f"{type(self).__name__}(V={self.V:.3e} m³)"


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyMaterial(Material):
        HEAT_CAPACITY = 1000.0
    # Instantiate
    mata = DummyMaterial(m=10.0, U=1e6, V=0.01)
    matb = DummyMaterial(m=10.0, U=2e6, V=0.02)
    exch = MaterialExchange(m=5.0, U=5e5, V=0.005)
    energy = Energy(U=1e5)
    mass = Mass(m=2.0)
    volume = Volume(V=0.002)
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
    # Test exchange addition
    matg = mata + exch
    assert matg.m == 15.0
    assert matg.U == 1.5e6
    # Test exchange subtraction
    math = mata - exch
    assert math.m == 5.0
    assert math.U == 5e5
    # Test right-side addition
    mati = exch + mata
    assert mati.m == 15.0
    assert mati.U == 1.5e6
    # Test right-side subtraction
    matj = exch - mata
    assert matj.m == -5.0
    assert matj.U == -5e5
    # Test material exchange addition
    matk = mass + energy + volume
    assert isinstance(matk, MaterialExchange)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

