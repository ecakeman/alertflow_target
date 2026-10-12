"""场景目录的只读接口。

只读、无副作用：Runner 拉目录、自己驱动测试。Fault Lab 不参与执行，
也不观测 AlertFlow / Agent——边界不变。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .scenarios import BY_ID, SCENARIOS

router = APIRouter()


@router.get("/scenarios")
async def list_scenarios(tag: Optional[str] = Query(default=None, description="按标签过滤")):
    scenarios = [s for s in SCENARIOS if not tag or tag in s.tags]
    return {"count": len(scenarios), "scenarios": [s.model_dump(mode="json") for s in scenarios]}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    scenario = BY_ID.get(scenario_id)
    if scenario is None:
        return JSONResponse({"error": "unknown scenario"}, status_code=404)
    return scenario.model_dump(mode="json")
