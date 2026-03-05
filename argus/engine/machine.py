"""
StateMachine — async 5-state runner. Full implementation in plan 02-03.
"""
from __future__ import annotations
from argus.engine.states import RunContext, RunResult


class StateMachine:
    """Async runner for the PLAN->EXECUTE->VERIFY->REFLECT->COMMIT state sequence."""

    def __init__(self, gateway, cost_hook, handlers=None, llm_callable=None):
        raise NotImplementedError("StateMachine implemented in plan 02-03")

    async def run(self, context: RunContext) -> RunResult:
        raise NotImplementedError("StateMachine implemented in plan 02-03")
