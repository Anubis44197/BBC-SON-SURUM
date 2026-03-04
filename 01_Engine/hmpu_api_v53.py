from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
from hmpu_core import HMPU_Governor

app = FastAPI(
    title="BBC HMPU v8.3.0 Industrial API",
    description="Hybrid Mathematical Processing Unit - Thread-Safe & Persistent Aura Field Dynamics",
    version="8.3.0"
)

governor = HMPU_Governor(weights_path="hmpu_weights.json")

# --- API Models ---
class SignalStream(BaseModel):
    chunks: List[str]
    threshold: float = 0.4

class FeedbackLoop(BaseModel):
    delta: float
    stability: bool

class PulseIntent(BaseModel):
    current_aura: float
    magnitude: float
    op_type: str

class FocusQuery(BaseModel):
    query_vec: List[float]
    targets: List[Dict[str, Any]]

# --- Endpoints ---

@app.get("/")
async def status():
    return {
        "engine": "HMPU v8.3.0 Industrial",
        "status": "Aura Field Stable",
        "features": ["Thread-Safe", "Persistent", "NaN-Resistant"],
        "operators": ["dC/dt", "nabla A", "P_t+1", "F_perp"]
    }

@app.post("/hmpu/v53/filter")
async def chaos_filter(data: SignalStream):
    """Operator 1: Chaos Derivative Filter"""
    try:
        signals = governor.chaos_derivative_filter(data.chunks, data.threshold)
        return {"signals": signals, "count": len(signals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hmpu/v53/bend")
async def aura_bend(data: FeedbackLoop):
    """Operator 2: Aura Gradient Bending"""
    try:
        governor.aura_gradient_bend(data.delta, data.stability)
        return {"status": "Aura Field Re-calibrated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hmpu/v53/predict")
async def pulse_predict(data: PulseIntent):
    """Operator 3: Pulse Perturbation Prediction"""
    try:
        return governor.pulse_perturbation_sim(data.current_aura, data.magnitude, data.op_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hmpu/v53/focus")
async def focus_projection(data: FocusQuery):
    """Operator 4: Focus Projection Search"""
    try:
        results = governor.focus_projection(data.query_vec, data.targets)
        return {"focused_results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hmpu/v53/aura-score")
async def get_aura_score(s: float, c: float, p: float):
    """Calculate current Aura Field Score"""
    score = governor.aura_field_score(s, c, p)
    return {"aura_score": round(score, 6)}

if __name__ == "__main__":
    print("Launching HMPU v8.3 Governor on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
