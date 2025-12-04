#!/usr/bin/env python3
"""
Simple test to verify GSE GPWR simulator connection from Linux
"""
import socket
import time
from gse import GDAClient

def test_connection():
    """Test basic connectivity to simulator"""
    print("=" * 60)
    print("GSE GPWR Simulator Connection Test")
    print("=" * 60)

    # Step 1: Test network connectivity
    print("\n[1/4] Testing network connectivity to 10.1.0.123:9800...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(('10.1.0.123', 9800))
        sock.close()
        print("✓ Network connection successful")
    except Exception as e:
        print(f"✗ Network connection failed: {e}")
        print("\nMake sure the simulator is running on Windows VM:")
        print("  ssh brad@10.1.0.123")
        print("  cd D:\\GPWR\\Plant")
        print("  call UploadGPWR_EnglishUnit_ALL.cmd")
        return False

    # Step 2: Connect to GDA server
    print("\n[2/4] Connecting to GDA server...")
    try:
        client = GDAClient(host='10.1.0.123', port=9800, timeout=10.0)
        client.connect()
        print("✓ GDA server connection successful")
    except Exception as e:
        print(f"✗ Failed to connect to GDA server: {e}")
        return False

    # Step 3: Read some variables
    print("\n[3/4] Reading simulation variables...")
    try:
        # Read reactor power
        power = client.read_variable('RCS01POWER')
        print(f"  Reactor Power:         {power}")

        # Read average temperature
        tavg = client.read_variable('RCS01TAVE')
        print(f"  Average Temperature:   {tavg}")

        # Read pressurizer pressure
        press = client.read_variable('PRS01PRESS')
        print(f"  Pressurizer Pressure:  {press}")

        print("✓ Variable reads successful")
    except Exception as e:
        print(f"✗ Failed to read variables: {e}")
        client.disconnect()
        return False

    # Step 4: Write a variable (safe test - just reading it back)
    print("\n[4/4] Testing variable write...")
    try:
        # Read current rod position
        current_rod = client.read_variable('RTC01DEMAND')
        print(f"  Current rod position: {current_rod}")

        # Write it back (no change, just testing write capability)
        client.write_variable('RTC01DEMAND', float(current_rod))
        print(f"  Wrote rod position: {current_rod}")

        # Read it again to verify
        new_rod = client.read_variable('RTC01DEMAND')
        print(f"  Verified rod position: {new_rod}")

        print("✓ Variable write successful")
    except Exception as e:
        print(f"✗ Failed to write variable: {e}")
        client.disconnect()
        return False

    # Disconnect
    client.disconnect()

    # Success!
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print("\nYour Linux machine can successfully communicate with")
    print("the GSE GPWR simulator running on the Windows VM!")
    print("\nYou are ready to start RL training.")
    return True

if __name__ == '__main__':
    try:
        success = test_connection()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
