# bbc_core/http_server.py
"""BBC Core HTTP Server - v8.3 Integrated"""

import os
import sys
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Central Logger
try:
    from bbc_core.bbc_logger import get_logger
    logger = get_logger("BBC-API")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bbc-api")

# BBC Core Imports
try:
    from bbc_core.hmpu_engine import HMPUEngine
    from bbc_core.state_manager import StateManager
    from bbc_core.native_adapter import BBCNativeAdapter
except ImportError as e:
    logger.critical(f"BBC Core import error: {e}")
    sys.exit(1)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Global variables
adapter: Optional[BBCNativeAdapter] = None
state_manager: Optional[StateManager] = None
startup_time = time.time()
PROJECT_ROOT = os.getenv("BBC_PROJECT_ROOT", ".")

class AnalyzeRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path of the file to analyze")
    analysis_type: str = Field("auto", description="Analysis type: log | code | data | auto")

class CreateRecipeRequest(BaseModel):
    content: str = Field(..., description="Raw text content to convert into a recipe")
    max_recipe_size: int = Field(5000, description="Maximum character size of the generated recipe")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global adapter, state_manager
    logger.info(f"--- BBC API SERVER STARTING (Project: {PROJECT_ROOT}) ---")
    try:
        # Initialize Core components
        state_manager = StateManager()
        adapter = BBCNativeAdapter(project_root=PROJECT_ROOT)
        logger.info("BBC Native Adapter and State Manager Ready.")
        yield
    finally:
        if state_manager:
            state_manager.close()
        logger.info("--- BBC API SERVER STOPPED ---")

app = FastAPI(
    title="BBC HMPU Core API", 
    description="BBC v8.3 Analysis & Integration API",
    version="8.3.0", 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

@app.get("/health")
async def health_check():
    mem_mb = 0
    try:
        import psutil
        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
    except (ImportError, Exception):
        pass

    return {
        "status": "healthy" if adapter and state_manager else "degraded",
        "service": "bbc_api",
        "version": "8.3.0",
        "adapter_ready": adapter is not None,
        "state_manager_ready": state_manager is not None,
        "memory_mb": round(mem_mb, 2),
        "uptime_seconds": round(time.time() - startup_time, 2),
        "cwd": os.getcwd()
    }

@app.post("/api/analyze")
async def analyze_file(request: AnalyzeRequest):
    if not adapter: 
        raise HTTPException(status_code=503, detail="Adapter not initialized")
    
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=400, detail="File not found")
    
    try:
        # Single file analysis using the same logic as project analysis
        # For simplicity, we wrap it in a pseudo-project analysis for one file
        # or use engine directly if adapter exposes it.
        result = await adapter.engine.analyze_file(request.file_path, request.analysis_type)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in analyze_file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/project_context")
async def get_project_context(silent: bool = True):
    """
    Tüm projenin BBC context'ini (recipe) üretir.
    NativeAdapter kullanır, dolayısıyla hmpu, index ve symbol analizi içerir.
    """
    if not adapter: 
        raise HTTPException(status_code=503, detail="Adapter not initialized")
    
    try:
        logger.info(f"Generating project context: {PROJECT_ROOT}")
        context = await adapter.analyze_project(PROJECT_ROOT, silent=silent)
        
        return {
            "success": True,
            "version": "8.3.0",
            "project_path": PROJECT_ROOT,
            "context": context
        }
    except Exception as e:
        logger.error(f"Error in get_project_context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbol_analysis")
async def get_symbol_analysis():
    """
    Projenin sembol analizi ve kritik sembol bilgisini döner.
    Daha önce yapılmış olan son analizin sonuçlarını context'ten çeker.
    """
    if not adapter:
        raise HTTPException(status_code=503, detail="Adapter not initialized")
    
    try:
        # Analysis trigger (if not already done)
        # In a real scenario, we might cache this or store in state_manager
        # For now, we perform a quick scan
        context = await adapter.analyze_project(PROJECT_ROOT, silent=True)
        symbol_data = context.get("symbol_analysis", {})
        
        if not symbol_data:
            return {"success": False, "message": "No symbol data generated"}
            
        return {
            "success": True,
            "data": symbol_data
        }
    except Exception as e:
        logger.error(f"Error in get_symbol_analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    if not state_manager: 
        raise HTTPException(status_code=503, detail="State manager not initialized")
    
    try:
        stats = state_manager.get_stats()
        # Add API specific stats
        stats.update({
            "api_version": "8.3.0",
            "uptime_seconds": round(time.time() - startup_time, 2),
            "adapter_ready": adapter is not None,
            "project_root": PROJECT_ROOT
        })
        return stats
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    port = int(os.getenv("BBC_API_PORT", 3333))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

