# Nuclear Plant Operator Game Module

This directory contains an interactive nuclear plant operator training game built on top of the core simulator. It includes a FastAPI backend and a simple HTML/JS frontend.

For overall project information, see the main `README.md` in the root directory.

## 🚀 Quick Start

1.  **Start the API server:**
    ```bash
    cd game
    # Ensure requirements from game/requirements.txt are installed
    # e.g., pip install -r requirements.txt
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload 
    # Note: api.py defaults to port 8000, adjust if needed.
    ```

2.  **Open the game:**
    Open `game/frontend/index.html` in your web browser.

3.  **Play:**
    - Select difficulty level.
    - Click "START GAME".
    - Use control buttons to manage the plant.

## Key Components
- **`game_engine.py`**: Wraps the core simulator with game mechanics (perturbations, scoring).
- **`api.py`**: FastAPI backend providing REST API and WebSocket for real-time game updates.
- **`frontend/`**: Contains the simple HTML/JS frontend for the game.
- **`requirements.txt`**: Python dependencies specific to the game module.

Refer to the main project `README.md` for more details on the core simulator and overall architecture.
