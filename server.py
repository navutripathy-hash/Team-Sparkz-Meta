"""
server.py -- AuditRepairEnv++ OpenEnv Server
=============================================
FastAPI server: /reset, /step, /state, /health
OpenEnv-compliant, HuggingFace-ready, port 7860.
"""

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tasks import TASK_CONFIGS, TASK_IDS, LedgerEnvironment, AuditObservation


# ────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None, description="easy | medium | hard")

class StepAction(BaseModel):
    message: str = Field(..., description="Agent action text, e.g. 'FIX_ENTRY 1'")

class StepResponse(BaseModel):
    observation: AuditObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
    last_action_error: Optional[str] = None

class StateResponse(BaseModel):
    episode_id: str
    task_id: str
    step: int
    max_steps: int
    total_reward: float
    done: bool
    remaining_budget: int
    initial_budget: int
    errors_count: int
    history: List[Dict[str, Any]]
    started_at: float


# ────────────────────────────────────────
# EPISODE STATE
# ────────────────────────────────────────

class EpisodeState:
    def __init__(self, env: LedgerEnvironment):
        self.episode_id = str(uuid.uuid4())
        self.env = env
        self.total_reward = 0.0
        self.history: List[Dict[str, Any]] = []
        self.started_at = time.time()


_current_episode: Optional[EpisodeState] = None


# ────────────────────────────────────────
# FASTAPI APP
# ────────────────────────────────────────

app = FastAPI(title="AuditRepairEnv++", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def root():
    return {"name": "AuditRepairEnv++", "status": "running", "docs": "/docs", "message": "API is live."}


# ────────────────────────────────────────
# OPENENV ENDPOINTS
# ────────────────────────────────────────

async def _do_reset(task_id: Optional[str] = None):
    global _current_episode

    tid = task_id or "easy"
    if tid not in TASK_CONFIGS:
        raise HTTPException(400, f"Unknown task '{tid}'. Available: {TASK_IDS}")

    config = TASK_CONFIGS[tid]
    env = config.create_env()
    _current_episode = EpisodeState(env)

    obs = env.get_observation(echoed_message=f"Environment reset. Task: {config.name}")
    return obs.model_dump()


@app.post("/reset")
async def reset_post(request: ResetRequest = ResetRequest()):
    return await _do_reset(request.task_id)


@app.get("/reset")
async def reset_get(task_id: Optional[str] = None):
    return await _do_reset(task_id)


@app.post("/step")
async def step(action: StepAction):
    global _current_episode

    if _current_episode is None:
        raise HTTPException(400, "No active episode. Call /reset first.")
    if _current_episode.env.done:
        raise HTTPException(400, "Episode finished. Call /reset to start a new one.")

    ep = _current_episode
    result = ep.env.step_with_message(action.message)

    reward = float(result.get("reward", 0))
    done = bool(result.get("done", False))
    error = result.get("error")

    ep.total_reward = round(ep.total_reward + reward, 4)
    ep.history.append({
        "step": ep.env.step,
        "action": action.message[:200],
        "reward": reward,
        "done": done,
        "info": result.get("result", ""),
    })

    final_score = None
    if done:
        final_score = ep.env.compute_final_score()

    return StepResponse(
        observation=result["observation"],
        reward=reward,
        done=done,
        info={
            "total_reward": ep.total_reward,
            "episode_id": ep.episode_id,
            "result": result.get("result", ""),
            "final_score": final_score,
        },
        last_action_error=error,
    ).model_dump()


@app.get("/state")
async def state():
    if _current_episode is None:
        raise HTTPException(400, "No active episode. Call /reset first.")
    ep = _current_episode
    return StateResponse(
        episode_id=ep.episode_id,
        task_id=ep.env.task_id,
        step=ep.env.step,
        max_steps=ep.env.max_steps,
        total_reward=ep.total_reward,
        done=ep.env.done,
        remaining_budget=ep.env.remaining_budget,
        initial_budget=ep.env.initial_budget,
        errors_count=len(ep.env.get_errors()),
        history=ep.history,
        started_at=ep.started_at,
    ).model_dump()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": "AuditRepairEnv++",
        "tasks": TASK_IDS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)