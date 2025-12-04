#!/usr/bin/env python3
"""
Verification script for GSE GPWR library.

Tests that all components can be imported and basic operations work.
"""

print("=" * 70)
print("GSE GPWR Library Verification")
print("=" * 70)

# Test 1: Import main package
print("\n[1/8] Testing package import...")
try:
    import gse
    print(f"✓ Package imported successfully (version {gse.__version__})")
except Exception as e:
    print(f"✗ Failed to import package: {e}")
    exit(1)

# Test 2: Import core classes
print("\n[2/8] Testing core class imports...")
try:
    from gse import GDAClient, GPWREnvironment
    print("✓ GDAClient imported")
    print("✓ GPWREnvironment imported")
except Exception as e:
    print(f"✗ Failed to import core classes: {e}")
    exit(1)

# Test 3: Import data types
print("\n[3/8] Testing data type imports...")
try:
    from gse.types import GDES, MALFS, OVERS, DataType, PointType
    print("✓ GDES imported")
    print("✓ MALFS imported")
    print("✓ DataType enum imported")
except Exception as e:
    print(f"✗ Failed to import data types: {e}")
    exit(1)

# Test 4: Import exceptions
print("\n[4/8] Testing exception imports...")
try:
    from gse.exceptions import GSEError, RPCError, VariableNotFoundError
    print("✓ GSEError imported")
    print("✓ RPCError imported")
    print("✓ VariableNotFoundError imported")
except Exception as e:
    print(f"✗ Failed to import exceptions: {e}")
    exit(1)

# Test 5: XDR encoding/decoding
print("\n[5/8] Testing XDR functionality...")
try:
    from gse.xdr import XDREncoder, XDRDecoder
    
    # Test encoding
    encoder = XDREncoder()
    encoder.encode_int(42)
    encoder.encode_string("hello")
    encoder.encode_float(3.14)
    data = encoder.get_bytes()
    
    # Test decoding
    decoder = XDRDecoder(data)
    assert decoder.decode_int() == 42
    assert decoder.decode_string() == "hello"
    assert abs(decoder.decode_float() - 3.14) < 1e-5
    
    print("✓ XDR encoding/decoding works correctly")
except Exception as e:
    print(f"✗ XDR test failed: {e}")
    exit(1)

# Test 6: RPC client creation
print("\n[6/8] Testing RPC client creation...")
try:
    from gse.rpc_client import RPCClient
    client = RPCClient('10.1.0.123', 9800)
    assert client.host == '10.1.0.123'
    assert client.port == 9800
    assert not client.is_connected()
    print("✓ RPC client created successfully")
except Exception as e:
    print(f"✗ RPC client creation failed: {e}")
    exit(1)

# Test 7: GDA client creation
print("\n[7/8] Testing GDA client creation...")
try:
    client = GDAClient(host='10.1.0.123', port=9800)
    assert client.host == '10.1.0.123'
    assert client.port == 9800
    assert not client.is_connected()
    print("✓ GDA client created successfully")
except Exception as e:
    print(f"✗ GDA client creation failed: {e}")
    exit(1)

# Test 8: Environment creation
print("\n[8/8] Testing RL environment creation...")
try:
    env = GPWREnvironment(host='10.1.0.123', port=9800)
    obs_vars = env.get_observation_space_info()
    action_vars = env.get_action_space_info()
    
    assert len(obs_vars) > 0, "No observation variables defined"
    assert len(action_vars) > 0, "No action variables defined"
    
    print(f"✓ Environment created successfully")
    print(f"  - {len(obs_vars)} observation variables")
    print(f"  - {len(action_vars)} action variables")
except Exception as e:
    print(f"✗ Environment creation failed: {e}")
    exit(1)

# Summary
print("\n" + "=" * 70)
print("✓ All verification tests passed!")
print("=" * 70)
print("\nLibrary is ready to use. To connect to the simulator:")
print("  1. Ensure simulator is running at 10.1.0.123:9800")
print("  2. Use: with GDAClient(host='10.1.0.123') as client:")
print("  3. See examples in: gse/examples/basic_usage.py")
print("\nRun tests: python3 -m pytest gse/tests/ -v")
print("=" * 70)
