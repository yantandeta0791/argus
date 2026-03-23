"""AutoGen adapter for Argus security enforcement.

AutoGen's DefaultInterventionHandler operates at the message-passing level —
too coarse for per-tool security gates. This adapter uses the FunctionTool
closure pattern: each secured tool is a FunctionTool whose inner async function
calls the Argus gateway gates (pre_tool_call / post_tool_call) then delegates
to the original tool.

This is fail-closed: any ArgusSecurityError raised by the gateway propagates
directly to the AutoGen framework — no exceptions are caught or swallowed here.
"""

from __future__ import annotations

from typing import Any

from argus.security.gateway import SecurityGateway


def _wrap_single_autogen_tool(
    tool: Any,
    gateway: SecurityGateway,
    agent_role: str,
) -> Any:
    # Lazy imports — no hard dep at module level
    from autogen_core.tools import FunctionTool  # type: ignore[import]
    from autogen_core import CancellationToken  # type: ignore[import]

    _name_attr = getattr(tool, "name", None)
    original_name: str = (
        _name_attr
        if isinstance(_name_attr, str)
        else getattr(tool, "__name__", "unknown_tool")
    )
    description: str = (
        getattr(tool, "description", None)
        or getattr(tool, "__doc__", None)
        or "Argus-secured tool"
    )

    import asyncio as _asyncio

    # Distinguish BaseTool (has run_json, is not itself a coroutinefunction)
    # from a plain async callable (is itself a coroutinefunction).
    _is_plain_callable = _asyncio.iscoroutinefunction(tool)

    async def _secured(**kwargs: Any) -> str:
        tool_input: dict[str, Any] = kwargs
        # Pre-tool gates (sync call inside async — valid Python)
        gateway.pre_tool_call(agent_role, original_name, tool_input)

        if _is_plain_callable:
            # Plain async callable path
            raw_output = await tool(**kwargs)
        else:
            # BaseTool path: run_json(args_dict, cancellation_token)
            token = CancellationToken()
            raw_output = await tool.run_json(kwargs, token)

        output_str = str(raw_output) if not isinstance(raw_output, str) else raw_output
        # Post-tool gates
        return gateway.post_tool_call(output_str)

    _secured.__name__ = original_name
    return FunctionTool(_secured, description=description, name=original_name)


def wrap_tools(
    tools: list[Any],
    gateway: SecurityGateway,
    agent_role: str = "default",
) -> list[Any]:
    """Wrap a list of AutoGen tools with Argus security gates.

    Args:
        tools: List of AutoGen tools (BaseTool subclasses or plain async callables).
        gateway: The SecurityGateway instance providing pre/post_tool_call hooks.
        agent_role: The role of the agent using these tools (used in policy checks).

    Returns:
        A list of FunctionTool instances, each wrapping the corresponding input tool
        with pre_tool_call and post_tool_call security enforcement.
    """
    return [_wrap_single_autogen_tool(t, gateway, agent_role) for t in tools]
