"""
CrewAI adapter — wraps CrewAI tools with Argus security enforcement.

Uses a proxy/wrapper pattern around tool.run() — NOT CrewAI's on_tool_start /
on_tool_end callbacks. CrewAI backgrounds those callbacks, so security violations
would be silently swallowed. The proxy pattern intercepts synchronously and
fail-closed.

CrewAI call chain: framework calls tool.run() (public entry point) which
validates inputs against args_schema, then delegates to tool._run() (private).
This adapter intercepts at run() — the public boundary — so Argus gates fire
before any Pydantic validation and before _run() is ever reached on denial.

crewai is NOT a required install. This adapter uses duck typing (Any) and works
with any object that has .name and .run().

Usage:
    from argus.adapters.crewai import wrap_tools
    from argus.security.gateway import SecurityGateway, GatewayConfig
    from argus.security.audit.logger import AuditLogger

    gateway = SecurityGateway(config=GatewayConfig(), audit_logger=audit_logger)
    safe_tools = wrap_tools(tools, gateway=gateway, agent_role="my_agent")
    crew = Crew(agents=[agent], tasks=[task], tools=safe_tools)
"""

from __future__ import annotations

from typing import Any

from argus.security.gateway import SecurityGateway


class ArgusCrewAIToolWrapper:
    """Wraps a CrewAI tool with Argus security gates.

    Intercepts run() to run pre_tool_call and post_tool_call through
    the SecurityGateway. Exceptions propagate synchronously — never backgrounded.

    CrewAI typically passes tool inputs as keyword arguments matching the tool's
    Pydantic args_schema. String inputs are also supported (normalized for the
    gateway but passed unchanged to the underlying tool).
    """

    def __init__(
        self,
        tool: Any,
        gateway: SecurityGateway,
        agent_role: str = "default",
        caller_id: str | None = None,
        hop_depth: int = 0,
    ) -> None:
        self._tool = tool
        self._gateway = gateway
        self._agent_role = agent_role
        self._caller_id = caller_id
        self._hop_depth = hop_depth
        self.name = tool.name

    def run(self, *args: Any, **kwargs: Any) -> str:
        """Execute tool with Argus security enforcement."""
        # Normalize input for the gateway — dict passthrough, string wraps,
        # kwargs (Pydantic-style) captured as dict. Original args/kwargs
        # are passed unchanged to the underlying tool.run().
        if kwargs:
            tool_input: dict[str, Any] = kwargs
        elif args and isinstance(args[0], dict):
            tool_input = args[0]
        elif args:
            tool_input = {"input": args[0]}
        else:
            tool_input = {}

        # Set caller context ContextVars at the boundary if caller identity is known.
        # Lazy import to avoid import-time dependency on identity module.
        tokens = None
        if self._caller_id is not None:
            from argus.security.identity import reset_caller_context, set_caller_context

            tokens = set_caller_context(self._caller_id, self._hop_depth)

        try:
            # Pre-tool security gates (permission check, audit)
            self._gateway.pre_tool_call(self._agent_role, self.name, tool_input)

            # Execute the actual tool (pass original args/kwargs unchanged
            # so CrewAI's Pydantic validation runs on the real input)
            raw_output = self._tool.run(*args, **kwargs)
            output_str = str(raw_output) if not isinstance(raw_output, str) else raw_output

            # Post-tool security gates (injection scan, redaction, egress, audit)
            clean_output = self._gateway.post_tool_call(output_str)
        finally:
            if tokens is not None:
                from argus.security.identity import reset_caller_context

                reset_caller_context(tokens)

        return clean_output

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the wrapped tool."""
        return getattr(self._tool, name)


def wrap_tools(
    tools: list[Any],
    gateway: SecurityGateway,
    agent_role: str = "default",
    caller_id: str | None = None,
    hop_depth: int = 0,
) -> list[ArgusCrewAIToolWrapper]:
    """Wrap a list of CrewAI tools with Argus security enforcement.

    Args:
        tools: List of CrewAI BaseTool instances (or duck-typed equivalents).
        gateway: Configured SecurityGateway instance.
        agent_role: Role identifier for permission enforcement.
        caller_id: Optional calling agent identity for multi-agent enforcement.
            When set, ContextVars are set at each run() boundary and reset
            in a finally block (no identity leaks between calls).
        hop_depth: Delegation depth from the root supervisor (default 0 = direct).

    Returns:
        List of ArgusCrewAIToolWrapper instances (drop-in replacements).
    """
    return [
        ArgusCrewAIToolWrapper(
            tool=t,
            gateway=gateway,
            agent_role=agent_role,
            caller_id=caller_id,
            hop_depth=hop_depth,
        )
        for t in tools
    ]
