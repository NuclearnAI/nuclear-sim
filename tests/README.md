# Tests Module

This directory contains the test suite for the Nuclear Plant Simulator. It uses a custom testing framework (`base_test.py`) to validate the functionality, safety, and reliability of all major components.

For overall project information and architecture, see the main `README.md` in the root directory.

## Running Tests

### Full Test Suite
From the project root directory:
```bash
python tests/test_suite.py
```
Alternatively, using pytest:
```bash
python -m pytest tests/
```

### Individual Test Modules
To run a specific test module using the custom suite runner:
```bash
python tests/test_suite.py --module "Reactivity Model"
```
To list available modules:
```bash
python tests/test_suite.py --list
```
To run a specific test file using pytest:
```bash
python -m pytest tests/test_reactivity_model.py
```

## Structure
- **`base_test.py`**: Contains the `BaseTest` class and `TestAssertions` helper for writing tests.
- **`test_suite.py`**: The main runner for the custom test suite, capable of running all tests or specific modules.
- **`test_*.py` files**: Individual test modules for different components of the simulator (e.g., `test_reactivity_model.py`, `test_heat_sources.py`).

This test suite is crucial for ensuring the simulator's correctness and stability. Refer to the main project `README.md` for development and contribution guidelines.
