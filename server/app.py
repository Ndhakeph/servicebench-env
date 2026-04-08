# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the ServiceBench Environment.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /health: Health check

Usage:
    uvicorn server.app:app --host 0.0.0.0 --port 7860
"""

from __future__ import annotations

import sys
import os

# Ensure parent directory is importable for models / mock_services
_PARENT = os.path.join(os.path.dirname(__file__), "..")
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from fastapi import Body, FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional

from models import ServiceBenchAction
from server.servicebench_environment import ServiceBenchEnvironment

app = FastAPI(title="ServiceBench Environment", version="0.1.0")

# Single shared environment instance
_env = ServiceBenchEnvironment()


# --- Request / Response schemas ---

class ResetRequest(BaseModel):
    task_id: int = 1
    seed: Optional[int] = None
    episode_id: Optional[str] = None


class StepResponse(BaseModel):
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/reset")
def reset(req: Optional[ResetRequest] = Body(default=None)):
    seed = req.seed if req is not None else None
    episode_id = req.episode_id if req is not None else None
    task_id = req.task_id if req is not None else 1
    obs = _env.reset(seed=seed, episode_id=episode_id, task_id=task_id)
    return obs.model_dump()


@app.post("/step")
def step(action: ServiceBenchAction):
    result = _env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
def state():
    return _env.state.model_dump()


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
