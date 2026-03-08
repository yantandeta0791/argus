"""
StateMachine -- async 5-state runner for Argus execution engine.

Enforces the deterministic invariant: no LLM output drives a state transition.
TRANSITION_SEQUENCE is the only valid order; cost_hook() fires before every state;
any exception triggers in-memory rollback of RunContext.artifacts (STM-03).

Phase 3 injects real LLM callable into handlers via llm_callable parameter.
Phase 4 injects SessionStore via store parameter for cross-run persistence.
Phase 2 state handlers are stubs; they receive llm_callable but do not call it.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Callable

from argus.engine.states import TaskState, RunContext, RunResult, LLMCallable

# Fixed forward sequence -- never re-ordered, never selected by LLM output (STM-02)
TRANSITION_SEQUENCE: list[TaskState] = [
    TaskState.PLAN,
    TaskState.EXECUTE,
    TaskState.VERIFY,
    TaskState.REFLECT,
    TaskState.COMMIT,
]


# Default no-op handler -- used when caller does not inject a handler for a state
async def _noop_handler(
    context: RunContext, llm: LLMCallable | None, *, store: Any = None
) -> None:
    """No-op stub for states that have no injected handler."""
    pass


class StateMachine:
    """Async runner that executes a task through the 5-state sequence.

    Handlers are async callables with signature:
        async def handler(context: RunContext, llm: LLMCallable | None, *, store=None) -> None

    Handlers mutate context.artifacts in-place. They must NOT return a state --
    the next state is always the next entry in TRANSITION_SEQUENCE (STM-02).

    Args:
        gateway:        SecurityGateway instance (passed through to ToolRunner in Phase 2).
                        The machine itself does not call gateway directly -- ToolRunner does.
        cost_hook:      Callable[[], bool]. Returns True if cost budget exceeded (STM-04).
                        Called before every state. Must be synchronous.
        handlers:       Optional dict mapping TaskState -> async handler callable.
                        Missing states use _noop_handler.
        llm_callable:   Optional LLMCallable injected by Phase 3. Passed to every handler.
                        None in Phase 2 tests.
        store:          Optional SessionStore injected by Phase 4. Passed to every handler
                        as a keyword argument. None when memory is not configured.
    """

    def __init__(
        self,
        gateway: Any,
        cost_hook: Callable[[], bool],
        handlers: dict[TaskState, Any] | None = None,
        llm_callable: LLMCallable | None = None,
        store: Any = None,
        obs: Any = None,
    ) -> None:
        self._gateway = gateway
        self._cost_hook = cost_hook
        self._llm_callable = llm_callable
        self._store = store
        self._obs = obs
        # Resolve handlers -- missing states fall back to no-op (STM-01: all 5 states must fire)
        self._handlers: dict[TaskState, Any] = {
            state: (handlers or {}).get(state, _noop_handler)
            for state in TRANSITION_SEQUENCE
        }

    async def run(self, context: RunContext) -> RunResult:
        """Execute the task through PLAN->EXECUTE->VERIFY->REFLECT->COMMIT.

        On any exception (including ArgusSecurityError from ToolRunner):
        - Rolls back context.artifacts to the pre-run snapshot (STM-03)
        - Returns RunResult with success=False and the failure state

        On cost budget exceeded before any state:
        - Returns RunResult with final_state=ABORT and success=False (STM-04)
        """
        # Snapshot working memory for rollback (STM-03)
        snapshot = copy.deepcopy(context)

        try:
            for state in TRANSITION_SEQUENCE:
                # Cost check before every state -- ABORT fires deterministically (STM-04)
                if self._cost_hook():
                    context.current_state = TaskState.ABORT
                    return RunResult(
                        task_id=context.task_id,
                        final_state=TaskState.ABORT,
                        artifacts=snapshot.artifacts,  # rolled back
                        error="Cost budget exceeded -- ABORT",
                        success=False,
                    )

                prior_state = context.current_state  # capture before updating

                # Set current state (observable by handlers via context.current_state)
                context.current_state = state

                # Dispatch to handler -- handler mutates context.artifacts (STM-01)
                # Phase 4: store passed as keyword argument for backward compatibility
                state_start = time.monotonic()
                handler = self._handlers[state]
                await handler(context, self._llm_callable, store=self._store)
                duration_ms = (time.monotonic() - state_start) * 1000

                if self._obs:
                    self._obs.on_state_transition(
                        prior_state, state, context, duration_ms
                    )

            # All 5 states completed -- run is successful
            result = RunResult(
                task_id=context.task_id,
                final_state=TaskState.COMMIT,
                artifacts=context.artifacts,
                error=None,
                success=True,
            )
            if self._obs:
                self._obs.on_run_complete(result)
            return result

        except Exception as exc:
            # Rollback working memory to pre-run snapshot (STM-03)
            # ArgusSecurityError falls here too -- no special security handling in machine
            context.artifacts = snapshot.artifacts
            context.error = exc
            return RunResult(
                task_id=context.task_id,
                final_state=context.current_state,  # state where failure occurred
                artifacts=context.artifacts,
                error=str(exc),
                success=False,
            )
