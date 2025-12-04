"""
Data structures for GSE GPWR simulator.

Defines all data types, enums, and structures used in GDA Server communication.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import IntEnum


class DataType(IntEnum):
    """Variable data types."""
    I1 = 0   # Integer*1 (signed byte)
    L1 = 1   # Logical*1 (boolean byte)
    I2 = 2   # Integer*2 (short)
    L2 = 3   # Logical*2
    I4 = 4   # Integer*4 (int/long)
    L4 = 5   # Logical*4
    R4 = 6   # Real*4 (float)
    R8 = 7   # Real*8 (double)
    I8 = 8   # Integer*8 (long long)
    C8 = 9   # Complex*8
    C16 = 10 # Complex*16
    H0 = 11  # Hollerith (string)


class PointType(IntEnum):
    """Point/variable classification types."""
    PARAMETER = 1
    VARIABLE = 2
    CONSTANT = 3
    TEMPORARY = 4
    UNDEFINED = 5
    DUMMYARG = 6
    LOCALVAR = 7
    LOOPINDEX = 8
    SUBRNAME = 9
    EXTNAME = 10
    CONTMOD = 11
    SEGNAME = 12
    COMPNAME = 13
    FUNCNAME = 14
    DBERROR = 15


# GDES (Generic Data Entry Structure) flags
GDES_NAME = 0x1
GDES_TYPE = 0x2
GDES_GID = 0x4
GDES_DIMS = 0x8
GDES_SDES = 0x10
GDES_UNIT = 0x20
GDES_LDES = 0x40
GDES_BASE = 0x80
GDES_VALUE = 0x100
GDES_OFFSET = 0x200

GDES_ALL = (GDES_NAME | GDES_TYPE | GDES_GID | GDES_DIMS |
            GDES_SDES | GDES_UNIT | GDES_LDES | GDES_BASE | GDES_VALUE)

GDES_STD = (GDES_NAME | GDES_TYPE | GDES_GID | GDES_DIMS |
            GDES_SDES | GDES_UNIT | GDES_BASE | GDES_VALUE)


@dataclass
class GDES:
    """Generic Data Entry Structure - Variable metadata.

    Contains detailed information about a simulation variable including
    its name, type, dimensions, description, units, and current value.
    """
    name: str = ""
    type: int = 0  # DataType
    gid: int = 0  # Global ID
    kind: int = 0  # PointType
    uflags: int = 0  # User flags
    dims: Tuple[int, int, int] = (0, 0, 0)  # Array dimensions
    sdes: str = ""  # Short description
    unit: str = ""  # Engineering units
    ldes: str = ""  # Long description
    user: str = ""  # Owner username
    base: int = 0  # Offset in global
    offset: int = 0  # Element offset
    value: str = ""  # Current value (string representation)
    u: str = ""  # Application-specific data
    pnext: Optional['GDES'] = None  # Next GDES in linked list


@dataclass
class MALFS:
    """Malfunction Structure.

    Defines a malfunction to be inserted into the simulation.
    Malfunctions can ramp variables to specific values over time.
    """
    avail: int = 1  # Availability flag
    type: int = 1  # Malfunction type (1=ramp)
    scale: int = 0  # Scale factor
    pending: int = 0  # Pending flag
    event: int = 0  # Event trigger
    index: int = 0  # Malfunction index
    trgindex: int = 0  # Trigger index
    gid: int = 0  # Global ID
    trggid: int = 0  # Trigger global ID
    delay: int = 0  # Delay time (seconds)
    ldelete: int = 0  # Auto-delete time
    ramp: int = 0  # Ramp rate (seconds)
    offset: int = 0  # Variable offset
    trgoffset: int = 0  # Trigger offset
    goffset: int = 0  # Global offset
    gtrgoffset: int = 0  # Trigger global offset
    time: int = 0  # Execution time
    final: float = 0.0  # Final value
    init: float = 0.0  # Initial value
    delta: float = 0.0  # Change per step
    low: float = 0.0  # Low limit
    high: float = 0.0  # High limit
    value: float = 0.0  # Current value
    vars: str = ""  # Variable name
    trgvars: str = ""  # Trigger variable
    desc: str = ""  # Description
    param: str = ""  # Parameters
    tam: str = ""  # TAM string
    malftype: int = 0  # Type code


@dataclass
class OVERS:
    """Override Structure.

    Defines an override to freeze or force a variable to a specific value.
    """
    avail: int = 1
    type: int = 0
    pending: int = 0
    event: int = 0
    sc: int = 0
    wd: int = 0
    bt: int = 0
    index: int = 0
    gid: int = 0
    numdi: int = 0  # Number of discrete items
    current: int = 0  # Current item
    delay: int = 0
    ldelete: int = 0
    ramp: int = 0
    offset: int = 0
    goffset: int = 0
    time: int = 0
    varoffset: List[int] = field(default_factory=lambda: [0] * 16)  # MAX_POS=16
    final: float = 0.0
    init: float = 0.0
    delta: float = 0.0
    low: float = 0.0
    high: float = 0.0
    value: float = 0.0
    vars: str = ""
    desc: str = ""
    param: str = ""
    tam: str = ""


@dataclass
class REMS:
    """Remote Function Structure.

    Defines a remote function (pre-programmed action) to be activated.
    """
    avail: int = 1
    type: int = 0
    scale: int = 0
    pending: int = 0
    event: int = 0
    index: int = 0
    trgindex: int = 0
    gid: int = 0
    delay: int = 0
    ldelete: int = 0
    ramp: int = 0
    offset: int = 0
    goffset: int = 0
    trgoffset: int = 0
    time: int = 0
    pause: int = 0
    final: float = 0.0
    init: float = 0.0
    delta: float = 0.0
    low: float = 0.0
    high: float = 0.0
    value: float = 0.0
    vars: str = ""
    trgvars: str = ""
    desc: str = ""
    param: str = ""
    tam: str = ""
    remtype: int = 0
    feedback_var: str = ""
    feedback_gid: int = 0
    feedback_goffset: int = 0
    feedback_offset: int = 0
    feedback_vartype: int = 0
    feedback_value: float = 0.0


@dataclass
class GLCF:
    """Global Component Failure Structure.

    Defines a component failure (e.g., pump failure, valve stuck).
    """
    avail: int = 1
    type: int = 0
    scale: int = 0
    pending: int = 0
    event: int = 0
    index: int = 0
    trgindex: int = 0
    delay: int = 0
    ldelete: int = 0
    ramp: int = 0
    time: int = 0
    final: float = 0.0
    init: float = 0.0
    delta: float = 0.0
    low: float = 0.0
    high: float = 0.0
    gid: int = 0
    trggid: int = 0
    typegid: int = 0
    fdbkgid: int = 0
    fdbktypegid: int = 0
    goffset: int = 0
    gtrgoffset: int = 0
    gtypeoffset: int = 0
    gfdbkoffset: int = 0
    gfdbktypeoffset: int = 0
    offset: int = 0
    trgoffset: int = 0
    typeoffset: int = 0
    fdbkoffset: int = 0
    fdbktypeoffset: int = 0
    trigger: int = 0
    value: float = 0.0
    fdbk: float = 0.0
    fdbktype: int = 0
    failtype: int = 0
    vars: str = ""
    trgvars: str = ""
    fdbkvars: str = ""
    fdbktypevars: str = ""
    failtypevars: str = ""
    desc: str = ""
    param: str = ""
    tam: str = ""
    glcftype: int = 0


@dataclass
class FPO:
    """Fixed Parameter Override Structure.

    Defines an override for fixed parameters (constants).
    """
    avail: int = 1
    type: int = 0
    scale: int = 0
    pending: int = 0
    event: int = 0
    index: int = 0
    fdbkindex: int = 0
    gid: int = 0
    fdbkgid: int = 0
    delay: int = 0
    ldelete: int = 0
    ramp: int = 0
    offset: int = 0
    fdbkoffset: int = 0
    goffset: int = 0
    gfdbkoffset: int = 0
    time: int = 0
    final: float = 0.0
    init: float = 0.0
    delta: float = 0.0
    low: float = 0.0
    high: float = 0.0
    value: float = 0.0
    defvalue: float = 0.0  # Default value
    vars: str = ""
    fdbkvars: str = ""
    desc: str = ""
    param: str = ""
    tam: str = ""
    malftype: int = 0


@dataclass
class ANO:
    """Annunciator Override Structure.

    Defines an override for alarm annunciator states.
    """
    avail: int = 1
    type: int = 0
    pending: int = 0
    event: int = 0
    index: int = 0
    gid: int = 0
    delay: int = 0
    ldelete: int = 0
    offset: int = 0
    goffset: int = 0
    time: int = 0
    value: int = 0  # Alarm state (0=off, 1=on)
    vars: str = ""
    desc: str = ""
    param: str = ""
    tam: str = ""


@dataclass
class ALLACTIVE:
    """All Active Instructor Actions Structure.

    Contains all currently active instructor actions in one structure.
    """
    nummalf: int = 0
    malf: List[MALFS] = field(default_factory=list)
    numremf: int = 0
    remf: List[REMS] = field(default_factory=list)
    numglcf: int = 0
    glcf: List[GLCF] = field(default_factory=list)
    numano: int = 0
    ano: List[ANO] = field(default_factory=list)
    numfpo: int = 0
    fpo: List[FPO] = field(default_factory=list)
    numovers: int = 0
    overs: List[OVERS] = field(default_factory=list)


@dataclass
class BTRKS:
    """Backtrack Structure.

    Contains historical simulation data.
    """
    time: int = 0
    var1: float = 0.0
    var2: float = 0.0
    var3: float = 0.0
    var4: float = 0.0
    var5: float = 0.0


@dataclass
class DCVALUES:
    """Data Collection Values Structure.

    Contains current data collection values.
    """
    time: float = 0.0
    ic: int = 0
    n: int = 0
    verify: int = 0
    InstrAct: float = 0.0
    OperAct: float = 0.0
    InstrActCnt: float = 0.0
    OperActCnt: float = 0.0
    values: List[float] = field(default_factory=list)


@dataclass
class DCHISTORY:
    """Data Collection History Structure.

    Contains time-series data collection.
    """
    n: int = 0  # Number of points
    m: int = 0  # Number of time levels
    time: List[float] = field(default_factory=list)
    values: List[List[float]] = field(default_factory=list)  # [points][time]
