"""
Nuclear Plant Operator Game API

FastAPI backend that serves the game engine and provides WebSocket support
for real-time game updates.
"""

import asyncio
import json
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from game_engine import (
    ControlAction,
    GameDifficulty,
    GameState,
    NuclearOperatorGame,
)
from pydantic import BaseModel


class GameSessionRequest(BaseModel):
    """Request to start a new game session"""
    difficulty: str = "operator"
    duration: int = 1800  # 30 minutes default


class PlayerActionRequest(BaseModel):
    """Request to perform a player action"""
    action: str
    magnitude: float = 1.0


class GameSessionResponse(BaseModel):
    """Response containing game session info"""
    session_id: str
    difficulty: str
    duration: int
    status: str


class GameStateResponse(BaseModel):
    """Response containing current game state"""
    # Plant parameters
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
    
    # Game data
    score: int
    time_elapsed: float
    time_remaining: float
    current_perturbations: List[str]
    alarms: List[str]
    difficulty: str
    lives_remaining: int
    
    # Performance metrics
    safety_violations: int
    efficiency_score: float
    response_time_avg: float
    
    # Game status
    is_running: bool


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_game_state(self, session_id: str, game_state: GameState):
        if session_id in self.active_connections:
            try:
                # Convert GameState to dict for JSON serialization
                state_dict = {
                    "power_level": game_state.power_level,
                    "fuel_temperature": game_state.fuel_temperature,
                    "coolant_temperature": game_state.coolant_temperature,
                    "coolant_pressure": game_state.coolant_pressure,
                    "coolant_flow_rate": game_state.coolant_flow_rate,
                    "steam_temperature": game_state.steam_temperature,
                    "steam_pressure": game_state.steam_pressure,
                    "control_rod_position": game_state.control_rod_position,
                    "steam_valve_position": game_state.steam_valve_position,
                    "scram_status": game_state.scram_status,
                    "score": game_state.score,
                    "time_elapsed": game_state.time_elapsed,
                    "time_remaining": game_state.time_remaining,
                    "current_perturbations": game_state.current_perturbations,
                    "alarms": game_state.alarms,
                    "difficulty": game_state.difficulty.value,
                    "lives_remaining": game_state.lives_remaining,
                    "safety_violations": game_state.safety_violations,
                    "efficiency_score": game_state.efficiency_score,
                    "response_time_avg": game_state.response_time_avg,
                    "is_running": True  # Will be set by the caller
                }
                
                await self.active_connections[session_id].send_text(json.dumps(state_dict))
            except Exception as e:
                print(f"Error sending game state to {session_id}: {e}")
                self.disconnect(session_id)


# Initialize FastAPI app
app = FastAPI(
    title="Nuclear Plant Operator Game API",
    description="API for the nuclear plant operator training game",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
game_sessions: Dict[str, NuclearOperatorGame] = {}
connection_manager = ConnectionManager()


def generate_session_id() -> str:
    """Generate a unique session ID"""
    import uuid
    return str(uuid.uuid4())


def convert_game_state_to_response(game_state: GameState, is_running: bool) -> GameStateResponse:
    """Convert GameState to API response format"""
    return GameStateResponse(
        power_level=game_state.power_level,
        fuel_temperature=game_state.fuel_temperature,
        coolant_temperature=game_state.coolant_temperature,
        coolant_pressure=game_state.coolant_pressure,
        coolant_flow_rate=game_state.coolant_flow_rate,
        steam_temperature=game_state.steam_temperature,
        steam_pressure=game_state.steam_pressure,
        control_rod_position=game_state.control_rod_position,
        steam_valve_position=game_state.steam_valve_position,
        scram_status=game_state.scram_status,
        score=game_state.score,
        time_elapsed=game_state.time_elapsed,
        time_remaining=game_state.time_remaining,
        current_perturbations=game_state.current_perturbations,
        alarms=game_state.alarms,
        difficulty=game_state.difficulty.value,
        lives_remaining=game_state.lives_remaining,
        safety_violations=game_state.safety_violations,
        efficiency_score=game_state.efficiency_score,
        response_time_avg=game_state.response_time_avg,
        is_running=is_running
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Nuclear Plant Operator Game API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "active_sessions": len(game_sessions)}


@app.post("/game/start", response_model=GameSessionResponse)
async def start_game(request: GameSessionRequest):
    """Start a new game session"""
    try:
        # Validate difficulty
        try:
            difficulty = GameDifficulty(request.difficulty.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid difficulty: {request.difficulty}")
        
        # Generate session ID
        session_id = generate_session_id()
        
        # Create new game
        game = NuclearOperatorGame(difficulty=difficulty, game_duration=float(request.duration))
        game_sessions[session_id] = game
        
        return GameSessionResponse(
            session_id=session_id,
            difficulty=difficulty.value,
            duration=request.duration,
            status="started"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")


@app.get("/game/{session_id}/state", response_model=GameStateResponse)
async def get_game_state(session_id: str):
    """Get current game state"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    game_state = game.get_game_state()
    
    return convert_game_state_to_response(game_state, game.is_running)


@app.post("/game/{session_id}/action", response_model=GameStateResponse)
async def perform_action(session_id: str, request: PlayerActionRequest):
    """Perform a player action"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    
    # Convert action string to ControlAction enum
    try:
        action = ControlAction[request.action.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
    
    # Apply the action without advancing time
    game_state = game.apply_action(action, request.magnitude)
    
    # Send update via WebSocket if connected
    await connection_manager.send_game_state(session_id, game_state)
    
    return convert_game_state_to_response(game_state, game.is_running)


@app.post("/game/{session_id}/step", response_model=GameStateResponse)
async def step_game(session_id: str):
    """Step the game forward without player action (for automatic progression)"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    game_state = game.step()  # No action
    
    # Send update via WebSocket if connected
    await connection_manager.send_game_state(session_id, game_state)
    
    return convert_game_state_to_response(game_state, game.is_running)


@app.get("/game/{session_id}/summary")
async def get_game_summary(session_id: str):
    """Get game summary/results"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    return game.get_game_summary()


@app.post("/game/{session_id}/reset")
async def reset_game(session_id: str, request: Optional[GameSessionRequest] = None):
    """Reset the game session"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    
    # Reset with new difficulty if provided
    if request:
        try:
            difficulty = GameDifficulty(request.difficulty.lower())
            game.reset_game(difficulty)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid difficulty: {request.difficulty}")
    else:
        game.reset_game()
    
    return {"status": "reset", "session_id": session_id}


@app.delete("/game/{session_id}")
async def end_game(session_id: str):
    """End and cleanup a game session"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    # Cleanup
    del game_sessions[session_id]
    connection_manager.disconnect(session_id)
    
    return {"status": "ended", "session_id": session_id}


@app.get("/game/{session_id}/actions")
async def get_available_actions(session_id: str):
    """Get list of available control actions"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    game = game_sessions[session_id]
    actions = game.get_available_actions()
    
    return {
        "actions": [
            {
                "name": action.name,
                "value": action.value,
                "description": action.name.replace("_", " ").title()
            }
            for action in actions
        ]
    }


@app.websocket("/game/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time game updates"""
    if session_id not in game_sessions:
        await websocket.close(code=4004, reason="Game session not found")
        return
    
    await connection_manager.connect(websocket, session_id)
    game = game_sessions[session_id]
    
    try:
        # Send initial game state
        game_state = game.get_game_state()
        await connection_manager.send_game_state(session_id, game_state)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "action":
                    action_name = message.get("action")
                    magnitude = message.get("magnitude", 1.0)
                    
                    try:
                        action = ControlAction[action_name.upper()]
                        game_state = game.apply_action(action, magnitude)
                        await connection_manager.send_game_state(session_id, game_state)
                    except KeyError:
                        await websocket.send_text(json.dumps({
                            "error": f"Invalid action: {action_name}"
                        }))
                
                elif message.get("type") == "step":
                    # Step without action
                    game_state = game.step()
                    await connection_manager.send_game_state(session_id, game_state)
                
                elif message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
            except asyncio.TimeoutError:
                # Send periodic updates even without client messages
                game_state = game.get_game_state()
                await connection_manager.send_game_state(session_id, game_state)
    
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        connection_manager.disconnect(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
