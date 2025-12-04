"""
Gym-compatible RL environment for GSE GPWR simulator.

Provides a standard Gym interface for reinforcement learning with configurable
observation and action spaces, reward functions, and safety limits.
"""

import logging
import time
from typing import Dict, Any, Tuple, List, Optional, Callable
import numpy as np

from gse.gda_client import GDAClient
from gse.exceptions import GSEError

logger = logging.getLogger(__name__)


class GPWREnvironment:
    """Gym-compatible environment for GSE GPWR simulator.

    Provides a standard reinforcement learning interface with customizable
    observation/action spaces and reward functions.

    Example:
        >>> env = GPWREnvironment(host='10.1.0.123')
        >>> env.connect()
        >>> obs = env.reset(ic=100)  # Reset to 100% power
        >>> action = {'rod_demand': 0.0, 'fw_flow': 100.0}
        >>> obs, reward, done, info = env.step(action)
        >>> env.close()

    Attributes:
        observation_space: Dictionary defining observation variables
        action_space: Dictionary defining action variables
        reward_function: Custom reward function
    """

    def __init__(
        self,
        host: str = '10.1.0.123',
        port: int = 9800,
        timeout: float = 10.0,
        observation_vars: Optional[Dict[str, str]] = None,
        action_vars: Optional[Dict[str, str]] = None,
        reward_function: Optional[Callable] = None,
        step_delay: float = 0.1,
        max_episode_steps: int = 1000,
    ):
        """Initialize GPWR environment.

        Args:
            host: GDA server hostname or IP
            port: GDA server port
            timeout: Operation timeout
            observation_vars: Dictionary mapping observation keys to variable names
            action_vars: Dictionary mapping action keys to variable names
            reward_function: Custom reward function (obs, action, next_obs) -> float
            step_delay: Delay between actions in seconds (simulation update time)
            max_episode_steps: Maximum steps per episode
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.step_delay = step_delay
        self.max_episode_steps = max_episode_steps

        # Initialize GDA client
        self.client = GDAClient(host, port, timeout)

        # Set up observation space
        self.observation_vars = observation_vars or self._default_observation_vars()

        # Set up action space
        self.action_vars = action_vars or self._default_action_vars()

        # Set reward function
        self.reward_function = reward_function or self._default_reward_function

        # Episode tracking
        self.current_step = 0
        self.episode_count = 0
        self.last_obs: Optional[Dict[str, float]] = None

    def _default_observation_vars(self) -> Dict[str, str]:
        """Default observation space variables.

        Returns:
            Dictionary of observation variable mappings
        """
        return {
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

    def _default_action_vars(self) -> Dict[str, str]:
        """Default action space variables.

        Returns:
            Dictionary of action variable mappings
        """
        return {
            'rod_demand': 'RTC01DEMAND',
            'przr_spray': 'PRS01SPRAY',
            'przr_heaters': 'PRS01HEATERS',
            'fw_flow_demand': 'CFW01DEMAND',
            'turbine_governor': 'TUR01GOVERNOR',
        }

    def connect(self) -> None:
        """Connect to GDA server.

        Raises:
            ConnectionError: If connection fails
        """
        self.client.connect()
        logger.info(f"Environment connected to {self.host}:{self.port}")

    def disconnect(self) -> None:
        """Disconnect from GDA server."""
        self.client.disconnect()
        logger.info("Environment disconnected")

    def close(self) -> None:
        """Close environment (alias for disconnect)."""
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if connected to server.

        Returns:
            True if connected, False otherwise
        """
        return self.client.is_connected()

    def reset(self, ic: int = 100, seed: Optional[int] = None) -> Dict[str, float]:
        """Reset environment to initial condition.

        Args:
            ic: Initial condition number (default: 100 = full power)
            seed: Random seed (for reproducibility, currently unused)

        Returns:
            Initial observation dictionary

        Raises:
            GSEError: If reset fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        logger.info(f"Resetting environment to IC {ic}")

        # Reset to initial condition
        self.client.reset_to_ic(ic)

        # Wait for simulator to stabilize
        time.sleep(2.0)

        # Reset episode tracking
        self.current_step = 0
        self.episode_count += 1

        # Get initial observations
        obs = self._get_observations()
        self.last_obs = obs

        logger.info(f"Episode {self.episode_count} started")
        return obs

    def step(self, action: Dict[str, float]) -> Tuple[Dict[str, float], float, bool, Dict[str, Any]]:
        """Take an environment step.

        Args:
            action: Dictionary of actions to take

        Returns:
            Tuple of (observation, reward, done, info)
                - observation: Current state observations
                - reward: Reward for this step
                - done: Whether episode is finished
                - info: Additional information dictionary

        Raises:
            GSEError: If step fails
        """
        if not self.is_connected():
            raise GSEError("Not connected to GDA server")

        # Save previous observation for reward calculation
        prev_obs = self.last_obs

        # Apply actions
        self._apply_actions(action)

        # Wait for simulator to update
        time.sleep(self.step_delay)

        # Get new observations
        obs = self._get_observations()
        self.last_obs = obs

        # Calculate reward
        reward = self.reward_function(prev_obs, action, obs)

        # Check if episode is done
        done = self._check_done(obs)

        # Additional info
        info = {
            'step': self.current_step,
            'episode': self.episode_count,
        }

        self.current_step += 1

        # Check max steps
        if self.current_step >= self.max_episode_steps:
            done = True
            info['max_steps_reached'] = True

        return obs, reward, done, info

    def _get_observations(self) -> Dict[str, float]:
        """Read all observation variables.

        Returns:
            Dictionary of observation values

        Raises:
            GSEError: If reading fails
        """
        obs = {}

        # Read all observation variables
        for key, var_name in self.observation_vars.items():
            try:
                value_str = self.client.read_variable(var_name)
                # Convert to float
                obs[key] = float(value_str)
            except Exception as e:
                logger.error(f"Failed to read observation '{key}' ({var_name}): {e}")
                # Use NaN for failed reads
                obs[key] = np.nan

        return obs

    def _apply_actions(self, action: Dict[str, float]) -> None:
        """Write action variables.

        Args:
            action: Dictionary of action values

        Raises:
            GSEError: If writing fails
        """
        for key, value in action.items():
            if key not in self.action_vars:
                logger.warning(f"Unknown action key: {key}")
                continue

            var_name = self.action_vars[key]
            try:
                self.client.write_variable(var_name, value)
            except Exception as e:
                logger.error(f"Failed to write action '{key}' ({var_name}): {e}")
                # Continue with other actions

    def _default_reward_function(
        self,
        prev_obs: Optional[Dict[str, float]],
        action: Dict[str, float],
        obs: Dict[str, float]
    ) -> float:
        """Default reward function.

        Reward for maintaining stable operation near setpoint.

        Args:
            prev_obs: Previous observations (may be None on first step)
            action: Actions taken
            obs: Current observations

        Returns:
            Reward value
        """
        if prev_obs is None:
            return 0.0

        reward = 0.0

        # Target values for steady-state operation
        target_power = 100.0  # MW (or %)
        target_pressure = 2250.0  # psia
        target_level = 50.0  # %

        # Penalize deviation from targets
        power_error = abs(obs.get('reactor_power', target_power) - target_power)
        pressure_error = abs(obs.get('przr_pressure', target_pressure) - target_pressure)
        level_error = abs(obs.get('przr_level', target_level) - target_level)

        # Scaled penalties
        reward -= power_error * 0.1
        reward -= pressure_error * 0.01
        reward -= level_error * 0.1

        # Bonus for staying within safe operating range
        if (2000 < obs.get('przr_pressure', 0) < 2500 and
            20 < obs.get('przr_level', 0) < 80 and
            90 < obs.get('reactor_power', 0) < 110):
            reward += 10.0

        # Penalize large control actions (smoothness)
        if action:
            for value in action.values():
                if abs(value) > 100:
                    reward -= 1.0

        return reward

    def _check_done(self, obs: Dict[str, float]) -> bool:
        """Check if episode should terminate.

        Returns True if safety limits are exceeded or reactor trips.

        Args:
            obs: Current observations

        Returns:
            True if episode is done, False otherwise
        """
        # Check safety limits
        reactor_power = obs.get('reactor_power', 100.0)
        przr_pressure = obs.get('przr_pressure', 2250.0)
        przr_level = obs.get('przr_level', 50.0)

        # Trip conditions
        if przr_pressure < 1800 or przr_pressure > 2500:
            logger.info(f"Episode terminated: Pressurizer pressure out of range ({przr_pressure} psia)")
            return True

        if przr_level < 10 or przr_level > 90:
            logger.info(f"Episode terminated: Pressurizer level out of range ({przr_level}%)")
            return True

        if reactor_power < 0 or reactor_power > 120:
            logger.info(f"Episode terminated: Reactor power out of range ({reactor_power})")
            return True

        # Check for NaN values (sensor failure or communication error)
        if any(np.isnan(v) for v in obs.values()):
            logger.warning("Episode terminated: NaN values detected in observations")
            return True

        return False

    def get_observation_space_info(self) -> Dict[str, str]:
        """Get information about observation space.

        Returns:
            Dictionary mapping observation keys to variable names
        """
        return self.observation_vars.copy()

    def get_action_space_info(self) -> Dict[str, str]:
        """Get information about action space.

        Returns:
            Dictionary mapping action keys to variable names
        """
        return self.action_vars.copy()

    def render(self, mode: str = 'human') -> None:
        """Render environment (not implemented for simulator).

        Args:
            mode: Render mode (unused)
        """
        if self.last_obs:
            print(f"\n=== Step {self.current_step} ===")
            for key, value in self.last_obs.items():
                print(f"{key:20s}: {value:10.2f}")

    def seed(self, seed: Optional[int] = None) -> List[int]:
        """Set random seed (for compatibility, not used).

        Args:
            seed: Random seed

        Returns:
            List containing seed
        """
        return [seed] if seed is not None else []

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
