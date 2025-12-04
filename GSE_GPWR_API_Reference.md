# GSE GPWR Simulator - Complete API Reference

**Version**: GPWR 6.2, JADE 5.1.1, SimExec 5.0.0
**VM**: gpwr (10.1.0.123)
**Location**: `D:\GPWR\`

---

## Table of Contents

### Quick Start
- [Getting Started](#getting-started)
- [Quick Reference](#quick-reference)
- [Connection Examples](#connection-examples)

### API Overview
- [Architecture](#architecture)
- [Available Interfaces](#available-interfaces)
- [Data Types](#data-types)

### GDA Server API (Primary Interface)
- [GDA Overview](#gda-server-primary-interface)
- [Connection](#gda-connection)
- [Variable Access](#variable-access)
- [Instructor Actions](#instructor-actions)
- [Initial Conditions](#initial-conditions)
- [Data Collection](#data-collection)
- [Backtrack & Replay](#backtrack--replay)

### RPC Protocol
- [RPC Client API](#rpc-client-api)
- [XDR Serialization](#xdr-serialization)

### ISD Interface (Interactive)
- [ISD Overview](#isd-interface)
- [Screen Management](#screen-management)
- [Data Point Access](#data-point-access)

### Database API
- [MDD Database](#database-api)
- [Point Lookup](#point-lookup)
- [Global Tables](#global-tables)

### Data Structures
- [Core Structures](#data-structures-reference)
- [Malfunction Types](#malfunction-structures)
- [Override Types](#override-structures)

### Examples
- [Python Integration](#python-integration-examples)
- [C/C++ Examples](#cc-examples)

---

## Getting Started

### Prerequisites
```bash
# Connection requirements
Host: 10.1.0.123
Port: 9800 (GDA Server)
Protocol: ONC RPC over TCP
```

### Quick Start Steps

1. **Start the Simulator**
```cmd
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd
```

2. **Connect to GDA Server**
```python
import socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("10.1.0.123", 9800))
```

3. **Read Variables** (see [Variable Access](#variable-access))
4. **Write Controls** (see [Instructor Actions](#instructor-actions))

---

## Quick Reference

### Most Common Operations

| Operation | RPC Call | Description |
|-----------|----------|-------------|
| Read Variable | `CALLget` (85) | Read simulation variable by name |
| Write Variable | `CALLpost` (86) | Write value to variable |
| Get Variable Info | `CALLgetGDES` (1) | Get variable metadata (GDES) |
| Set Malfunction | `CALLsetMF` (23) | Insert malfunction |
| Reset to IC | `CALLresetIC` (7) | Load initial condition |
| Get Backtrack | `CALLgetBT` (9) | Get backtrack summary |
| Set Override | `CALLsetOR` (11) | Override variable value |

### Variable Name Examples
```python
# Core Parameters
'RCS01POWER'    # Reactor power
'RCS01TAVE'     # Average temperature
'PRS01PRESS'    # Pressurizer pressure
'SGN01LEVEL'    # Steam generator 1 level
'TUR01SPEED'    # Turbine speed
```

---

## Architecture

### Component Diagram
```
┌─────────────────────────────────────────────┐
│  RL Agent (Python)                          │
│  ├─ Observation: Read variables             │
│  └─ Action: Write commands                  │
└─────────────┬───────────────────────────────┘
              │ TCP/RPC (Port 9800)
┌─────────────▼───────────────────────────────┐
│  GDA Server (gdaserver.exe)                 │
│  ├─ Variable read/write                     │
│  ├─ Malfunction insertion                   │
│  ├─ IC management                           │
│  └─ Data collection                         │
└─────────────┬───────────────────────────────┘
              │ Shared Memory
┌─────────────▼───────────────────────────────┐
│  SimExec (mst.exe)                          │
│  ├─ Plant Model (mstG.dll - 23 MB)         │
│  ├─ Real-time execution                     │
│  └─ Physics simulation                      │
└─────────────────────────────────────────────┘
```

### Process Architecture
- **MST** (Main Simulation Task) - Real-time plant model execution
- **GDA Server** - Generic Data Acquisition API server
- **DBA Server** - Database server for variable metadata
- **Dir Server** - Directory service for configuration
- **JADE** - Java-based control room HMI (optional for headless)

---

## Available Interfaces

### 1. GDA Server (Recommended ⭐)
**Port**: 9800
**Protocol**: ONC RPC
**Best For**: RL integration, real-time control, automated testing

**Capabilities**:
- ✅ Read any simulation variable by name
- ✅ Write values to controllable variables
- ✅ Batch read/write operations
- ✅ High-frequency sampling (10+ Hz)
- ✅ Malfunction insertion
- ✅ Initial condition management
- ✅ Override control

### 2. OPC DA Server
**Library**: `WTOPCsvr.dll`
**Protocol**: OPC DA 2.0/3.0
**Best For**: Integration with industrial SCADA systems

### 3. ISD (Interactive Shell)
**Interface**: Command-line terminal
**Best For**: Manual testing, debugging, exploration

### 4. Low-level RPC
**Libraries**: `oncrpc.dll`, `gdadll.dll`
**Best For**: Custom C/C++ integration

---

## GDA Server (Primary Interface)

### GDA Connection

#### Service Configuration
```c
#define GDAVERSION 1
#define GDADC_SERVICE 9800
```

#### RPC Program Numbers
All GDA services use **program number** defined in the system configuration.

#### Connection Timeout
```c
struct timeval timeout;
timeout.tv_sec = 10;   // 10 second timeout
timeout.tv_usec = 0;
```

---

### Variable Access

#### Read Variable - `CALLget` (85)

**Function**: Get variable value by name

**Request Format**:
```c
char *variable_name = "RCS01TAVE";
```

**Response Format**:
```c
char *result;  // String representation of value
```

**Example**:
```python
def read_variable(client, var_name):
    """Read variable value from GDA server"""
    # Construct RPC call for CALLget (85)
    # ... XDR encode variable name
    # ... Send RPC request
    # ... Receive and decode response
    return value
```

#### Write Variable - `CALLpost` (86)

**Function**: Set variable value by name

**Request Format**:
```c
char *command = "RCS01DEMAND=100.0";
```

**Response Format**:
```c
char *status;  // Status message
```

#### Get Variable Metadata - `CALLgetGDES` (1)

**Function**: Get detailed variable information

**Request Structure**:
```c
typedef struct {
    unsigned long flags;    // GDES fields requested
    char *user;            // Client username
    GDES *gdes;            // GDES list to populate
} DBAPREQ;
```

**Response Structure** (`GDES`):
```c
struct gDES {
    struct gDES *pnext;        // Next GDES or NULL
    char *name;                // Variable name
    u_short type;              // Data type (I1, I2, I4, R4, R8, etc.)
    u_short gid;               // Global ID
    u_short kind;              // Variable, constant, parameter
    u_short uflags;            // User flags
    u_long dims[3];            // Array dimensions [MAX 3]
    char *sdes;                // Short description
    char *unit;                // Engineering units
    char *ldes;                // Long description
    char *user;                // Owner username
    u_long base;               // Offset in global
    u_long offset;             // Element offset
    char *value;               // Current value (string)
    char *u;                   // Application-specific data
};
```

**GDES Flag Bits**:
```c
#define DBAPREQ_NAME    0x1       // Include name
#define DBAPREQ_TYPE    0x2       // Include type
#define DBAPREQ_GID     0x4       // Include global ID
#define DBAPREQ_DIMS    0x8       // Include dimensions
#define DBAPREQ_SDES    0x10      // Include short description
#define DBAPREQ_UNIT    0x20      // Include units
#define DBAPREQ_LDES    0x40      // Include long description
#define DBAPREQ_BASE    0x80      // Include base address
#define DBAPREQ_VALUE   0x100     // Include value
#define DBAPREQ_OFFSET  0x200     // Include offset

// Common combinations
#define DBAPREQ_ALL     (DBAPREQ_NAME | DBAPREQ_TYPE | DBAPREQ_GID | \
                         DBAPREQ_DIMS | DBAPREQ_SDES | DBAPREQ_UNIT | \
                         DBAPREQ_LDES | DBAPREQ_BASE | DBAPREQ_VALUE)

#define DBAPREQ_STD     (DBAPREQ_NAME | DBAPREQ_TYPE | DBAPREQ_GID | \
                         DBAPREQ_DIMS | DBAPREQ_SDES | DBAPREQ_UNIT | \
                         DBAPREQ_BASE | DBAPREQ_VALUE)
```

**Data Types**:
```c
#define I1  0    // Integer*1 (signed byte)
#define L1  1    // Logical*1 (boolean byte)
#define I2  2    // Integer*2 (short)
#define L2  3    // Logical*2
#define I4  4    // Integer*4 (int/long)
#define L4  5    // Logical*4
#define R4  6    // Real*4 (float)
#define R8  7    // Real*8 (double)
#define I8  8    // Integer*8 (long long)
#define C8  9    // Complex*8
#define C16 10   // Complex*16
#define H0  11   // Hollerith (string)
```

#### Get Variable List - `CALLgetGDL` (1)

**Function**: Get list of all available variables

**Response**: Linked list of GDES structures

---

### Instructor Actions

#### Malfunctions

##### Set Malfunction - `CALLsetMF` (23)

**Function**: Insert a malfunction into the simulation

**Structure**:
```c
struct gMALF {
    short avail;           // Availability flag
    short type;            // Malfunction type
    short scale;           // Scale factor
    short pending;         // Pending flag
    short event;           // Event trigger
    short index;           // Malfunction index
    short trgindex;        // Trigger index
    short gid;             // Global ID
    short trggid;          // Trigger global ID
    long delay;            // Delay time (seconds)
    long ldelete;          // Auto-delete time
    long ramp;             // Ramp rate
    long offset;           // Variable offset
    long trgoffset;        // Trigger offset
    long goffset;          // Global offset
    long gtrgoffset;       // Trigger global offset
    long time;             // Execution time
    float final;           // Final value
    float init;            // Initial value
    float delta;           // Change per step
    float low;             // Low limit
    float high;            // High limit
    double value;          // Current value
    char *vars;            // Variable name
    char *trgvars;         // Trigger variable
    char *desc;            // Description
    char *param;           // Parameters
    char *tam;             // TAM string
    short malftype;        // Type code
};
typedef struct gMALF MALFS;
```

**Example**:
```python
def insert_malfunction(client, var_name, final_value, ramp_time):
    """Insert a malfunction on a variable

    Args:
        var_name: Variable to malfunction (e.g., "RCS01PUMP1SPD")
        final_value: Target malfunction value
        ramp_time: Time to ramp to final value (seconds)
    """
    malf = MALFS()
    malf.vars = var_name
    malf.final = final_value
    malf.ramp = ramp_time
    malf.type = 1  # Ramp type
    # ... encode and send via RPC call 23
```

##### Get Malfunction - `CALLgetMALF` (4) / `CALLgetMF` (26)

**Function**: Query active malfunctions

**Parameters**:
```c
int *index;  // Malfunction index to query (or -1 for all)
```

**Response**: MALFS structure(s)

##### Delete Malfunction - `CALLdelMALF` (8) / `CALLdelMF` (obsolete)

**Function**: Remove active malfunction

**Parameters**:
```c
int *index;  // Malfunction index to delete
```

#### Overrides

##### Set Override - `CALLsetOR` (11) / `CALLsetOV` (25)

**Function**: Override a variable value (freeze at specific value)

**Structure**:
```c
struct gOVER {
    short avail;           // Availability
    short type;            // Override type
    short pending;         // Pending flag
    short event;           // Event trigger
    short sc;              // SC flag
    short wd;              // WD flag
    short bt;              // Backtrack flag
    short index;           // Override index
    short gid;             // Global ID
    short numdi;           // Number of discrete items
    short current;         // Current item
    long delay;            // Delay (seconds)
    long ldelete;          // Auto-delete time
    long ramp;             // Ramp rate
    long offset;           // Offset
    long goffset;          // Global offset
    long time;             // Time
    long varoffset[16];    // Variable offsets (MAX_POS=16)
    float final;           // Final value
    float init;            // Initial value
    float delta;           // Delta per step
    float low;             // Low limit
    float high;            // High limit
    double value;          // Current value
    char *vars;            // Variable name
    char *desc;            // Description
    char *param;           // Parameters
    char *tam;             // TAM string
};
typedef struct gOVER OVERS;
```

**Use Cases**:
- Freeze a variable at current value
- Force a variable to specific value
- Test control logic response

##### Get Override - `CALLgetOVER` (12) / `CALLgetOV` (28)

**Function**: Query active overrides

##### Delete Override - `CALLdelOVER` (13)

**Function**: Remove active override

#### Remote Functions

##### Set Remote - `CALLsetRM` (24)

**Function**: Activate a remote function (pre-programmed action)

**Structure**:
```c
struct gREM {
    short avail;
    short type;
    short scale;
    short pending;
    short event;
    short index;
    short trgindex;
    short gid;
    long delay;
    long ldelete;
    long ramp;
    long offset;
    long goffset;
    long trgoffset;
    long time;
    long pause;
    float final;
    float init;
    float delta;
    float low;
    float high;
    double value;
    char *vars;            // Variable name
    char *trgvars;         // Trigger variable
    char *desc;            // Description
    char *param;           // Parameters
    char *tam;
    short remtype;

    // Feedback variables
    char *feedback_var;
    short feedback_gid;
    long feedback_goffset;
    long feedback_offset;
    short feedback_vartype;
    double feedback_value;
};
typedef struct gREM REMS;
```

**Examples of Remote Functions**:
- Start pump
- Open valve
- Trip reactor
- Reset system

##### Get Remote - `CALLgetREM` (15) / `CALLgetRM` (27)

**Function**: Query remote function status

##### Delete Remote - `CALLdelREM` (16)

**Function**: Delete active remote function

#### Global Component Failures

##### Set GLCF - `CALLsetGLCF` (148)

**Function**: Simulate component failure

**Structure**:
```c
struct gGLCF {
    short avail;
    short type;
    short scale;
    short pending;
    short event;
    short index;
    short trgindex;
    long delay;
    long ldelete;
    long ramp;
    long time;
    float final;
    float init;
    float delta;
    float low;
    float high;

    short gid;             // Component global ID
    short trggid;
    short typegid;
    short fdbkgid;
    short fdbktypegid;

    long goffset;
    long gtrgoffset;
    long gtypeoffset;
    long gfdbkoffset;
    long gfdbktypeoffset;

    long offset;
    long trgoffset;
    long typeoffset;
    long fdbkoffset;
    long fdbktypeoffset;

    short trigger;
    double value;
    double fdbk;
    short fdbktype;
    short failtype;

    char *vars;
    char *trgvars;
    char *fdbkvars;
    char *fdbktypevars;
    char *failtypevars;
    char *desc;
    char *param;
    char *tam;
    short glcftype;
};
typedef struct gGLCF GLCF;
```

**Use Cases**:
- Pump failure
- Valve stuck
- Sensor failure
- Control system failure

##### Get GLCF - `CALLgetGLCF` (147)

##### Delete GLCF - `CALLdelGLCF` (149)

##### Check GLCF - `CALLcheckGLCF` (50)

#### Fixed Parameter Overrides

##### Set FPO - `CALLsetFPO` (52)

**Function**: Override fixed parameters (constants that don't normally change)

**Structure**:
```c
struct gFPO {
    short avail;
    short type;
    short scale;
    short pending;
    short event;
    short index;
    short fdbkindex;       // Feedback index
    short gid;
    short fdbkgid;
    long delay;
    long ldelete;
    long ramp;
    long offset;
    long fdbkoffset;
    long goffset;
    long gfdbkoffset;
    long time;
    float final;
    float init;
    float delta;
    float low;
    float high;
    double value;
    float defvalue;        // Default value
    char *vars;
    char *fdbkvars;
    char *desc;
    char *param;
    char *tam;
    short malftype;
};
typedef struct gFPO FPO;
```

##### Get FPO - `CALLgetFPO` (51)

##### Delete FPO - `CALLdelFPO` (53)

#### Annunciator Overrides

##### Set ANO - `CALLsetANO` (56)

**Function**: Override alarm annunciator state

**Structure**:
```c
struct gANO {
    short avail;
    short type;
    short pending;
    short event;
    short index;
    short gid;
    long delay;
    long ldelete;
    long offset;
    long goffset;
    long time;
    short value;           // Alarm state (0=off, 1=on)
    char *vars;
    char *desc;
    char *param;
    char *tam;
};
typedef struct gANO ANO;
```

##### Get ANO - `CALLgetANO` (55)

##### Delete ANO - `CALLdelANO` (57)

#### Get All Active - `CALLgetALLACTIVE` (84)

**Function**: Get all active instructor actions in one call

**Structure**:
```c
struct gALLACTIVE {
    int nummalf;
    MALFS *malf;
    int numremf;
    REMS *remf;
    int numglcf;
    GLCF *glcf;
    int numano;
    ANO *ano;
    int numfpo;
    FPO *fpo;
    int numovers;
    OVERS *overs;
};
typedef struct gALLACTIVE ALLACTIVE;
```

---

### Initial Conditions

#### Reset to IC - `CALLresetIC` (7)

**Function**: Load a saved initial condition (plant state snapshot)

**Parameters**:
```c
int ic_number;  // IC number to load (e.g., 100 for "100% power")
```

**Common IC Numbers**:
- `0` - Cold shutdown
- `50` - 50% power
- `100` - 100% power (full power operation)
- Custom ICs as configured

#### Snap IC - `CALLsetIC` (5)

**Function**: Save current plant state as an IC

**Parameters**:
```c
int ic_number;  // IC number to save to
char *ic_name;  // IC name/description
```

#### Get IC Info - `CALLinfoIC` (41)

**Function**: Get information about available ICs

---

### Data Collection

#### Get DC Points List - `CALLgetDCPointsList` (62)

**Function**: Get list of variables being collected

**Response**:
```c
typedef struct {
    u_long n;          // Number of points
    GDES *gdes;        // Point list
} GDESLIST;
```

#### Add DC Point - `CALLaddDCPoint` (65)

**Function**: Add variable to data collection

**Parameters**:
```c
char *variable_name;
```

#### Delete DC Point - `CALLdelDCPoint` (66)

**Function**: Remove variable from data collection

#### Get DC Values - `CALLgetDCValues` (63)

**Function**: Get collected data values

**Response**:
```c
typedef struct {
    double time;
    int ic;
    int n;             // Number of points
    int verify;
    float InstrAct;
    float OperAct;
    float InstrActCnt;
    float OperActCnt;
    float value[MAX_RECORD_ITEMS];
} DCVALUES;
```

#### Get DC History - `CALLgetDCHistory` (68)

**Function**: Get time-series data

**Response**:
```c
typedef struct {
    int n;             // Number of points
    int m;             // Number of time levels
    double time[MAX_SEND_ITEMS];
    float value[MAX_SEND_POINTS][MAX_SEND_ITEMS];
} DCHISTORY;
```

---

### Backtrack & Replay

#### Get Backtrack - `CALLgetBT` (9)

**Function**: Get backtrack (historical) data summary

**Response**:
```c
struct gBTRK {
    int time;          // Simulation time
    float var1;        // Tracked variable 1
    float var2;        // Tracked variable 2
    float var3;        // Tracked variable 3
    float var4;        // Tracked variable 4
    float var5;        // Tracked variable 5
};
typedef struct gBTRK BTRKS;
```

#### Reset Backtrack - `CALLresetBT` (10)

**Function**: Go back to a previous simulation state

**Parameters**:
```c
int time;  // Time (seconds) to reset back to
```

**Use Case**: Replay scenarios from recorded data

---

## RPC Client API

### Overview

All GDA communications use **ONC RPC** (Open Network Computing Remote Procedure Call) over TCP.

### Creating RPC Client

```c
#include <rpc/rpc.h>
#include <rpc/clnt.h>

CLIENT *client;
struct sockaddr_in server_addr;
int sock = RPC_ANYSOCK;
struct timeval timeout;

// Setup server address
server_addr.sin_family = AF_INET;
server_addr.sin_addr.s_addr = inet_addr("10.1.0.123");
server_addr.sin_port = 0;  // Let RPC handle port

timeout.tv_sec = 10;
timeout.tv_usec = 0;

// Create TCP client
client = clnttcp_create(&server_addr,
                        GDA_PROGRAM_NUMBER,  // From config
                        GDA_VERSION,         // Version 1
                        &sock,
                        0,                   // Default send size
                        0);                  // Default recv size

if (client == NULL) {
    clnt_pcreateerror("Failed to create client");
    exit(1);
}
```

### Making RPC Calls

```c
// Generic RPC call pattern
enum clnt_stat status;
char *request = "VARIABLE_NAME";
char *response;

status = clnt_call(client,
                   CALLget,              // Procedure number
                   (xdrproc_t)xdr_wrapstring,  // Encode function
                   (char *)&request,            // Request data
                   (xdrproc_t)xdr_wrapstring,  // Decode function
                   (char *)&response,           // Response buffer
                   timeout);

if (status != RPC_SUCCESS) {
    clnt_perror(client, "RPC call failed");
}
```

### RPC Error Handling

```c
enum clnt_stat {
    RPC_SUCCESS = 0,
    RPC_CANTENCODEARGS = 1,
    RPC_CANTDECODERES = 2,
    RPC_CANTSEND = 3,
    RPC_CANTRECV = 4,
    RPC_TIMEDOUT = 5,
    RPC_VERSMISMATCH = 6,
    RPC_AUTHERROR = 7,
    RPC_PROGUNAVAIL = 8,
    RPC_PROGVERSMISMATCH = 9,
    RPC_PROCUNAVAIL = 10,
    RPC_CANTDECODEARGS = 11,
    RPC_SYSTEMERROR = 12,
    RPC_UNKNOWNHOST = 13,
    RPC_PMAPFAILURE = 14,
    RPC_PROGNOTREGISTERED = 15,
    RPC_FAILED = 16,
    RPC_UNKNOWNPROTO = 17
};
```

### Cleanup

```c
clnt_destroy(client);
```

---

## XDR Serialization

### Overview

XDR (External Data Representation) is used to serialize data for RPC calls.

### XDR Operations

```c
enum xdr_op {
    XDR_ENCODE = 0,  // Serialize to network format
    XDR_DECODE = 1,  // Deserialize from network
    XDR_FREE = 2     // Free allocated memory
};
```

### XDR Handle

```c
typedef struct {
    enum xdr_op x_op;
    struct xdr_ops *x_ops;
    char *x_public;
    char *x_private;
    char *x_base;
    int x_handy;
} XDR;
```

### Common XDR Functions

```c
// Primitive types
bool_t xdr_int(XDR *xdrs, int *ip);
bool_t xdr_u_int(XDR *xdrs, u_int *up);
bool_t xdr_long(XDR *xdrs, long *lp);
bool_t xdr_u_long(XDR *xdrs, u_long *ulp);
bool_t xdr_short(XDR *xdrs, short *sp);
bool_t xdr_u_short(XDR *xdrs, u_short *usp);
bool_t xdr_float(XDR *xdrs, float *fp);
bool_t xdr_double(XDR *xdrs, double *dp);
bool_t xdr_bool(XDR *xdrs, bool_t *bp);

// String
bool_t xdr_string(XDR *xdrs, char **cpp, u_int maxsize);
bool_t xdr_wrapstring(XDR *xdrs, char **cpp);

// Arrays
bool_t xdr_array(XDR *xdrs, caddr_t *addrp, u_int *sizep,
                 u_int maxsize, u_int elsize, xdrproc_t elproc);

// Opaque data
bool_t xdr_bytes(XDR *xdrs, char **cpp, u_int *sizep, u_int maxsize);
bool_t xdr_opaque(XDR *xdrs, char *p, u_int cnt);
```

### Memory Buffers

```c
void xdrmem_create(XDR *xdrs, caddr_t addr, u_int size, enum xdr_op op);
```

### Cleanup

```c
xdr_destroy(&xdrs);
```

---

## ISD Interface

### Overview

ISD (Interactive Shell for Data) provides a terminal-based interface for exploring and manipulating simulation variables.

### Data Point Structure

```c
typedef struct ISDDATA {
    char *sName;                   // Point name
    char *alias;                   // Alias name
    char global[S5NAMELEN + 8];   // Global ID
    LLType offset;                 // Address offset
    LLType ptr;                    // Logical address pointer
    LLType gptr;                   // Global pointer
    GVALUE val;                    // Current value
    GVALUE min;                    // Minimum value
    GVALUE max;                    // Maximum value
    int index;                     // Array index
    int ndim;                      // Number of dimensions
    int dimen[MAX_DIM];           // Dimension sizes
    int size;                      // Total size
    char unit[UNITLEN50];         // Engineering units
    char form[21];                // Display format
    char desc[33];                // Short description
    char dtype;                    // Data type
    int prec;                      // Precision
    unsigned char eprec;          // Extended precision
    char tm;                       // Type modifier
    char scanflag;                // Min/max initialized
    char par[S5NAMELEN0];         // Index parameter
    char vcopt;                    // Variable/constant/parameter
    char level;                    // Access level (U/O)
    char alteration;              // Alteration flag
    char found;
    char strtype[S5NAMELEN0];
    int isddflags;
    TIME_i dtime;
    char *longdesc;
    char *uds;
    char *newexp;
    struct ISDDATA *next;
} ISDDATA;
```

### Key Functions

```c
// Get variable value
int get_value(ISDDATA *item);

// Set variable value
int set_value(ISDDATA *item, RANGE_SET *nst, YYSTYPE *value, char *src);

// Display variable info
void isd_point(ISDDATA *item, char *name, int flags);

// Search for variables
void isd_search(char *pattern, int flags, int scope);

// Show module information
void isd_show_mod(char *module, LLType entry, int check);

// Show global table
void isd_show_glo(char *globalname);
```

---

## Database API

### MDD Point Structure

```c
typedef struct MDDPOINT {
    char name[S5NAMELEN0];
    char predecessor[S5NAMELEN0];
    char global[S5NAMELEN0];
    char system[SYSLEN50];
    char units[UNITLEN50];
    char format[9];
    char shortdes[73];
    char longdesc[5][73];
    char vcopt;                // Variable/constant/parameter/macro
    char type1;                // Data type I/R/L
    unsigned char bindto;      // Byte size (1,2,4,8)
    char bound;                // Bound indication
    char root;                 // Root indication
    char glob_type;            // Global type
    char rootflag;
    int globid;
    int prec;                  // Precision
    int dim[MAX_DIM];          // Array dimensions
    int child;                 // Successor index
    int up_sibling;            // Previous sibling
    int next_sibling;          // Next sibling
    int parent;                // Parent index
    int offset;                // Predecessor offset
    int glob_offset;           // Global offset
    int dflags;                // Bit flags
    LLType date;               // Creation date
    union {
        int l;
        double f;
        LLType i8;
        double c[2];
    } value;                   // Default value
    int lsa;
    double fvalue;
    double ivalue;
    int extdesc;
    char *extdescS;           // Extended description
    int noxref;               // Number of cross-references
    char *x_refs;             // Cross-reference data
    char stype[S5NAMELEN0];
    char inc;
    int nextblock;
    char equation[17];
    double lowlimit;
    double hilimit;
} MDDPOINT;
```

### Key Functions

```c
// Get point by name
MDDPOINT *get_mdd_c_name(FHS s, char *name, int lreq);

// Get point by index
MDDPOINT *get_mdd_c_x(FHS s, int x, int lreq);

// Get point metadata
intok GetMDDPT(char *name, int lreq, int flags, MDDPT *pt,
               void *(*alloc)(size_t));
```

### Global Table

```c
// Get global table
GLTABLEC *getMDDGLTABLE(int level, void *(*alloc)(size_t));
```

---

## Data Structures Reference

### Common Types

```c
// Large integer type (cross-platform)
typedef long long LLType;

// Boolean
typedef int bool_t;
#define TRUE  1
#define FALSE 0

// Generic value union
typedef union {
    int i;
    long l;
    float f;
    double d;
    LLType ll;
    char *s;
} GVALUE;

// Time
typedef long TIME_i;

// String lengths
#define S5NAMELEN    32
#define S5NAMELEN0   (S5NAMELEN + 1)
#define UNITLEN50    16
#define SYSLEN50     8
#define USERLEN50    16
```

### Point Types

```c
#define PARAMETER  1
#define VARIABLE   2
#define CONSTANT   3
#define TEMPORARY  4
#define UNDEFINED  5
#define DUMMYARG   6
#define LOCALVAR   7
#define LOOPINDEX  8
#define SUBRNAME   9
#define EXTNAME    10
#define CONTMOD    11
#define SEGNAME    12
#define COMPNAME   13
#define FUNCNAME   14
#define DBERROR    15
```

### Simulation Control

```c
// Simulation rate
#define RTS_FREEZE      'f'
#define RTS_RUN         'm'
#define RTS_SLOW_RATE   'y'
#define RTS_NORMAL_RATE 'o'
#define RTS_FAST_RATE   'g'
#define RTS_STEP        'w'
```

---

## Python Integration Examples

### Complete RL Environment

```python
import socket
import struct
import numpy as np
from typing import Dict, Any, Tuple

class GPWREnvironment:
    """Complete RL environment for GSE GPWR simulator"""

    def __init__(self, host='10.1.0.123', port=9800):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False

        # Define observation space variables
        self.obs_vars = {
            'reactor_power': 'RCS01POWER',
            'avg_temp': 'RCS01TAVE',
            'hot_leg_temp': 'RCS01THOT',
            'cold_leg_temp': 'RCS01TCOLD',
            'przr_pressure': 'PRS01PRESS',
            'przr_level': 'PRS01LEVEL',
            'sg1_level': 'SGN01LEVEL',
            'sg1_pressure': 'SGN01PRESS',
            'sg2_level': 'SGN02LEVEL',
            'sg2_pressure': 'SGN02PRESS',
            'turbine_speed': 'TUR01SPEED',
            'gen_power': 'GEN01POWER',
        }

        # Define action space variables
        self.action_vars = {
            'rod_demand': 'RTC01DEMAND',
            'przr_spray': 'PRS01SPRAY',
            'przr_heaters': 'PRS01HEATERS',
            'fw_flow_demand': 'CFW01DEMAND',
            'turbine_governor': 'TUR01GOVERNOR',
        }

    def connect(self):
        """Connect to GDA server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(10.0)
        self.connected = True
        print(f"Connected to GDA server at {self.host}:{self.port}")

    def disconnect(self):
        """Disconnect from GDA server"""
        if self.sock:
            self.sock.close()
        self.connected = False

    def read_variable(self, var_name: str) -> float:
        """Read a single variable value

        Args:
            var_name: Variable name (e.g., 'RCS01POWER')

        Returns:
            Variable value as float
        """
        # TODO: Implement RPC CALLget (85)
        # 1. Construct RPC message header
        # 2. XDR encode variable name
        # 3. Send request
        # 4. Receive response
        # 5. XDR decode value
        # 6. Parse and return
        pass

    def write_variable(self, var_name: str, value: float):
        """Write a single variable value

        Args:
            var_name: Variable name
            value: Value to write
        """
        # TODO: Implement RPC CALLpost (86)
        # Construct command string: "VAR_NAME=value"
        command = f"{var_name}={value}"
        pass

    def read_observations(self) -> Dict[str, float]:
        """Read all observation space variables

        Returns:
            Dictionary of observation values
        """
        obs = {}
        for key, var_name in self.obs_vars.items():
            obs[key] = self.read_variable(var_name)
        return obs

    def write_actions(self, actions: Dict[str, float]):
        """Write all action space variables

        Args:
            actions: Dictionary of action values
        """
        for key, value in actions.items():
            if key in self.action_vars:
                var_name = self.action_vars[key]
                self.write_variable(var_name, value)

    def reset(self, ic_number: int = 100) -> Dict[str, float]:
        """Reset environment to initial condition

        Args:
            ic_number: Initial condition number (default: 100 = 100% power)

        Returns:
            Initial observations
        """
        # TODO: Implement RPC CALLresetIC (7)
        # Reset to specified IC

        # Wait for simulator to stabilize
        import time
        time.sleep(2.0)

        # Return initial observations
        return self.read_observations()

    def step(self, actions: Dict[str, float]) -> Tuple[Dict, float, bool, Dict]:
        """Take environment step

        Args:
            actions: Dictionary of actions to take

        Returns:
            Tuple of (observations, reward, done, info)
        """
        # Write actions
        self.write_actions(actions)

        # Wait for simulator to update (adjust based on sim rate)
        import time
        time.sleep(0.1)

        # Read new observations
        obs = self.read_observations()

        # Calculate reward
        reward = self._calculate_reward(obs)

        # Check if episode is done
        done = self._check_done(obs)

        # Additional info
        info = {}

        return obs, reward, done, info

    def _calculate_reward(self, obs: Dict[str, float]) -> float:
        """Calculate reward based on observations

        Reward function should be customized for your specific task.
        Example: maintaining power at setpoint
        """
        target_power = 100.0  # MW
        power_error = abs(obs['reactor_power'] - target_power)

        # Penalize deviation from target
        reward = -power_error

        # Bonus for staying within safe limits
        if (obs['przr_pressure'] > 2000 and obs['przr_pressure'] < 2300 and
            obs['przr_level'] > 20 and obs['przr_level'] < 80):
            reward += 10.0

        return reward

    def _check_done(self, obs: Dict[str, float]) -> bool:
        """Check if episode should terminate

        Returns True if safety limits exceeded or goal achieved
        """
        # Trip conditions
        if obs['przr_pressure'] < 1800 or obs['przr_pressure'] > 2500:
            return True
        if obs['reactor_power'] < 0 or obs['reactor_power'] > 110:
            return True

        return False

# Usage example
if __name__ == '__main__':
    env = GPWREnvironment()
    env.connect()

    # Reset to 100% power IC
    obs = env.reset(ic_number=100)
    print(f"Initial observations: {obs}")

    # Take a step
    actions = {
        'rod_demand': 0.0,  # No rod motion
        'przr_spray': 0.0,
        'przr_heaters': 50.0,
        'fw_flow_demand': 100.0,
        'turbine_governor': 100.0,
    }

    obs, reward, done, info = env.step(actions)
    print(f"New observations: {obs}")
    print(f"Reward: {reward}")
    print(f"Done: {done}")

    env.disconnect()
```

### RPC Implementation Helper

```python
class RPCClient:
    """Helper for ONC RPC protocol"""

    RPC_CALL = 0
    RPC_REPLY = 1

    MSG_ACCEPTED = 0
    MSG_DENIED = 1

    SUCCESS = 0

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.xid = 0

    def call(self, prog: int, vers: int, proc: int,
             args: bytes) -> bytes:
        """Make RPC call

        Args:
            prog: Program number
            vers: Version number
            proc: Procedure number
            args: XDR-encoded arguments

        Returns:
            XDR-encoded response
        """
        self.xid += 1

        # Build RPC call message
        # [xid][call=0][rpcvers=2][prog][vers][proc][auth][args]
        msg = bytearray()

        # XID
        msg.extend(struct.pack('>I', self.xid))

        # Message type (CALL)
        msg.extend(struct.pack('>I', self.RPC_CALL))

        # RPC version (2)
        msg.extend(struct.pack('>I', 2))

        # Program, version, procedure
        msg.extend(struct.pack('>I', prog))
        msg.extend(struct.pack('>I', vers))
        msg.extend(struct.pack('>I', proc))

        # NULL auth (for now)
        msg.extend(struct.pack('>I', 0))  # AUTH_NULL
        msg.extend(struct.pack('>I', 0))  # Length 0
        msg.extend(struct.pack('>I', 0))  # AUTH_NULL
        msg.extend(struct.pack('>I', 0))  # Length 0

        # Arguments
        msg.extend(args)

        # Send with length prefix (record marking)
        length = len(msg) | 0x80000000  # Set high bit = last fragment
        self.sock.sendall(struct.pack('>I', length))
        self.sock.sendall(msg)

        # Receive response
        response = self._receive_fragment()

        return self._parse_reply(response)

    def _receive_fragment(self) -> bytes:
        """Receive RPC fragment with record marking"""
        # Read length
        length_bytes = self.sock.recv(4)
        length = struct.unpack('>I', length_bytes)[0]

        last_fragment = (length & 0x80000000) != 0
        length = length & 0x7FFFFFFF

        # Read data
        data = bytearray()
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data.extend(chunk)

        return bytes(data)

    def _parse_reply(self, data: bytes) -> bytes:
        """Parse RPC reply message"""
        offset = 0

        # XID
        xid = struct.unpack_from('>I', data, offset)[0]
        offset += 4

        # Message type (should be REPLY=1)
        msg_type = struct.unpack_from('>I', data, offset)[0]
        offset += 4

        if msg_type != self.RPC_REPLY:
            raise ValueError(f"Expected REPLY, got {msg_type}")

        # Reply status
        reply_stat = struct.unpack_from('>I', data, offset)[0]
        offset += 4

        if reply_stat != self.MSG_ACCEPTED:
            raise ValueError(f"RPC call rejected")

        # Verifier (skip)
        auth_flavor = struct.unpack_from('>I', data, offset)[0]
        offset += 4
        auth_len = struct.unpack_from('>I', data, offset)[0]
        offset += 4 + auth_len

        # Accept status
        accept_stat = struct.unpack_from('>I', data, offset)[0]
        offset += 4

        if accept_stat != self.SUCCESS:
            raise ValueError(f"RPC call failed: {accept_stat}")

        # Return payload (rest of data)
        return data[offset:]

# XDR encoding helpers
class XDR:
    """XDR encoding/decoding utilities"""

    @staticmethod
    def encode_string(s: str) -> bytes:
        """Encode string to XDR format"""
        b = s.encode('utf-8')
        length = len(b)
        padding = (4 - (length % 4)) % 4
        return struct.pack('>I', length) + b + (b'\x00' * padding)

    @staticmethod
    def decode_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
        """Decode XDR string

        Returns:
            Tuple of (string, new_offset)
        """
        length = struct.unpack_from('>I', data, offset)[0]
        offset += 4
        s = data[offset:offset+length].decode('utf-8')
        offset += length
        padding = (4 - (length % 4)) % 4
        offset += padding
        return s, offset

    @staticmethod
    def encode_int(i: int) -> bytes:
        """Encode integer to XDR"""
        return struct.pack('>i', i)

    @staticmethod
    def decode_int(data: bytes, offset: int = 0) -> Tuple[int, int]:
        """Decode XDR integer"""
        value = struct.unpack_from('>i', data, offset)[0]
        return value, offset + 4

    @staticmethod
    def encode_float(f: float) -> bytes:
        """Encode float to XDR"""
        return struct.pack('>f', f)

    @staticmethod
    def decode_float(data: bytes, offset: int = 0) -> Tuple[float, int]:
        """Decode XDR float"""
        value = struct.unpack_from('>f', data, offset)[0]
        return value, offset + 4

    @staticmethod
    def encode_double(d: float) -> bytes:
        """Encode double to XDR"""
        return struct.pack('>d', d)

    @staticmethod
    def decode_double(data: bytes, offset: int = 0) -> Tuple[float, int]:
        """Decode XDR double"""
        value = struct.unpack_from('>d', data, offset)[0]
        return value, offset + 8
```

---

## C/C++ Examples

### Basic Connection

```c
#include <rpc/rpc.h>
#include <ops.h>

int main() {
    CLIENT *client;
    struct sockaddr_in server;
    int sock = RPC_ANYSOCK;
    struct timeval timeout;

    // Setup
    server.sin_family = AF_INET;
    server.sin_addr.s_addr = inet_addr("10.1.0.123");
    server.sin_port = 0;

    timeout.tv_sec = 10;
    timeout.tv_usec = 0;

    // Create client
    client = clnttcp_create(&server, GDASERVICES, GDAVERSION,
                           &sock, 0, 0);

    if (client == NULL) {
        clnt_pcreateerror("clnttcp_create failed");
        return 1;
    }

    printf("Connected to GDA server\n");

    // Use client for RPC calls...

    clnt_destroy(client);
    return 0;
}
```

### Read Variable

```c
char *read_variable(CLIENT *client, const char *var_name) {
    char *request = strdup(var_name);
    char *response = NULL;
    enum clnt_stat status;
    struct timeval timeout = {10, 0};

    status = clnt_call(client, CALLget,
                       (xdrproc_t)xdr_wrapstring, (char *)&request,
                       (xdrproc_t)xdr_wrapstring, (char *)&response,
                       timeout);

    free(request);

    if (status != RPC_SUCCESS) {
        clnt_perror(client, "read_variable failed");
        return NULL;
    }

    return response;  // Caller must free
}

// Usage
char *value = read_variable(client, "RCS01POWER");
printf("RCS01POWER = %s\n", value);
free(value);
```

### Write Variable

```c
int write_variable(CLIENT *client, const char *var_name, double value) {
    char command[256];
    char *request;
    char *response = NULL;
    enum clnt_stat status;
    struct timeval timeout = {10, 0};

    // Format command
    snprintf(command, sizeof(command), "%s=%.6f", var_name, value);
    request = command;

    status = clnt_call(client, CALLpost,
                       (xdrproc_t)xdr_wrapstring, (char *)&request,
                       (xdrproc_t)xdr_wrapstring, (char *)&response,
                       timeout);

    if (status != RPC_SUCCESS) {
        clnt_perror(client, "write_variable failed");
        return -1;
    }

    if (response) {
        printf("Response: %s\n", response);
        xdr_free((xdrproc_t)xdr_wrapstring, (char *)&response);
    }

    return 0;
}

// Usage
write_variable(client, "RTC01DEMAND", 50.0);
```

### Insert Malfunction

```c
int insert_malfunction(CLIENT *client, const char *var_name,
                      float final_value, int ramp_time) {
    MALFS malf;
    int result;
    enum clnt_stat status;
    struct timeval timeout = {10, 0};

    // Initialize malfunction structure
    memset(&malf, 0, sizeof(MALFS));
    malf.vars = strdup(var_name);
    malf.final = final_value;
    malf.ramp = ramp_time;
    malf.type = 1;  // Ramp type
    malf.avail = 1;

    status = clnt_call(client, CALLsetMF,
                       (xdrproc_t)xdr_MALFS, (char *)&malf,
                       (xdrproc_t)xdr_int, (char *)&result,
                       timeout);

    free(malf.vars);

    if (status != RPC_SUCCESS) {
        clnt_perror(client, "insert_malfunction failed");
        return -1;
    }

    printf("Malfunction inserted: index=%d\n", result);
    return result;
}
```

---

## Troubleshooting

### Common Issues

#### Connection Refused
**Symptom**: Cannot connect to port 9800
**Solution**: Ensure GDA server is running
```cmd
cd D:\GPWR\Plant
call UploadGPWR_EnglishUnit_ALL.cmd
```

#### RPC Timeout
**Symptom**: RPC calls timeout
**Solutions**:
- Increase timeout value
- Check network connectivity
- Verify simulator is running (not frozen)

#### Variable Not Found
**Symptom**: Variable read returns error
**Solutions**:
- Check variable name spelling
- Use ISD to explore available variables
- Query database with `CALLgetGDES`

#### Invalid Value
**Symptom**: Write operation rejected
**Solutions**:
- Check value is within valid range
- Verify variable is writable (not constant)
- Check data type matches

---

## Additional Resources

### Documentation Files (on VM)
```
D:\GPWR\Documentation\Software Manuals\SimExec_User_Guide.pdf
D:\GPWR\Documentation\Software Manuals\jstation.pdf
D:\GPWR\GSES\SimExec\bin\JDBUserGuide\
```

### Header Files
```
D:\GPWR\GSES\SimExec\include\gda.h       - GDA Server API
D:\GPWR\GSES\SimExec\include\ops.h       - Common definitions
D:\GPWR\GSES\SimExec\include\isd.h       - ISD interface
D:\GPWR\GSES\SimExec\include\dbm.h       - Database API
D:\GPWR\GSES\SimExec\include\RPC\*.h     - RPC headers
```

### Configuration Files
```
D:\GPWR\Plant\setenv.cmd                 - Environment setup
D:\GPWR\Plant\UploadGPWR_EnglishUnit_ALL.cmd - Startup script
```

---

## Appendix: Complete RPC Call Reference

| Call # | Name | Description |
|--------|------|-------------|
| 1 | CALLgetGDL | Get variable list |
| 2 | CALLsetGDP | Set variable value |
| 3 | CALLsetIS | Set instructor station |
| 4 | CALLgetMALF | Get malfunction (old) |
| 5 | CALLsetIC | Snap IC |
| 6 | CALLgetIC | Get IC info |
| 7 | CALLresetIC | Reset to IC |
| 8 | CALLdelMALF | Delete malfunction (old) |
| 9 | CALLgetBT | Get backtrack |
| 10 | CALLresetBT | Reset backtrack |
| 11 | CALLsetOR | Set override |
| 12 | CALLgetOVER | Get override |
| 13 | CALLdelOVER | Delete override |
| 14 | CALLgetSWCK | Get switch check |
| 15 | CALLgetREM | Get remote |
| 16 | CALLdelREM | Delete remote |
| 17 | CALLgetET | Get event trigger |
| 18 | CALLsetET | Set event trigger |
| 19 | CALLsetEV | Set event |
| 20 | CALLcmdET | Command event trigger |
| 21 | CALLgetCMD | Get command |
| 22 | CALLgetIS | Get instructor station |
| 23 | CALLsetMF | Set malfunction |
| 24 | CALLsetRM | Set remote |
| 25 | CALLsetOV | Set override |
| 26 | CALLgetMF | Get malfunction |
| 27 | CALLgetRM | Get remote |
| 28 | CALLgetOV | Get override |
| 34 | CALLsetRET | Set remote event trigger |
| 40 | CALLcleanBT | Clean backtrack |
| 41 | CALLinfoIC | Get IC info |
| 42 | CALLgetGDP | Get variable value |
| 43 | CALLgetDR | Get DR |
| 44 | CALLsetDR | Set DR |
| 45 | CALLresetDR | Reset DR |
| 47 | CALLsetPAUSE | Set pause |
| 48 | CALLsetEXAM | Set exam mode |
| 49 | CALLgetSCInfo | Get SC info |
| 50 | CALLcheckGLCF | Check GLCF |
| 51 | CALLgetFPO | Get fixed parameter override |
| 52 | CALLsetFPO | Set fixed parameter override |
| 53 | CALLdelFPO | Delete fixed parameter override |
| 54 | CALLcheckFPO | Check FPO |
| 55 | CALLgetANO | Get annunciator override |
| 56 | CALLsetANO | Set annunciator override |
| 57 | CALLdelANO | Delete annunciator override |
| 58 | CALLcheckANO | Check ANO |
| 59 | CALLgetWildGDES | Get wild GDES |
| 60 | CALLcheckMF | Check malfunction |
| 61 | CALLgetGDESex | Get GDES extended |
| 62 | CALLgetDCPointsList | Get data collection points list |
| 63 | CALLgetDCValues | Get data collection values |
| 65 | CALLaddDCPoint | Add data collection point |
| 66 | CALLdelDCPoint | Delete data collection point |
| 67 | CALLgetDCQueryID | Get data collection query ID |
| 68 | CALLgetDCHistory | Get data collection history |
| 69 | CALLsaveDCFile | Save data collection file |
| 70 | CALLexportDCFile | Export data collection file |
| 71 | CALLgetDCHistoryID | Get data collection history ID |
| 84 | CALLgetALLACTIVE | Get all active instructor actions |
| 85 | CALLget | Get variable (primary) ⭐ |
| 86 | CALLpost | Post variable (primary) ⭐ |
| 147 | CALLgetGLCF | Get global component failure |
| 148 | CALLsetGLCF | Set global component failure |
| 149 | CALLdelGLCF | Delete global component failure |

---

**End of API Reference**

For support or questions, consult the SimExec User Guide or contact GSE Systems support.
