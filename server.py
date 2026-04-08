from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from supportdesk_env import SupportDeskAction, SupportDeskEnv


class ResetRequest(BaseModel):
    task_name: Optional[str] = None


app = FastAPI(title="SupportDesk OpenEnv", version="1.1.0")
ENV: SupportDeskEnv | None = None


async def _get_env(task_name: str | None = None) -> SupportDeskEnv:
    global ENV
    selected_task = task_name or os.getenv("SUPPORTDESK_TASK", "easy_refund")
    if ENV is None or ENV.task_name != selected_task:
        ENV = await SupportDeskEnv.create(task_name=selected_task)
    return ENV


@app.get("/")
async def root():
    return {
        "name": "supportdesk_openenv",
        "status": "ok",
        "tasks": ["easy_refund", "medium_fraud_and_billing", "hard_multi_queue"],
    }


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


@app.post("/reset")
async def reset(req: ResetRequest | None = None):
    env = await _get_env(req.task_name if req else None)
    result = await env.reset()
    return result.model_dump()


@app.post("/step")
async def step(action: SupportDeskAction):
    env = await _get_env()
    result = await env.step(action)
    return result.model_dump()


@app.get("/state")
async def state():
    env = await _get_env()
    return env.state().model_dump()
