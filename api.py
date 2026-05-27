"""
FastAPI service que expoe o roulette_analyzer via HTTP.

Endpoints:
  POST /analyze       -> roda detect_bias + simulacao, retorna JSON
  POST /spin          -> registra um giro num storage em memoria (ou Supabase)
  GET  /history/{w}   -> historico do wheel
  GET  /report/{w}    -> ultima analise consolidada
  GET  /health        -> healthcheck

Rodar local:
  pip install fastapi uvicorn
  uvicorn api:app --reload --port 8000

Rodar producao:
  uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.wheel import get_wheel
from core.bias import detect_bias
from core.strategies import compare_all_strategies
from core.ev import evaluate_all_numbers


app = FastAPI(title="Roulette Analyzer", version="0.1.0")

# Storage em memoria. Em producao, substituir por Supabase / Postgres.
_history: dict[str, list[str]] = defaultdict(list)
_timestamps: dict[str, list[str]] = defaultdict(list)


class SpinIn(BaseModel):
    wheel_id: str = Field(..., description="ID do wheel (ex.: 'casino-x-mesa-3')")
    wheel_type: str = Field("european", description="european | american")
    number: str = Field(..., description="numero do giro (0-36 ou '00')")
    timestamp: Optional[str] = None


class AnalyzeIn(BaseModel):
    wheel: str = "european"
    spins: List[str]
    run_simulation: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "wheels_tracked": len(_history)}


@app.post("/spin")
def add_spin(spin: SpinIn):
    wheel = get_wheel(spin.wheel_type)
    if spin.number not in wheel.position:
        raise HTTPException(400, f"Numero invalido para roda {spin.wheel_type}: {spin.number}")
    _history[spin.wheel_id].append(spin.number)
    _timestamps[spin.wheel_id].append(spin.timestamp or datetime.utcnow().isoformat())
    return {"ok": True, "wheel_id": spin.wheel_id, "total_spins": len(_history[spin.wheel_id])}


@app.get("/history/{wheel_id}")
def get_history(wheel_id: str, limit: int = 1000):
    spins = _history.get(wheel_id, [])
    return {"wheel_id": wheel_id, "total": len(spins), "last": spins[-limit:]}


@app.post("/analyze")
def analyze(body: AnalyzeIn):
    wheel = get_wheel(body.wheel)
    wheel.validate_spins(body.spins)
    bias = detect_bias(body.spins, wheel)
    sim = None
    if body.run_simulation and len(body.spins) > 0:
        sim = compare_all_strategies(wheel, n_sessions=500)
    return {"bias": bias, "strategies": sim}


@app.get("/report/{wheel_id}")
def report(wheel_id: str, wheel_type: str = "european"):
    spins = _history.get(wheel_id, [])
    if not spins:
        raise HTTPException(404, f"Sem historico para {wheel_id}")
    wheel = get_wheel(wheel_type)
    bias = detect_bias(spins, wheel)
    top_ev = evaluate_all_numbers(spins, wheel)[:10]
    return {
        "wheel_id": wheel_id,
        "n_spins": len(spins),
        "verdict": bias["verdict"],
        "confidence": bias["confidence"],
        "summary": bias["honest_summary"],
        "top_ev_numbers": top_ev,
        "hot_sectors": bias["full_tests"]["tests"]["sectors"].get("hot_sectors", []),
        "top_hot_numbers": bias["full_tests"]["tests"]["z_scores"]["top_hot"],
    }


@app.delete("/history/{wheel_id}")
def clear_history(wheel_id: str):
    n = len(_history.pop(wheel_id, []))
    _timestamps.pop(wheel_id, None)
    return {"cleared": n}
