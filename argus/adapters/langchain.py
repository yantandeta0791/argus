"""
LangChain adapter — wraps LangChain tools with Argus security enforcement.

Uses a proxy/wrapper pattern around tool.invoke() — NOT a BaseCallbackHandler.
LangChain v1 backgrounds callbacks, so security violations would be silently
swallowed. The proxy pattern intercepts synchronously and fail-closed.

Usage:
    from argus.adapters.langchain import wrap_tools
    from argus.security.gateway import SecurityGateway, GatewayConfig
    from argus.security.audit.logger import AuditLogger

    gateway = SecurityGateway(config=GatewayConfig(), audit_logger=audit_logger)
    safe_tools = wrap_tools(tools, gateway=gateway, agent_role="my_agent")
    agent = create_react_agent(llm, safe_tools)
"""

from __future__ import annotations

from typing import Any

from argus.security.gateway import SecurityGateway


class ArgusToolWrapper:
    """Wraps a LangChain tool with Argus security gates.

    Intercepts invoke() to run pre_tool_call and post_tool_call through
    the SecurityGateway. Exceptions propagate synchronously — never backgrounded.
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

    def invoke(self, input: dict[str, Any] | str, **kwargs: Any) -> str:
        """Execute tool with Argus security enforcement."""
        tool_input = input if isinstance(input, dict) else {"input": input}

        # Set caller context ContextVars at the boundary if caller identity is known.
        # Lazy import to avoid import-time dependency on identity module.
        tokens = None
        if self._caller_id is not None:
            from argus.security.identity import reset_caller_context, set_caller_context

            tokens = set_caller_context(self._caller_id, self._hop_depth)

        try:
            # Pre-tool security gates (permission check, audit)
            self._gateway.pre_tool_call(self._agent_role, self.name, tool_input)

            # Execute the actual tool
            raw_output = self._tool.invoke(input, **kwargs)
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
) -> list[ArgusToolWrapper]:
    """Wrap a list of LangChain tools with Argus security enforcement.

    Args:
        tools: List of LangChain BaseTool instances.
        gateway: Configured SecurityGateway instance.
        agent_role: Role identifier for permission enforcement.
        caller_id: Optional calling agent identity for multi-agent enforcement.
            When set, ContextVars are set at each invoke() boundary and reset
            in a finally block (no identity leaks between calls).
        hop_depth: Delegation depth from the root supervisor (default 0 = direct).

    Returns:
        List of ArgusToolWrapper instances (drop-in replacements).
    """
    return [
        ArgusToolWrapper(
            tool=t,
            gateway=gateway,
            agent_role=agent_role,
            caller_id=caller_id,
            hop_depth=hop_depth,
        )
        for t in tools
    ]
