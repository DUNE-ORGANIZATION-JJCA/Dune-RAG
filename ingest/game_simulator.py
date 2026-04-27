"""
Arthur Game Simulator - FASE 2
=============================
Simula partidas de Dune: Arrakis Dominion para aprender estrategias.
Se ejecuta en background - no afecta al chat.
"""

import os
import json
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class GameState:
    """Estado del juego Dune: Arrakis Dominion"""
    
    def __init__(self):
        self.turn = 1
        self.phase = "storm"  # storm, spice, action, battle, revenue
        self.players = {}
        self.board = {}
        self.spice = {}
        self.storm_pos = 0
        self.winner = None
    
    def reset(self):
        """Reinicia el juego."""
        self.turn = 1
        self.phase = "storm"
        self.players = {
            "Atreides": {"units": [], "strongholds": 2, "spice": 10, "alive": True},
            "Harkonnen": {"units": [], "strongholds": 2, "spice": 10, "alive": True},
            "Corrino": {"units": [], "strongholds": 2, "spice": 8, "alive": True}
        }
        self.board = {
            "regions": ["Sietes", "Carthay", "Arrakeen", "Giedi Prime", "Caladan", "Salusa", "Deep Desert"],
            "strongholds": {"Sietes": None, "Carthay": None, "Arrakeen": None, "Giedi Prime": "Harkonnen", "Caladan": "Atreides", "Salusa": "Corrino", "Deep Desert": None}
        }
        self.spice = {k: random.randint(0, 5) for k in self.board["regions"]}
        self.storm_pos = random.randint(0, 6)
        self.winner = None
    
    def is_game_over(self) -> bool:
        """Verifica si hay ganador."""
        alive = [p for p, d in self.players.items() if d["alive"] and d["strongholds"] > 0]
        if len(alive) <= 1:
            self.winner = alive[0] if alive else "draw"
            return True
        
        # Victoria por especia
        for p, d in self.players.items():
            if d.get("spice", 0) >= 100:
                self.winner = p
                return True
        return False
    
    def get_state_summary(self) -> str:
        """Resumen del estado para Arthur."""
        lines = [f"Turno {self.turn}, Fase: {self.phase}"]
        for player, data in self.players.items():
            lines.append(f"{player}: {data['strongholds']} fuertes, {data['spice']} especia")
        return "\n".join(lines)


class GameSimulator:
    """
    Simula partidas completas para que Arthur aprende estrategias.
    """
    
    def __init__(self):
        self.games_played = 0
        self.strategies = {}
        self.learnings = []
    
    def simulate_game(self, faction: str = "Atreides") -> Dict[str, Any]:
        """Simula una partida completa."""
        state = GameState()
        state.reset()
        
        game_record = {
            "faction": faction,
            "decisions": [],
            "outcomes": [],
            "winner": None,
            "turns": 0
        }
        
        # Simular hasta que alguien gane
        while not state.is_game_over():
            game_record["turns"] += 1
            
            # Fase actual
            phase = state.phase
            
            # Decisión basada en estrategia
            decision = self._make_decision(faction, state)
            game_record["decisions"].append({
                "turn": state.turn,
                "phase": phase,
                "decision": decision,
                "state": state.get_state_summary()
            })
            
            # Ejecutar acción
            outcome = self._execute_action(faction, state, decision)
            game_record["outcomes"].append(outcome)
            
            # Avanzar fase/turno
            self._advance_phase(state)
        
        game_record["winner"] = state.winner
        self.games_played += 1
        
        # Analizar y guardar aprendizaje
        self._analyze_game(game_record)
        
        return game_record
    
    def _make_decision(self, faction: str, state: GameState) -> str:
        """Toma una decisión estratégica."""
        player = state.players.get(faction)
        if not player:
            return "esperar"
        
        spice = player.get("spice", 0)
        strongholds = player.get("strongholds", 0)
        
        # Estrategia simple basada en recursos
        if spice < 30 and strongholds < 3:
            return "recoger_especia"
        elif strongholds < 5 and spice > 20:
            return "atacar_fuerte"
        elif state.phase == "battle":
            return "combatir"
        else:
            return "construir_unidad"
    
    def _execute_action(self, faction: str, state: GameState, decision: str) -> Dict:
        """Ejecuta una acción."""
        player = state.players.get(faction)
        
        if decision == "recoger_especia":
            # Recoger especia de territorios controlados
            collected = random.randint(1, 5)
            if player:
                player["spice"] = player.get("spice", 0) + collected
            return {"action": "recoger", "collected": collected}
        
        elif decision == "atacar_fuerte":
            # Atacar fuerte enemigo
            enemy = random.choice(["Atreides", "Harkonnen", "Corrino"])
            if enemy != faction and state.players.get(enemy, {}).get("strongholds", 0) > 0:
                if player:
                    player["strongholds"] = player.get("strongholds", 0) + 1
                if enemy in state.players:
                    state.players[enemy]["strongholds"] = max(0, state.players[enemy].get("strongholds", 1) - 1)
                return {"action": "atacar", "target": enemy, "success": True}
        
        elif decision == "combatir":
            # Combatir
            roll = random.randint(1, 6) + random.randint(1, 6)
            enemy_roll = random.randint(1, 6) + random.randint(1, 6)
            return {"action": "combatir", "our_roll": roll, "enemy_roll": enemy_roll, "win": roll > enemy_roll}
        
        else:
            # Construir unidad
            cost = random.randint(3, 8)
            if player and player.get("spice", 0) >= cost:
                player["spice"] = player.get("spice", 0) - cost
                return {"action": "construir", "cost": cost}
        
        return {"action": decision, "result": "completed"}
    
    def _advance_phase(self, state: GameState):
        """Avanza fase del juego."""
        phases = ["storm", "spice", "action", "battle", "revenue"]
        current_idx = phases.index(state.phase)
        
        if current_idx < len(phases) - 1:
            state.phase = phases[current_idx + 1]
        else:
            state.phase = "storm"
            state.turn += 1
    
    def _analyze_game(self, record: Dict):
        """Analiza la partida y guarda aprendizaje."""
        winner = record["winner"]
        faction = record["faction"]
        turns = record["turns"]
        
        # Guardar resultado
        learning = {
            "date": datetime.now().isoformat(),
            "faction": faction,
            "winner": winner,
            "turns": turns,
            "decisions_count": len(record["decisions"])
        }
        
        self.learnings.append(learning)
        
        # Mantener solo últimos 100 aprendizajes
        if len(self.learnings) > 100:
            self.learnings = self.learnings[-100:]
        
        logger.info(f"Game {self.games_played}: {winner} wins in {turns} turns")
    
    def get_best_strategy(self, faction: str) -> Dict[str, Any]:
        """Obtiene la mejor estrategia para una facción."""
        wins = [l for l in self.learnings if l["faction"] == faction and l["winner"] == faction]
        losses = [l for l in self.learnings if l["faction"] == faction and l["winner"] != faction]
        
        return {
            "faction": faction,
            "games_played": len([l for l in self.learnings if l["faction"] == faction]),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / max(1, len(wins) + len(losses)),
            "avg_turns": sum(l["turns"] for l in wins) / max(1, len(wins))
        }
    
    def run_simulation_batch(self, n: int = 10, faction: str = "Atreides"):
        """Ejecuta N simulaciones."""
        results = []
        for i in range(n):
            result = self.simulate_game(faction)
            results.append(result)
            if (i + 1) % 5 == 0:
                logger.info(f"Simulated {i + 1}/{n} games")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del simulador."""
        return {
            "games_played": self.games_played,
            "total_learnings": len(self.learnings),
            "strategies": {f: self.get_best_strategy(f) for f in ["Atreides", "Harkonnen", "Corrino"]}
        }


# Instancia global
simulator = GameSimulator()


def run_simulation(n: int = 10, faction: str = "Atreides"):
    """ función para ejecutar simulaciones """
    try:
        return simulator.run_simulation_batch(n, faction)
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return []


def get_simulation_stats():
    """ obtener estadísticas """
    try:
        return simulator.get_stats()
    except:
        return {}