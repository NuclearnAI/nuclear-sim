# Examples Module

This directory contains example scripts and a Jupyter notebook to demonstrate various capabilities of the Nuclear Plant Simulator. These examples show how to use the simulator's features, including different heat sources and interactive modes.

For overall project information, installation, and detailed CLI usage, please refer to the main `README.md` in the root directory.

## Contents
- **`interactive_constant_heat.py`**: An interactive demo using the constant heat source, ideal for understanding secondary systems without reactor physics complexity.
- **`interactive_*.sh` scripts**: Shell scripts that launch the main simulator CLI (`nuclear_sim.py`) with pre-configured arguments for various interactive scenarios (e.g., normal operation, power ramps, emergency events).
- **`nuclear_plant_constant_heat_simulation.ipynb`**: A Jupyter Notebook providing a comprehensive demonstration of the constant heat source and data analysis.

## Running Examples

### Interactive Python Demo
```bash
python examples/interactive_constant_heat.py
```
(Follow in-demo instructions)

### Shell Script Launchers
(Run from the project root directory)
```bash
bash examples/interactive_normal.sh
bash examples/interactive_power_ramp.sh
# ... and others
```

These examples are a great way to get started with the simulator and see its different modes of operation. The output data and plots from these examples will be saved in the `runs/` directory.
