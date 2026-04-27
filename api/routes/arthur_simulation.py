"""
Arthur Simulation Routes
=================================
Endpoints para que Arthur aprenda jugando.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SimulationRequest(BaseModel):
    """Request para simulación"""
    faction: str = Field(default="Atreides", description="Facción a simular")
    games: int = Field(default=10, description="Número de partidas")


class SimulationResponse(BaseModel):
    """Response de simulación"""
    games_played: int
    winner: str
    turns: int
    details: Dict[str, Any]


@router.post("/simulate", response_model=List[SimulationResponse])
async def run_simulation(request: SimulationRequest):
    """
    🕹️ Ejecuta simulaciones de juego para que Arthur aprenda.
    
    Arthur jugara partidas automaticamente para aprender estrategias.
    """
    try:
        from ingest.game_simulator import run_simulation
        
        # Ejecutar simulaciones
        results = run_simulation(n=request.games, faction=request.faction)
        
        # Convertir a response
        return [
            SimulationResponse(
                games_played=1,
                winner=r.get("winner", "unknown"),
                turns=r.get("turns", 0),
                details=r
            )
            for r in results
        ]
        
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulation-stats")
async def get_simulation_stats():
    """
    📊 Obtiene estadísticas de simulaciones jugadas.
    """
    try:
        from ingest.game_simulator import get_simulation_stats
        return get_simulation_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/learn-strategy")
async def learn_strategy(faction: str):
    """
    🎓 Aprende la mejor estrategia para una facción.
    """
    try:
        from ingest.game_simulator import simulator
        return simulator.get_best_strategy(faction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))