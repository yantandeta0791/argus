"""FastMCP server adapter for Argus security enforcement.

This module provides ``wrap_mcp_server`` — a single-call API that attaches
Argus security middleware to any FastMCP server instance.  The middleware
class ``ArgusMCPMiddleware`` intercepts every ``call_tool`` request:

* **Pre-call gate** — ``gateway.pre_tool_call`` runs *before* the real tool
  executes.  Any ``ArgusSecurityError`` raised here is converted to
  ``ToolError`` and the underlying tool is **never invoked** (fail-closed).
* **Post-call gate** — ``gateway.post_tool_call`` runs on the tool's text
  output before it is returned to the caller.  Injection / egress violations
  raise ``ToolError`` after the tool has already run.

Lazy-import rationale
---------------------
``fastmcp`` and ``mcp`` are optional extras (``pip install argus[mcp]``).
Importing this module on a system without those packages must *not* raise
``ImportError``.  All references to fastmcp/mcp symbols are therefore placed
inside method bodies where they execute only when the adapter is actually
used.
"""

from __future__ import annotations

from typing import Any

from argus.security.gateway import SecurityGateway


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


def _extract_text(result: Any) -> str:
    """Extract all text content items from a CallToolResult and join them."""
    parts = []
    for item in getattr(result, "content", []):
        if getattr(item, "type", None) == "text":
            parts.append(getattr(item, "text", ""))
    return "\n".join(parts)


def _replace_text(result: Any, clean_text: str) -> Any:
    """Replace the first text content item with *clean_text*, preserving others.

    Works with both real Pydantic ``CallToolResult`` (uses ``model_copy``) and
    plain stub/non-Pydantic objects used in tests (direct attribute assignment).
    """
    from mcp.types import TextContent  # type: ignore[import]  # lazy

    new_content: list = []
    first_text = True
    for item in getattr(result, "content", []):
        if getattr(item, "type", None) == "text":
            if first_text:
                new_content.append(TextContent(type="text", text=clean_text))
                first_text = False
            # subsequent text items are dropped (replaced by the single cleaned item)
        else:
            new_content.append(item)

    try:
        return result.model_copy(update={"content": new_content})
    except AttributeError:
        # Stub / non-Pydantic result used in tests
        result.content = new_content
        return result


# ---------------------------------------------------------------------------
# Middleware class
# ---------------------------------------------------------------------------


class ArgusMCPMiddleware:
    """FastMCP middleware that enforces Argus security gates on every tool call.

    Instantiated with a :class:`~argus.security.gateway.SecurityGateway` and
    an *agent_role* string.  The instance is passed to
    ``server.add_middleware()`` by :func:`wrap_mcp_server`.

    The class body deliberately does *not* inherit from
    ``fastmcp.server.middleware.Middleware`` at definition time so that the
    module can be imported without fastmcp installed.  FastMCP's
    ``add_middleware`` duck-types its argument — it only requires the
    ``on_call_tool`` coroutine method to be present.
    """

    def __init__(self, gateway: SecurityGateway, agent_role: str = "default") -> None:
        self._gateway = gateway
        self._agent_role = agent_role

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        """Intercept a tool call, apply security gates, return (possibly cleaned) result."""
        from fastmcp.exceptions import ToolError  # type: ignore[import]  # lazy
        from argus.security.exceptions import ArgusSecurityError

        tool_name: str = context.message.name
        tool_input: dict = context.message.arguments or {}

        # Pre-call gate — tool must NOT be invoked if this raises
        try:
            self._gateway.pre_tool_call(self._agent_role, tool_name, tool_input)
        except ArgusSecurityError as exc:
            raise ToolError(str(exc)) from exc

        result = await call_next(context)

        output_str = _extract_text(result)

        # Post-call gate — filter / block dangerous output
        try:
            clean = self._gateway.post_tool_call(output_str)
        except ArgusSecurityError as exc:
            raise ToolError(str(exc)) from exc

        return _replace_text(result, clean)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def wrap_mcp_server(
    server: Any,
    gateway: SecurityGateway,
    agent_role: str = "default",
) -> Any:
    """Attach Argus security middleware to *server* and return it.

    Args:
        server: Any FastMCP ``Server`` instance (or duck-typed equivalent).
        gateway: The :class:`~argus.security.gateway.SecurityGateway` that
            provides ``pre_tool_call`` and ``post_tool_call`` hooks.
        agent_role: The role string passed to gateway calls (default
            ``"default"``).

    Returns:
        The same *server* object with ``ArgusMCPMiddleware`` attached.
    """
    middleware = ArgusMCPMiddleware(gateway=gateway, agent_role=agent_role)
    server.add_middleware(middleware)
    return server
