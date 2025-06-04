"""
Nuclear Plant Operator Game Engine

This module provides a game wrapper around the existing nuclear plant simulator,
adding perturbations, scoring, and game mechanics while preserving the RL engine.
"""

import random
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from simulator.core.sim import ControlAction, NuclearPlantSimulator, ReactorState


class GameDifficulty(Enum):
    """Game difficulty levels"""
    TRAINEE = "trainee"
    OPERATOR = "operator"  
    SENIOR_OPERATOR = "senior_operator"
    SHIFT_SUPERVISOR = "shift_supervisor"


class PerturbationType(Enum):
    """Types of perturbations that can occur"""
    EQUIPMENT_DEGRADATION = "equipment_degradation"
    LOAD_CHANGE = "load_change"
    SENSOR_DRIFT = "sensor_drift"
    FUEL_AGING = "fuel_aging"
    EXTERNAL_EVENT = "external_event"
    MAINTENANCE_REQUIRED = "maintenance_required"


@dataclass
class GamePerturbation:
    """Represents a game perturbation event"""
    perturbation_type: PerturbationType
    severity: float  # 0.1 to 2.0
    duration: float  # seconds
    description: str
    action_sequence: List[tuple]  # (ControlAction, magnitude, delay)


@dataclass
class GameState:
    """Current game state"""
    # Plant parameters (from simulator)
    power_level: float
    fuel_temperature: float
    coolant_temperature: float
    coolant_pressure: float
    coolant_flow_rate: float
    steam_temperature: float
    steam_pressure: float
    control_rod_position: float
    steam_valve_position: float
    scram_status: bool
    
    # Game-specific data
    score: int
    time_elapsed: float
    time_remaining: float
    current_perturbations: List[str]
    alarms: List[str]
    difficulty: GameDifficulty
    lives_remaining: int
    
    # Performance metrics
    safety_violations: int
    efficiency_score: float
    response_time_avg: float


class PerturbationManager:
    """Manages random perturbations and challenges"""
    
    def __init__(self, difficulty: GameDifficulty):
        self.difficulty = difficulty
        self.active_perturbations = []
        self.last_perturbation_time = 0.0
        self.perturbation_cooldown = self._get_cooldown_time()
    
    def _get_cooldown_time(self) -> float:
        """Get time between perturbations based on difficulty"""
        cooldowns = {
            GameDifficulty.TRAINEE: 180.0,      # 3 minutes
            GameDifficulty.OPERATOR: 120.0,     # 2 minutes  
            GameDifficulty.SENIOR_OPERATOR: 90.0,  # 1.5 minutes
            GameDifficulty.SHIFT_SUPERVISOR: 60.0   # 1 minute
        }
        return cooldowns[self.difficulty]
    
    def should_inject_perturbation(self, current_time: float) -> bool:
        """Check if it's time for a new perturbation"""
        time_since_last = current_time - self.last_perturbation_time
        
        # Base probability increases over time since last perturbation
        base_prob = min(0.1, time_since_last / self.perturbation_cooldown * 0.05)
        
        # Difficulty modifier
        difficulty_multiplier = {
            GameDifficulty.TRAINEE: 0.5,
            GameDifficulty.OPERATOR: 1.0,
            GameDifficulty.SENIOR_OPERATOR: 1.5,
            GameDifficulty.SHIFT_SUPERVISOR: 2.0
        }[self.difficulty]
        
        return random.random() < (base_prob * difficulty_multiplier)
    
    def generate_perturbation(self) -> GamePerturbation:
        """Generate a random perturbation based on difficulty"""
        perturbation_types = [
            PerturbationType.EQUIPMENT_DEGRADATION,
            PerturbationType.LOAD_CHANGE,
            PerturbationType.EXTERNAL_EVENT,
        ]
        
        # Add more complex perturbations for higher difficulties
        if self.difficulty in [GameDifficulty.SENIOR_OPERATOR, GameDifficulty.SHIFT_SUPERVISOR]:
            perturbation_types.extend([
                PerturbationType.SENSOR_DRIFT,
                PerturbationType.FUEL_AGING,
                PerturbationType.MAINTENANCE_REQUIRED
            ])
        
        perturbation_type = random.choice(perturbation_types)
        severity = random.uniform(0.3, 1.5)
        duration = random.uniform(30, 180)  # 30 seconds to 3 minutes
        
        return self._create_specific_perturbation(perturbation_type, severity, duration)
    
    def _create_specific_perturbation(self, ptype: PerturbationType, severity: float, duration: float) -> GamePerturbation:
        """Create specific perturbation based on type"""
        
        if ptype == PerturbationType.EQUIPMENT_DEGRADATION:
            # Simulate pump degradation by reducing coolant flow
            return GamePerturbation(
                perturbation_type=ptype,
                severity=severity,
                duration=duration,
                description=f"Primary coolant pump efficiency degraded by {severity*20:.0f}%",
                action_sequence=[(ControlAction.DECREASE_COOLANT_FLOW, severity, 0)]
            )
        
        elif ptype == PerturbationType.LOAD_CHANGE:
            # Simulate grid demand change
            if random.random() > 0.5:
                return GamePerturbation(
                    perturbation_type=ptype,
                    severity=severity,
                    duration=duration,
                    description=f"Grid demand increased - need {severity*10:.0f}% more power",
                    action_sequence=[(ControlAction.OPEN_STEAM_VALVE, severity, 0)]
                )
            else:
                return GamePerturbation(
                    perturbation_type=ptype,
                    severity=severity,
                    duration=duration,
                    description=f"Grid demand decreased - reduce power by {severity*10:.0f}%",
                    action_sequence=[(ControlAction.CLOSE_STEAM_VALVE, severity, 0)]
                )
        
        elif ptype == PerturbationType.EXTERNAL_EVENT:
            # Simulate external cooling water temperature change
            return GamePerturbation(
                perturbation_type=ptype,
                severity=severity,
                duration=duration,
                description="Cooling water temperature increased due to weather",
                action_sequence=[(ControlAction.INCREASE_COOLANT_FLOW, severity * 0.8, 0)]
            )
        
        else:
            # Default perturbation
            return GamePerturbation(
                perturbation_type=ptype,
                severity=severity,
                duration=duration,
                description="Minor system disturbance detected",
                action_sequence=[]
            )


class ScoreTracker:
    """Tracks player performance and calculates scores"""
    
    def __init__(self):
        self.total_score = 0
        self.safety_violations = 0
        self.efficiency_points = 0
        self.response_times = []
        self.last_alarm_time = None
        self.power_stability_history = []
    
    def update_score(self, reactor_state: ReactorState, time_elapsed: float) -> int:
        """Update score based on current plant state"""
        points_this_step = 0
        
        # Base points for keeping plant online
        if not reactor_state.scram_status:
            points_this_step += 1
        
        # Power stability bonus (target 100% power)
        power_deviation = abs(reactor_state.power_level - 100.0)
        if power_deviation < 2.0:  # Within 2%
            points_this_step += 5
        elif power_deviation < 5.0:  # Within 5%
            points_this_step += 2
        elif power_deviation > 20.0:  # More than 20% deviation
            points_this_step -= 3
        
        # Temperature management
        if reactor_state.fuel_temperature < 800:  # Safe temperature
            points_this_step += 1
        elif reactor_state.fuel_temperature > 1200:  # Approaching limits
            points_this_step -= 5
        
        # Pressure management
        if 14.0 < reactor_state.coolant_pressure < 16.0:  # Optimal range
            points_this_step += 1
        elif reactor_state.coolant_pressure > 16.5:  # High pressure
            points_this_step -= 3
        
        # Safety violations
        if reactor_state.scram_status:
            points_this_step -= 100
            self.safety_violations += 1
        
        # Efficiency bonus for optimal rod position
        if 80 < reactor_state.control_rod_position < 98:  # Good operating range
            points_this_step += 1
        
        self.total_score += points_this_step
        self.power_stability_history.append(reactor_state.power_level)
        
        # Keep only last 60 seconds of history
        if len(self.power_stability_history) > 60:
            self.power_stability_history.pop(0)
        
        return points_this_step
    
    def calculate_efficiency_score(self) -> float:
        """Calculate efficiency based on power stability"""
        if len(self.power_stability_history) < 10:
            return 0.0
        
        # Calculate standard deviation of power level
        power_std = np.std(self.power_stability_history)
        
        # Lower standard deviation = higher efficiency
        efficiency = max(0.0, 100.0 - float(power_std) * 10.0)
        return float(efficiency)
    
    def record_response_time(self, response_time: float):
        """Record operator response time to alarms"""
        self.response_times.append(response_time)
        # Keep only last 10 response times
        if len(self.response_times) > 10:
            self.response_times.pop(0)
    
    def get_average_response_time(self) -> float:
        """Get average response time"""
        return float(np.mean(self.response_times)) if self.response_times else 0.0


class NuclearOperatorGame:
    """Main game engine that wraps the nuclear plant simulator"""
    
    def __init__(self, difficulty: GameDifficulty = GameDifficulty.OPERATOR, game_duration: float = 1800):
        self.simulator = NuclearPlantSimulator(dt=1.0)
        self.perturbation_manager = PerturbationManager(difficulty)
        self.score_tracker = ScoreTracker()
        
        self.difficulty = difficulty
        self.game_duration = game_duration  # 30 minutes default
        self.start_time = time.time()
        self.game_time = 0.0
        self.is_running = True
        self.lives_remaining = 3  # Allow 3 SCRAM events before game over
        
        # Initialize simulator to steady state
        self.simulator.reset()
        
        # Game state tracking
        self.current_alarms = []
        self.active_perturbations = []
        self.last_alarm_time = None
    
    def step(self) -> GameState:
        """Execute one game step - advances time by 1 second"""
        if not self.is_running:
            return self.get_game_state()
        
        # Run simulation for 1 second (no player action)
        sim_result = self.simulator.step()
        self.game_time += self.simulator.dt
        
        # Check if game time is up
        if self.game_time >= self.game_duration:
            self.is_running = False
        
        # Check if we should inject a perturbation
        if self.perturbation_manager.should_inject_perturbation(self.game_time):
            perturbation = self.perturbation_manager.generate_perturbation()
            self._apply_perturbation(perturbation)
            self.perturbation_manager.last_perturbation_time = self.game_time
        
        # Update score
        points_earned = self.score_tracker.update_score(self.simulator.state, self.game_time)
        
        # Check for SCRAM
        if self.simulator.state.scram_status and self.lives_remaining > 0:
            self.lives_remaining -= 1
            if self.lives_remaining <= 0:
                self.is_running = False
            else:
                # Reset simulator after SCRAM but continue game
                self.simulator.reset()
        
        # Update alarms
        self._update_alarms()
        
        return self.get_game_state()
    
    def apply_action(self, player_action: ControlAction, action_magnitude: float = 1.0) -> GameState:
        """Apply a player action without advancing time"""
        if not self.is_running:
            return self.get_game_state()
        
        # Apply player action without stepping time
        self.simulator.apply_action(player_action, action_magnitude)
        
        # Update alarms (in case action caused immediate changes)
        self._update_alarms()
        
        return self.get_game_state()
    
    def _apply_perturbation(self, perturbation: GamePerturbation):
        """Apply a perturbation to the simulator"""
        self.active_perturbations.append(perturbation.description)
        
        # Execute the perturbation's action sequence
        for action, magnitude, delay in perturbation.action_sequence:
            # For now, apply immediately (could add delay logic later)
            self.simulator.step(action, magnitude)
        
        # Keep only last 5 perturbations for display
        if len(self.active_perturbations) > 5:
            self.active_perturbations.pop(0)
    
    def _update_alarms(self):
        """Update current alarm conditions"""
        alarms = []
        state = self.simulator.state
        
        # Temperature alarms
        if state.fuel_temperature > 1000:
            alarms.append("HIGH FUEL TEMPERATURE")
        if state.coolant_temperature > 320:
            alarms.append("HIGH COOLANT TEMPERATURE")
        
        # Pressure alarms
        if state.coolant_pressure > 16.5:
            alarms.append("HIGH COOLANT PRESSURE")
        elif state.coolant_pressure < 14.0:
            alarms.append("LOW COOLANT PRESSURE")
        
        # Power alarms
        if state.power_level > 110:
            alarms.append("HIGH POWER LEVEL")
        elif state.power_level < 80:
            alarms.append("LOW POWER LEVEL")
        
        # Flow alarms
        if state.coolant_flow_rate < 10000:
            alarms.append("LOW COOLANT FLOW")
        
        # SCRAM alarm
        if state.scram_status:
            alarms.append("REACTOR SCRAM ACTIVATED")
        
        # Track new alarms for response time
        new_alarms = set(alarms) - set(self.current_alarms)
        if new_alarms and not self.last_alarm_time:
            self.last_alarm_time = self.game_time
        
        self.current_alarms = alarms
    
    def get_game_state(self) -> GameState:
        """Get current game state for frontend"""
        state = self.simulator.state
        
        return GameState(
            # Plant parameters
            power_level=state.power_level,
            fuel_temperature=state.fuel_temperature,
            coolant_temperature=state.coolant_temperature,
            coolant_pressure=state.coolant_pressure,
            coolant_flow_rate=state.coolant_flow_rate,
            steam_temperature=state.steam_temperature,
            steam_pressure=state.steam_pressure,
            control_rod_position=state.control_rod_position,
            steam_valve_position=state.steam_valve_position,
            scram_status=state.scram_status,
            
            # Game data
            score=self.score_tracker.total_score,
            time_elapsed=self.game_time,
            time_remaining=max(0, self.game_duration - self.game_time),
            current_perturbations=self.active_perturbations.copy(),
            alarms=self.current_alarms.copy(),
            difficulty=self.difficulty,
            lives_remaining=self.lives_remaining,
            
            # Performance metrics
            safety_violations=self.score_tracker.safety_violations,
            efficiency_score=self.score_tracker.calculate_efficiency_score(),
            response_time_avg=self.score_tracker.get_average_response_time()
        )
    
    def reset_game(self, difficulty: Optional[GameDifficulty] = None):
        """Reset the game to initial state"""
        if difficulty:
            self.difficulty = difficulty
            self.perturbation_manager = PerturbationManager(difficulty)
        
        self.simulator.reset()
        self.score_tracker = ScoreTracker()
        self.game_time = 0.0
        self.is_running = True
        self.lives_remaining = 3
        self.current_alarms = []
        self.active_perturbations = []
        self.last_alarm_time = None
    
    def get_available_actions(self) -> List[ControlAction]:
        """Get list of available control actions"""
        return list(ControlAction)
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get final game summary"""
        return {
            'final_score': self.score_tracker.total_score,
            'safety_violations': self.score_tracker.safety_violations,
            'efficiency_score': self.score_tracker.calculate_efficiency_score(),
            'average_response_time': self.score_tracker.get_average_response_time(),
            'time_survived': self.game_time,
            'difficulty': self.difficulty.value,
            'game_completed': self.game_time >= self.game_duration and self.lives_remaining > 0
        }


# Example usage and testing
def demo_game():
    """Demonstrate the game engine"""
    print("Nuclear Plant Operator Game Demo")
    print("=" * 40)
    
    game = NuclearOperatorGame(difficulty=GameDifficulty.OPERATOR, game_duration=300)  # 5 minute demo
    
    print(f"Starting game - Difficulty: {game.difficulty.value}")
    print(f"Duration: {game.game_duration} seconds")
    print(f"Lives: {game.lives_remaining}")
    print()
    
    step_count = 0
    while game.is_running and step_count < 300:
        # Simulate some player actions
        if step_count == 30:
            action = ControlAction.CONTROL_ROD_WITHDRAW
            print("Player action: Withdrawing control rods")
        elif step_count == 60:
            action = ControlAction.INCREASE_COOLANT_FLOW
            print("Player action: Increasing coolant flow")
        elif step_count == 120:
            action = ControlAction.OPEN_STEAM_VALVE
            print("Player action: Opening steam valve")
        else:
            action = None
        
        # Step the game
        if action:
            game.apply_action(action)
        game_state = game.step()
        
        # Print status every 30 seconds
        if step_count % 30 == 0:
            print(f"\nTime: {game_state.time_elapsed:6.0f}s | Score: {game_state.score:5d} | "
                  f"Power: {game_state.power_level:6.1f}% | Lives: {game_state.lives_remaining}")
            
            if game_state.alarms:
                print(f"ALARMS: {', '.join(game_state.alarms)}")
            
            if game_state.current_perturbations:
                print(f"EVENTS: {game_state.current_perturbations[-1]}")
        
        step_count += 1
    
    # Game summary
    summary = game.get_game_summary()
    print(f"\n{'='*40}")
    print("GAME OVER")
    print(f"Final Score: {summary['final_score']}")
    print(f"Safety Violations: {summary['safety_violations']}")
    print(f"Efficiency Score: {summary['efficiency_score']:.1f}")
    print(f"Time Survived: {summary['time_survived']:.0f}s")
    print(f"Game Completed: {summary['game_completed']}")


if __name__ == "__main__":
    demo_game()
