"""
Arthur Routes - Endpoints de la API de Arthur
===========================================
Endpoints para interactuar con Arthur.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from ..pipelines.arthur_pipeline import (
    ArthurPipeline,
    ArthurQueryRequest,
    ArthurConfig
)

router = APIRouter()
pipeline = ArthurPipeline()


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMAS - Tipos de request/response
# ═══════════════════════════════════════════════════════════════════════════

class ArthurQueryRequestSchema(BaseModel):
    """Request para consultar a Arthur"""
    question: str = Field(..., description="Pregunta del jugador")
    mode: str = Field(
        default="contextual",
        description="Modo de Arthur: contextual, strategic, narrative, observer, mentor, companion"
    )
    game_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Estado actual del juego (opcional)"
    )
    player_history: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Historial del jugador (opcional)"
    )
    player_id: Optional[str] = Field(
        default=None,
        description="ID del jugador para personalización (opcional)"
    )


class ArthurResponseSchema(BaseModel):
    """Response de Arthur"""
    answer: str
    sources: List[Dict[str, Any]]
    mode_used: str
    arthur_tone: bool = True
    success: bool = True
    error: Optional[str] = None


class RecommendationRequestSchema(BaseModel):
    """Request para recomendación estratégica"""
    player_id: str
    game_state: Dict[str, Any]
    question: Optional[str] = None


class RecommendationResponseSchema(BaseModel):
    """Respuesta de recomendación"""
    recommendation: str
    alternatives: List[str]
    reasoning: str
    confidence: float
    historical_precedent: Optional[str] = None


class PlayerProfileSchema(BaseModel):
    """Perfil de un jugador"""
    player_id: str
    games_played: int = 0
    wins: int = 0
    favorite_faction: Optional[str] = None
    playstyle: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.post("/query", response_model=ArthurResponseSchema)
async def arthur_query(request: ArthurQueryRequestSchema):
    """
    🎯 Consulta principal a Arthur.
    
    Args:
        question: La pregunta del jugador
        modo: Modo de interacción (contextual, strategic, narrative, observer, mentor, companion)
        game_state: Estado actual del juego (opcional)
        player_history: Historial del jugador (opcional)
    
    Returns:
        Respuesta de Arthur con personalidad
    """
    try:
        arthur_request = ArthurQueryRequest(
            question=request.question,
            mode=request.mode,
            game_state=request.game_state,
            player_history=request.player_history,
            player_id=request.player_id
        )
        
        result = pipeline.query(arthur_request)
        
        return ArthurResponseSchema(
            answer=result.answer,
            sources=result.sources,
            mode_used=result.mode_used,
            arthur_tone=result.arthur_tone,
            success=result.success,
            error=result.error
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes")
async def get_modes():
    """
    📋 Lista los modos disponibles de Arthur.
    """
    from ..pipelines.arthur_pipeline import ARTHUR_MODES
    return {"modes": ARTHUR_MODES}


@router.get("/stats")
async def get_stats():
    """
    📊 Obtiene estadísticas del sistema Arthur.
    """
    return pipeline.get_stats()


@router.post("/recommend", response_model=RecommendationResponseSchema)
async def get_recommendation(request: RecommendationRequestSchema):
    """
    🎯 Obtiene recomendación estratégica personalizada.
    
    Args:
        player_id: ID del jugador
        game_state: Estado actual del juego
        question: Pregunta específica (opcional)
    
    Returns:
        Recomendación con alternativas y reasoning
    """
    try:
        # Construir query
        question = request.question or "¿Qué me recomienda para esta situación?"
        
        arthur_request = ArthurQueryRequest(
            question=question,
            mode="strategic",
            game_state=request.game_state,
            player_id=request.player_id
        )
        
        result = pipeline.query(arthur_request)
        
        return RecommendationResponseSchema(
            recommendation=result.answer,
            alternatives=[],  # TODO: implementar alternativas
            reasoning="Basado en el análisis de tu situación",
            confidence=0.75,
            historical_precedent=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{player_id}", response_model=PlayerProfileSchema)
async def get_player_profile(player_id: str):
    """
    👤 Obtiene el perfil de un jugador.
    """
    # TODO: integrar con player profile DB
    return PlayerProfileSchema(
        player_id=player_id,
        games_played=0,
        wins=0,
        favorite_faction=None,
        playstyle=None,
        strengths=[],
        weaknesses=[]
    )


@router.get("/health")
async def health_check():
    """
    ❤️ Verifica el estado de Arthur.
    """
    try:
        stats = pipeline.get_stats()
        return {
            "status": "healthy" if "error" not in stats else "degraded",
            "arthur_version": "1.0.0",
            "services": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }