"""
Remote Simulator Management for GSE GPWR

Provides remote control of GSE GPWR simulator on Windows VM via SSH.
Designed for scaling to hundreds of VMs for parallel RL training.
"""

import subprocess
import time
import socket
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SimulatorManager:
    """
    Remote management of GSE GPWR simulator on Windows VM

    Features:
    - Start/stop simulator remotely via SSH
    - Check simulator status
    - Auto-restart on failure
    - Health monitoring
    """

    def __init__(self,
                 host: str = '10.1.0.123',
                 ssh_user: str = 'brad',
                 gda_port: int = 9800,
                 gpwr_path: str = r'D:\GPWR\Plant',
                 startup_script: str = 'UploadGPWR_EnglishUnit_ALL.cmd'):
        """
        Initialize simulator manager

        Args:
            host: Windows VM hostname/IP
            ssh_user: SSH username
            gda_port: GDA Server port (default 9800)
            gpwr_path: Path to GPWR installation on Windows
            startup_script: Simulator startup script name
        """
        self.host = host
        self.ssh_user = ssh_user
        self.gda_port = gda_port
        self.gpwr_path = gpwr_path
        self.startup_script = startup_script

    def _ssh_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Execute command on Windows VM via SSH

        Args:
            command: Windows command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        ssh_cmd = [
            'ssh',
            f'{self.ssh_user}@{self.host}',
            command
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"SSH command timed out after {timeout}s")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"SSH command failed: {e}")
            return -1, "", str(e)

    def is_port_open(self, timeout: float = 2.0) -> bool:
        """
        Check if GDA server port is open

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if port is open, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.gda_port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Port check failed: {e}")
            return False

    def is_running(self) -> bool:
        """
        Check if simulator is running

        Returns:
            True if simulator processes are running
        """
        # Check for mst.exe process
        code, stdout, stderr = self._ssh_command(
            'tasklist | findstr /i "mst.exe"'
        )

        has_mst = code == 0 and 'mst.exe' in stdout

        # Check for gdaserver.exe process
        code, stdout, stderr = self._ssh_command(
            'tasklist | findstr /i "gdaserver.exe"'
        )

        has_gda = code == 0 and 'gdaserver.exe' in stdout

        # Check if port is listening
        port_open = self.is_port_open()

        logger.info(f"Simulator status: mst={has_mst}, gda={has_gda}, port={port_open}")

        return has_mst and has_gda and port_open

    def start(self, wait: bool = True, timeout: int = 60) -> bool:
        """
        Start the simulator

        Args:
            wait: Wait for simulator to be ready
            timeout: Maximum wait time in seconds

        Returns:
            True if started successfully
        """
        logger.info(f"Starting simulator on {self.host}")

        # Check if already running
        if self.is_running():
            logger.info("Simulator already running")
            return True

        # Build startup command
        # Use PowerShell to start in background
        startup_cmd = (
            f'powershell -Command '
            f'"cd {self.gpwr_path}; '
            f"Start-Process cmd.exe -ArgumentList '/c {self.startup_script}' "
            f'-WindowStyle Hidden"'
        )

        # Execute startup
        code, stdout, stderr = self._ssh_command(startup_cmd, timeout=10)

        if code != 0:
            logger.error(f"Failed to start simulator: {stderr}")
            return False

        if not wait:
            return True

        # Wait for simulator to start
        logger.info(f"Waiting for simulator to start (up to {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_running():
                elapsed = time.time() - start_time
                logger.info(f"Simulator started successfully in {elapsed:.1f}s")
                return True
            time.sleep(2)

        logger.error(f"Simulator failed to start within {timeout}s")
        return False

    def stop(self, force: bool = False) -> bool:
        """
        Stop the simulator

        Args:
            force: Force kill processes if graceful stop fails

        Returns:
            True if stopped successfully
        """
        logger.info(f"Stopping simulator on {self.host}")

        if not self.is_running():
            logger.info("Simulator not running")
            return True

        # Try graceful stop first
        # Kill mst.exe
        code, stdout, stderr = self._ssh_command(
            'taskkill /IM mst.exe'
        )

        # Kill gdaserver.exe
        code, stdout, stderr = self._ssh_command(
            'taskkill /IM gdaserver.exe'
        )

        # Wait a bit
        time.sleep(3)

        # Check if stopped
        if not self.is_running():
            logger.info("Simulator stopped successfully")
            return True

        if force:
            logger.warning("Forcing simulator stop")
            self._ssh_command('taskkill /F /IM mst.exe')
            self._ssh_command('taskkill /F /IM gdaserver.exe')
            time.sleep(2)

            if not self.is_running():
                logger.info("Simulator force-stopped")
                return True

        logger.error("Failed to stop simulator")
        return False

    def restart(self, timeout: int = 60) -> bool:
        """
        Restart the simulator

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            True if restarted successfully
        """
        logger.info("Restarting simulator")

        if not self.stop(force=True):
            logger.error("Failed to stop simulator for restart")
            return False

        time.sleep(5)  # Give Windows time to clean up

        return self.start(wait=True, timeout=timeout)

    def get_status(self) -> dict:
        """
        Get detailed simulator status

        Returns:
            Dictionary with status information
        """
        status = {
            'running': self.is_running(),
            'port_open': self.is_port_open(),
            'processes': {}
        }

        # Check mst.exe
        code, stdout, _ = self._ssh_command('tasklist | findstr /i "mst.exe"')
        status['processes']['mst'] = code == 0 and 'mst.exe' in stdout

        # Check gdaserver.exe
        code, stdout, _ = self._ssh_command('tasklist | findstr /i "gdaserver.exe"')
        status['processes']['gdaserver'] = code == 0 and 'gdaserver.exe' in stdout

        # Check dbaserver.exe
        code, stdout, _ = self._ssh_command('tasklist | findstr /i "dbaserver.exe"')
        status['processes']['dbaserver'] = code == 0 and 'dbaserver.exe' in stdout

        return status

    def health_check(self) -> bool:
        """
        Perform health check on simulator

        Returns:
            True if simulator is healthy
        """
        try:
            from .gda_client import GDAClient

            # Try to connect and read a variable
            client = GDAClient(host=self.host, port=self.gda_port, timeout=5.0)
            client.connect()

            # Try to read a variable
            power = client.read_variable('RCS01POWER')

            client.disconnect()

            # If we got here, simulator is responding
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def ensure_running(self, auto_restart: bool = True) -> bool:
        """
        Ensure simulator is running, restart if needed

        Args:
            auto_restart: Automatically restart if not running

        Returns:
            True if simulator is running (or was restarted successfully)
        """
        if self.is_running():
            # Do health check
            if self.health_check():
                return True
            else:
                logger.warning("Simulator running but failing health check")
                if auto_restart:
                    return self.restart()
                return False
        else:
            logger.warning("Simulator not running")
            if auto_restart:
                return self.start()
            return False


def main():
    """CLI interface for simulator management"""
    import argparse

    parser = argparse.ArgumentParser(description='GSE GPWR Simulator Manager')
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'health'],
                       help='Command to execute')
    parser.add_argument('--host', default='10.1.0.123',
                       help='Windows VM hostname (default: 10.1.0.123)')
    parser.add_argument('--user', default='brad',
                       help='SSH username (default: brad)')
    parser.add_argument('--port', type=int, default=9800,
                       help='GDA server port (default: 9800)')
    parser.add_argument('--force', action='store_true',
                       help='Force stop (kill processes)')
    parser.add_argument('--timeout', type=int, default=60,
                       help='Timeout in seconds (default: 60)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create manager
    manager = SimulatorManager(
        host=args.host,
        ssh_user=args.user,
        gda_port=args.port
    )

    # Execute command
    if args.command == 'start':
        success = manager.start(timeout=args.timeout)
        print(f"✓ Simulator started" if success else "✗ Failed to start simulator")
        exit(0 if success else 1)

    elif args.command == 'stop':
        success = manager.stop(force=args.force)
        print(f"✓ Simulator stopped" if success else "✗ Failed to stop simulator")
        exit(0 if success else 1)

    elif args.command == 'restart':
        success = manager.restart(timeout=args.timeout)
        print(f"✓ Simulator restarted" if success else "✗ Failed to restart simulator")
        exit(0 if success else 1)

    elif args.command == 'status':
        status = manager.get_status()
        print("\nSimulator Status:")
        print(f"  Running: {status['running']}")
        print(f"  Port {args.port}: {'Open' if status['port_open'] else 'Closed'}")
        print("\nProcesses:")
        for proc, running in status['processes'].items():
            print(f"  {proc}: {'✓' if running else '✗'}")
        exit(0 if status['running'] else 1)

    elif args.command == 'health':
        healthy = manager.health_check()
        print(f"✓ Simulator is healthy" if healthy else "✗ Simulator is unhealthy")
        exit(0 if healthy else 1)


if __name__ == '__main__':
    main()
