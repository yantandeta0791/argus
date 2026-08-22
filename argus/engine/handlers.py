"""
Default state handlers — the real agent loop for `argus run`.

Each handler is an async callable matching the StateMachine handler signature:
    async def handler(context: RunContext, llm: LLMCallable | None, *, store=None) -> None

Handlers call the injected LLMCallable (LLMRouter), parse any tool-call request
from the model response, and execute it through ToolRunner (which crosses the
SecurityGateway seam). Artifacts accumulate in context.artifacts.

The gateway and observability manager are closed over at construction time
(default_handlers), because the StateMachine dispatches handlers with a fixed
signature and cannot pass extra kwargs.

Design invariants preserved:
- Transitions are still driven solely by TRANSITION_SEQUENCE (machine.py).
- All tool execution crosses SecurityGateway pre/post gates via ToolRunner.
- COMMIT never calls the LLM (config `COMMIT: null` contract).
"""

from __future__ import annotations

import json
import re
from typing import Any

from argus.engine.states import RunContext, TaskState
from argus.engine.tools import ToolManifest, ToolRunner


# Matches a JSON object like: {"tool": "name", "input": {...}}
_TOOL_CALL_RE = re.compile(
    r"\{[\s\S]*?\"tool\"\s*:\s*\"(?P<name>[^\"]+)\"[\s\S]*?\"input\"\s*:\s*(?P<input>\{.*?\})\s*\}",
    re.DOTALL,
)


class ToolRegistry:
    """Name -> (ToolManifest, tool_fn) mapping shared by all handlers."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolManifest, Any]] = {}

    def register(self, manifest: ToolManifest, tool_fn: Any) -> None:
        self._tools[manifest.name] = (manifest, tool_fn)

    def get(self, name: str) -> tuple[ToolManifest, Any] | None:
        return self._tools.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


async def _call_llm(context: RunContext, llm: Any) -> str:
    """Invoke the LLM callable; returns response text ('' when no LLM configured)."""
    if llm is None:
        return ""
    result: dict[str, Any] = await llm(context)
    return str(result.get("response", ""))


def _parse_tool_call(response_text: str) -> tuple[str, dict] | None:
    """Extract the first tool-call request from response text, or None."""
    match = _TOOL_CALL_RE.search(response_text)
    if not match:
        return None
    try:
        raw_input = json.loads(match.group("input"))
    except json.JSONDecodeError:
        return None
    return match.group("name"), raw_input


def default_handlers(
    registry: ToolRegistry | None = None,
    gateway: Any = None,
    obs: Any = None,
) -> dict[TaskState, Any]:
    """Build the standard handler set wired to a shared ToolRegistry.

    Args:
        registry: ToolRegistry with registered ToolManifests + tool callables.
        gateway:  SecurityGateway (or test double). Every tool execution crosses
                  its pre/post gates via ToolRunner. Required for tool execution;
                  None means tool calls are recorded as blocked (fail closed).
        obs:      Optional ObservabilityManager forwarded to ToolRunner.
    """
    tools = registry if registry is not None else ToolRegistry()

    async def _run_tool_request(
        context: RunContext, response_text: str, agent_role: str = "agent"
    ) -> dict[str, Any] | None:
        """Execute at most one tool-call request from the response text.

        Fail-closed rules:
        - Unknown tool name -> recorded in blocked_tools, never executed.
        - No gateway configured -> recorded in blocked_tools, never executed.
        """
        parsed = _parse_tool_call(response_text)
        if parsed is None:
            return None
        name, raw_input = parsed
        entry = tools.get(name)
        if entry is None or gateway is None:
            context.artifacts.setdefault("blocked_tools", []).append(name)
            return None
        manifest, tool_fn = entry
        runner = ToolRunner(manifest, tool_fn, gateway, obs=obs)
        validated = await runner.call(agent_role, raw_input)
        record = {
            "tool": name,
            "state": str(context.current_state),
            "output": validated.model_dump(),
        }
        context.artifacts.setdefault("tool_calls", []).append(record)
        return record["output"]

    async def plan_handler(context: RunContext, llm: Any, *, store: Any = None) -> None:
        text = await _call_llm(context, llm)
        context.artifacts["plan"] = text
        # A plan may propose a read-only discovery tool call.
        await _run_tool_request(context, text)

    async def execute_handler(context: RunContext, llm: Any, *, store: Any = None) -> None:
        text = await _call_llm(context, llm)
        output = await _run_tool_request(context, text)
        context.artifacts["execution_output"] = output if output is not None else text

    async def verify_handler(context: RunContext, llm: Any, *, store: Any = None) -> None:
        text = await _call_llm(context, llm)
        context.artifacts["verification"] = text
        output = await _run_tool_request(context, text)
        if output is not None:
            context.artifacts["verification_evidence"] = output

    async def reflect_handler(context: RunContext, llm: Any, *, store: Any = None) -> None:
        text = await _call_llm(context, llm)
        context.artifacts["reflection"] = text

    async def commit_handler(context: RunContext, llm: Any, *, store: Any = None) -> None:
        """Deterministic finalization — never calls the LLM (COMMIT: null contract)."""
        context.artifacts["committed"] = True
        context.artifacts.setdefault(
            "summary",
            {
                "task_id": context.task_id,
                "tool_call_count": len(context.artifacts.get("tool_calls", [])),
                "blocked_tool_count": len(context.artifacts.get("blocked_tools", [])),
            },
        )

    return {
        TaskState.PLAN: plan_handler,
        TaskState.EXECUTE: execute_handler,
        TaskState.VERIFY: verify_handler,
        TaskState.REFLECT: reflect_handler,
        TaskState.COMMIT: commit_handler,
    }
