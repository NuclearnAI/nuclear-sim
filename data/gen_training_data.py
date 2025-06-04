import json
import random
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

# Import the fixed PWR simulator and scenario generator
from simulator.core.sim import ControlAction, NuclearPlantSimulator


class ScenarioType(Enum):
    """Types of plant scenarios for training data"""

    NORMAL_OPERATION = "normal_operation"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    LOAD_FOLLOWING = "load_following"

    # Equipment failures
    CONTROL_ROD_MALFUNCTION = "control_rod_malfunction"
    RCS_PUMP_DEGRADATION = "rcs_pump_degradation"
    STEAM_GENERATOR_TUBE_LEAK = "sg_tube_leak"
    FEEDWATER_PUMP_FAILURE = "feedwater_pump_failure"
    TURBINE_VIBRATION = "turbine_vibration"
    CONDENSER_FOULING = "condenser_fouling"
    PRESSURIZER_HEATER_FAILURE = "pressurizer_heater_failure"
    INSTRUMENT_DRIFT = "instrument_drift"
    VALVE_STICKING = "valve_sticking"
    HEAT_EXCHANGER_FOULING = "heat_exchanger_fouling"

    # Transients
    REACTOR_TRIP = "reactor_trip"
    TURBINE_TRIP = "turbine_trip"
    LOSS_OF_FEEDWATER = "loss_of_feedwater"
    STEAM_LINE_BREAK = "steam_line_break"
    RCS_LEAK = "rcs_leak"


@dataclass
class TrainingExample:
    """Structure for training data"""

    scenario_type: str
    timeseries_data: List[List[float]]  # Time series of plant parameters
    timestamps: List[float]
    parameter_names: List[str]
    descriptions: List[str]  # Time-aligned descriptions
    summary: str
    equipment_status: Dict[str, str]
    severity: str  # "normal", "minor", "major", "severe"
    recommended_actions: List[str]


class EquipmentFailureSimulator:
    """Simulates various equipment failures and their signatures"""

    def __init__(self, base_simulator):
        self.sim = base_simulator

    def inject_control_rod_malfunction(self, start_time: int, severity: str = "minor"):
        """Simulate control rod sticking or drive mechanism issues"""
        if severity == "minor":
            # Rod moves slowly
            original_speed = self.sim.max_control_rod_speed
            self.sim.max_control_rod_speed *= 0.3

            return {
                "description": f"Control rod drive mechanism showing reduced response speed at T+{start_time}s. Rod movement rate decreased to 30% of normal.",
                "equipment": "Control Rod Drive Mechanism",
                "failure_mode": "Reduced Response Speed",
                "symptoms": [
                    "Slow power response to rod commands",
                    "Extended time to reach target rod position",
                ],
                "actions": [
                    "Monitor rod position indicators",
                    "Consider alternate rod groups",
                    "Plan maintenance window",
                ],
            }

        elif severity == "major":
            # Rod completely stuck
            stuck_position = self.sim.state.control_rod_position

            return {
                "description": f"Control rod #{random.randint(1, 53)} stuck at {stuck_position:.1f}% withdrawn position at T+{start_time}s. Drive mechanism non-responsive.",
                "equipment": "Control Rod Drive Mechanism",
                "failure_mode": "Mechanical Jam",
                "symptoms": [
                    "Rod position unchanged despite commands",
                    "Drive motor current anomaly",
                    "Loss of reactivity control margin",
                ],
                "actions": [
                    "Declare rod inoperable",
                    "Use alternate control rods",
                    "Adjust boron concentration",
                    "Plan emergency maintenance",
                ],
            }

    def inject_rcs_pump_degradation(self, start_time: int, severity: str = "minor"):
        """Simulate RCS pump bearing wear or impeller degradation"""
        degradation_rate = 0.95 if severity == "minor" else 0.85

        # Gradually reduce flow capacity
        self.sim.state.coolant_flow_rate *= degradation_rate

        # Add flow oscillations for bearing wear
        flow_noise = (
            np.random.normal(0, 50) if severity == "major" else np.random.normal(0, 20)
        )
        self.sim.state.coolant_flow_rate += flow_noise

        return {
            "description": f"RCS pump showing signs of degradation at T+{start_time}s. Flow rate decreased {(1 - degradation_rate) * 100:.0f}% with increased variability.",
            "equipment": "Reactor Coolant Pump",
            "failure_mode": "Mechanical Degradation"
            if severity == "minor"
            else "Bearing Failure",
            "symptoms": [
                "Reduced flow rate",
                "Flow oscillations",
                "Increased vibration",
                "Motor current variations",
            ],
            "actions": [
                "Monitor pump parameters closely",
                "Prepare backup pump",
                "Consider power reduction",
                "Schedule maintenance",
            ],
        }

    def inject_steam_generator_tube_leak(
        self, start_time: int, severity: str = "minor"
    ):
        """Simulate SG tube leak - primary to secondary"""
        leak_rate = 1.0 if severity == "minor" else 5.0  # kg/s

        # Decrease coolant flow due to leak
        self.sim.state.coolant_flow_rate -= leak_rate * 2  # Flow reduction due to leak

        # Slight pressure effect
        pressure_effect = 0.01 * leak_rate
        self.sim.state.steam_pressure += pressure_effect

        return {
            "description": f"Steam generator tube leak detected at T+{start_time}s. Primary-to-secondary leakage rate approximately {leak_rate:.1f} kg/s.",
            "equipment": "Steam Generator Tubes",
            "failure_mode": "Tube Leak",
            "symptoms": [
                "Rising secondary side radiation",
                "RCS makeup demand",
                "SG chemistry changes",
                "Slight SG pressure increase",
            ],
            "actions": [
                "Monitor radiation levels",
                "Increase RCS makeup",
                "Consider plant shutdown",
                "Isolate affected SG if severe",
            ],
        }

    def inject_feedwater_pump_failure(self, start_time: int):
        """Simulate feedwater pump trip or failure"""
        # Sudden loss of feedwater flow
        self.sim.state.feedwater_flow_rate *= 0.1  # 90% reduction

        return {
            "description": f"Feedwater pump trip at T+{start_time}s. Feedwater flow reduced to {self.sim.state.feedwater_flow_rate:.0f} kg/s.",
            "equipment": "Feedwater Pump",
            "failure_mode": "Pump Trip",
            "symptoms": [
                "Rapid feedwater flow reduction",
                "SG level dropping",
                "Low pump discharge pressure",
                "Pump motor trip alarm",
            ],
            "actions": [
                "Start backup feedwater pump",
                "Monitor SG levels closely",
                "Reduce reactor power",
                "Investigate pump trip cause",
            ],
        }

    def inject_condenser_fouling(self, start_time: int, severity: str = "minor"):
        """Simulate condenser tube fouling"""
        fouling_factor = 0.8 if severity == "minor" else 0.6

        # Reduce heat transfer effectiveness - affect steam temperature
        self.sim.state.steam_temperature += (1 - fouling_factor) * 10

        return {
            "description": f"Condenser performance degradation detected at T+{start_time}s. Heat transfer reduced by {(1 - fouling_factor) * 100:.0f}%.",
            "equipment": "Main Condenser",
            "failure_mode": "Tube Fouling",
            "symptoms": [
                "Rising condenser pressure",
                "Increasing condenser temperature",
                "Reduced vacuum",
                "Higher circulating water outlet temperature",
            ],
            "actions": [
                "Monitor condenser performance",
                "Consider backwash cycle",
                "Check CW system",
                "Plan condenser cleaning",
            ],
        }

    def inject_instrument_drift(self, start_time: int, parameter: str):
        """Simulate instrument calibration drift"""
        drift_amount = random.uniform(-2, 2)  # % drift

        return {
            "description": f"{parameter} indication showing drift of {drift_amount:+.1f}% at T+{start_time}s. Possible calibration issue.",
            "equipment": f"{parameter} Transmitter",
            "failure_mode": "Calibration Drift",
            "symptoms": [
                "Parameter reading inconsistent with plant conditions",
                "Trending away from expected values",
            ],
            "actions": [
                "Compare with redundant instruments",
                "Perform instrument calibration check",
                "Consider taking instrument out of service",
            ],
        }


class TrainingDataGenerator:
    """Generates comprehensive plant scenarios with descriptions"""

    def __init__(self):
        self.failure_sim = None

    def generate_scenario(
        self, scenario_type: ScenarioType, duration: int = 600
    ) -> TrainingExample:
        """Generate a complete scenario with time series and descriptions"""

        # Create fresh simulator for each scenario
        sim = NuclearPlantSimulator(dt=1.0)
        self.failure_sim = EquipmentFailureSimulator(sim)

        timeseries_data = []
        timestamps = []
        descriptions = []
        equipment_status = {"all_systems": "normal"}
        recommended_actions = []

        # Run scenario
        failure_injected = False
        failure_info = None

        for t in range(duration):
            # Inject equipment failure at random time (if applicable)
            if (
                not failure_injected
                and t > 120
                and self._should_inject_failure(scenario_type, t)
            ):
                failure_info = self._inject_failure(scenario_type, t)
                if failure_info:
                    equipment_status[failure_info["equipment"]] = failure_info[
                        "failure_mode"
                    ]
                    recommended_actions.extend(failure_info["actions"])
                    failure_injected = True

            # Apply control actions based on scenario
            action = self._get_scenario_action(scenario_type, t, failure_injected)
            result = sim.step(action)

            # Store data
            timeseries_data.append(result["observation"].tolist())
            timestamps.append(sim.time)

            # Generate time-aligned descriptions
            if t % 30 == 0 or (
                failure_injected and t % 10 == 0
            ):  # Every 30 seconds or every 10s after failure
                description = self._generate_time_description(
                    sim, t, failure_info, failure_injected
                )
                descriptions.append(description)

            # Break if simulation terminated
            if result["done"]:
                break

        # Generate overall summary
        summary = self._generate_scenario_summary(scenario_type, sim, failure_info)

        # Determine severity
        severity = self._assess_severity(scenario_type, sim)

        return TrainingExample(
            scenario_type=scenario_type.value,
            timeseries_data=timeseries_data,
            timestamps=timestamps,
            parameter_names=self._get_parameter_names(),
            descriptions=descriptions,
            summary=summary,
            equipment_status=equipment_status,
            severity=severity,
            recommended_actions=recommended_actions,
        )

    def _should_inject_failure(self, scenario_type: ScenarioType, t: int) -> bool:
        """Determine if failure should be injected at time t"""
        failure_scenarios = [
            ScenarioType.CONTROL_ROD_MALFUNCTION,
            ScenarioType.RCS_PUMP_DEGRADATION,
            ScenarioType.STEAM_GENERATOR_TUBE_LEAK,
            ScenarioType.FEEDWATER_PUMP_FAILURE,
            ScenarioType.CONDENSER_FOULING,
            ScenarioType.INSTRUMENT_DRIFT,
        ]

        if scenario_type in failure_scenarios:
            # Inject failure with some probability (earlier = higher chance)
            probability = 0.02 + 0.001 * (t - 120)  # Increasing probability over time
            return random.random() < probability

        return False

    def _inject_failure(self, scenario_type: ScenarioType, t: int) -> Optional[Dict]:
        """Inject appropriate failure based on scenario type"""
        if self.failure_sim is None:
            return None

        try:
            if scenario_type == ScenarioType.CONTROL_ROD_MALFUNCTION:
                return self.failure_sim.inject_control_rod_malfunction(
                    t, random.choice(["minor", "major"])
                )
            elif scenario_type == ScenarioType.RCS_PUMP_DEGRADATION:
                return self.failure_sim.inject_rcs_pump_degradation(
                    t, random.choice(["minor", "major"])
                )
            elif scenario_type == ScenarioType.STEAM_GENERATOR_TUBE_LEAK:
                return self.failure_sim.inject_steam_generator_tube_leak(
                    t, random.choice(["minor", "major"])
                )
            elif scenario_type == ScenarioType.FEEDWATER_PUMP_FAILURE:
                return self.failure_sim.inject_feedwater_pump_failure(t)
            elif scenario_type == ScenarioType.CONDENSER_FOULING:
                return self.failure_sim.inject_condenser_fouling(
                    t, random.choice(["minor", "major"])
                )
            elif scenario_type == ScenarioType.INSTRUMENT_DRIFT:
                parameter = random.choice(
                    [
                        "RCS Pressure",
                        "Steam Generator Level",
                        "Neutron Flux",
                        "RCS Temperature",
                    ]
                )
                return self.failure_sim.inject_instrument_drift(t, parameter)
        except Exception as e:
            print(f"Error injecting failure: {e}")
            return None

        return {
            "description": "Unknown failure",
            "equipment": "Unknown",
            "failure_mode": "Unknown",
            "actions": [],
        }

    def _get_scenario_action(
        self, scenario_type: ScenarioType, t: int, failure_occurred: bool
    ):
        """Get appropriate control action for scenario at time t"""

        if scenario_type == ScenarioType.NORMAL_OPERATION:
            # Occasional minor adjustments
            if t % 200 == 0:
                return random.choice(
                    [
                        ControlAction.NO_ACTION,
                        ControlAction.CONTROL_ROD_WITHDRAW,
                        ControlAction.CONTROL_ROD_INSERT,
                    ]
                )

        elif scenario_type == ScenarioType.STARTUP:
            if t < 300:
                return ControlAction.CONTROL_ROD_WITHDRAW
            else:
                return ControlAction.NO_ACTION

        elif scenario_type == ScenarioType.LOAD_FOLLOWING:
            # Sinusoidal power changes
            if np.sin(t / 100) > 0.5:
                return ControlAction.CONTROL_ROD_WITHDRAW
            elif np.sin(t / 100) < -0.5:
                return ControlAction.CONTROL_ROD_INSERT

        elif failure_occurred and scenario_type == ScenarioType.FEEDWATER_PUMP_FAILURE:
            # Operator response to feedwater pump failure
            if t % 60 == 0:  # Every minute, try to manage the situation
                return random.choice(
                    [ControlAction.INCREASE_FEEDWATER, ControlAction.CONTROL_ROD_INSERT]
                )

        return ControlAction.NO_ACTION

    def _generate_time_description(
        self, sim, t: int, failure_info: Optional[Dict], failure_occurred: bool
    ) -> str:
        """Generate natural language description of current plant state"""

        base_description = (
            f"T+{t}s: Reactor power at {sim.state.power_level:.1f}%, "
            f"Fuel temperature {sim.state.fuel_temperature:.0f}°C, "
            f"Coolant temperature {sim.state.coolant_temperature:.0f}°C"
        )

        if failure_occurred and failure_info:
            return f"{base_description}. {failure_info['description']}"

        # Add context based on trends
        if sim.state.power_level > 105:
            base_description += ". Power above normal operating range."
        elif sim.state.power_level < 95:
            base_description += ". Power below normal operating range."

        if sim.state.coolant_pressure > 16.0:
            base_description += " RCS pressure elevated."
        elif sim.state.coolant_pressure < 15.0:
            base_description += " RCS pressure below normal."

        return base_description

    def _generate_scenario_summary(
        self, scenario_type: ScenarioType, sim, failure_info: Optional[Dict]
    ) -> str:
        """Generate overall scenario summary"""

        if scenario_type == ScenarioType.NORMAL_OPERATION:
            return f"Normal plant operation scenario. Final power level {sim.state.power_level:.1f}%, all systems stable."

        elif failure_info:
            return (
                f"{scenario_type.value.replace('_', ' ').title()} scenario. "
                f"{failure_info['equipment']} experienced {failure_info['failure_mode'].lower()}. "
                f"Plant responded with operator actions to maintain safe operation."
            )

        else:
            return f"{scenario_type.value.replace('_', ' ').title()} scenario completed successfully."

    def _assess_severity(self, scenario_type: ScenarioType, sim) -> str:
        """Assess overall scenario severity"""

        if sim.state.scram_status:
            return "severe"
        elif sim.state.power_level > 110 or sim.state.power_level < 90:
            return "major"
        elif scenario_type in [
            ScenarioType.NORMAL_OPERATION,
            ScenarioType.LOAD_FOLLOWING,
        ]:
            return "normal"
        else:
            return "minor"

    def _get_parameter_names(self) -> List[str]:
        """Get list of parameter names corresponding to observation vector"""
        return [
            "neutron_flux_norm",
            "fuel_temp_norm",
            "coolant_temp_norm",
            "coolant_pressure_norm",
            "coolant_flow_norm",
            "steam_temp_norm",
            "steam_pressure_norm",
            "steam_flow_norm",
            "control_rod_position_norm",
            "steam_valve_position_norm",
            "power_level_norm",
            "scram_status",
        ]


def generate_training_dataset(num_scenarios: int = 100) -> List[TrainingExample]:
    """Generate comprehensive training dataset"""

    generator = TrainingDataGenerator()
    dataset = []

    scenario_weights = {
        ScenarioType.NORMAL_OPERATION: 0.3,
        ScenarioType.STARTUP: 0.1,
        ScenarioType.SHUTDOWN: 0.1,
        ScenarioType.LOAD_FOLLOWING: 0.15,
        ScenarioType.CONTROL_ROD_MALFUNCTION: 0.08,
        ScenarioType.RCS_PUMP_DEGRADATION: 0.08,
        ScenarioType.STEAM_GENERATOR_TUBE_LEAK: 0.06,
        ScenarioType.FEEDWATER_PUMP_FAILURE: 0.06,
        ScenarioType.CONDENSER_FOULING: 0.04,
        ScenarioType.INSTRUMENT_DRIFT: 0.02,
    }

    print(f"Generating {num_scenarios} training scenarios...")

    for i in range(num_scenarios):
        # Select scenario type based on weights
        scenario_types = list(scenario_weights.keys())
        weights = list(scenario_weights.values())
        scenario_type = random.choices(scenario_types, weights=weights, k=1)[0]

        print(f"Generating scenario {i + 1}/{num_scenarios}: {scenario_type.value}")

        try:
            example = generator.generate_scenario(scenario_type, duration=600)
            dataset.append(example)
        except Exception as e:
            print(f"Error generating scenario {i + 1}: {e}")
            continue

    print(f"Successfully generated {len(dataset)} training examples")
    return dataset


def save_training_data(
    dataset: List[TrainingExample], filename: str = "nuclear_plant_training_data.json"
):
    """Save training dataset to JSON file"""

    # Convert to serializable format
    serializable_data = []
    for example in dataset:
        serializable_data.append(asdict(example))

    with open(filename, "w") as f:
        json.dump(serializable_data, f, indent=2)

    print(f"Training data saved to {filename}")
    print(f"Dataset contains {len(dataset)} examples")

    # Print statistics
    scenario_counts = {}
    severity_counts = {}

    for example in dataset:
        scenario_counts[example.scenario_type] = (
            scenario_counts.get(example.scenario_type, 0) + 1
        )
        severity_counts[example.severity] = severity_counts.get(example.severity, 0) + 1

    print("\nScenario distribution:")
    for scenario, count in scenario_counts.items():
        print(f"  {scenario}: {count}")

    print("\nSeverity distribution:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count}")


def demonstrate_training_data_generation():
    """Demonstrate the training data generation process"""

    print("Nuclear Plant Training Data Generation Demo")
    print("=" * 50)

    # Generate small dataset for demo
    dataset = generate_training_dataset(num_scenarios=5)

    # Show example
    if dataset:
        example = dataset[0]
        print(f"\nExample Training Data:")
        print(f"Scenario: {example.scenario_type}")
        print(f"Severity: {example.severity}")
        print(f"Summary: {example.summary}")
        print(f"Equipment Status: {example.equipment_status}")
        print(
            f"Recommended Actions: {example.recommended_actions[:2] if example.recommended_actions else 'None'}..."
        )
        print(f"Time series length: {len(example.timeseries_data)} data points")
        print(f"Number of descriptions: {len(example.descriptions)}")

        if example.descriptions:
            print(f"Sample description: {example.descriptions[0]}")

    # Save dataset
    save_training_data(dataset, "demo_training_data.json")

    return dataset


if __name__ == "__main__":
    # Run demonstration
    demo_dataset = demonstrate_training_data_generation()
