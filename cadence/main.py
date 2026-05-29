from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from cadence.agent.graph import cadence_graph
from cadence.api.productions import router as productions_router

app = FastAPI(title="Cadence API", version="0.1.0")
app.include_router(productions_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas de request/response ───────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str

class GenerateResponse(BaseModel):
    export_path: str
    rsong: dict
    knowledge_level: str
    validation_score: float
    retry_count: int
    sections: list[str]
    bpm: int
    key: str
    duration_ms: int


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "cadence"}

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    if not request.prompt or len(request.prompt.strip()) < 3:
        raise HTTPException(status_code=422, detail="Prompt demasiado corto.")

    initial_state = {
        "messages": [HumanMessage(content=request.prompt)],
        "intent": None,
        "style_profile": None,
        "technical_proposal": None,
        "narrative": None,
        "harmony": None,
        "development": None,
        "strategies": None,
        "orchestration_plan": None,
        "style_coherence": None,
        "style_coherence_retries": 0,
        "arrangement": None,
        "generation_seed": 0,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "repair_target": None,
        "repair_layers": None,
        "export_path": None,
        "rsong_data": None,
    }

    try:
        final_state = cadence_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el agente: {str(e)}")

    proposal = final_state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120
    key = f"{proposal.key} {proposal.mode}" if proposal else "C minor"

    return GenerateResponse(
        export_path=final_state["export_path"],
        rsong=final_state["rsong_data"],
        knowledge_level=final_state["intent"].knowledge_level,
        validation_score=final_state["validation_result"].score,
        retry_count=final_state.get("retry_count", 0),
        sections=final_state["structure"].sections,
        bpm=bpm,
        key=key,
        duration_ms=final_state["structure"].estimated_duration_ms,
    )
