"""
Public API surface for argus.engine.

Re-exports the 6 symbols that Phase 3 and downstream consumers use via
`from argus.engine import ...`. Implementation details live in sub-modules;
only these names are the public contract.

Phase 3 injects the real LLM callable into StateMachine at construction time.
Phase 4 injects memory read/write hooks as additional optional handler parameters.
"""

from argus.engine.states import TaskState, RunContext, RunResult, LLMCallable
from argus.engine.machine import StateMachine
from argus.engine.tools import ToolManifest, ToolRunner

__all__ = [
    "TaskState",
    "RunContext",
    "RunResult",
    "LLMCallable",
    "StateMachine",
    "ToolManifest",
    "ToolRunner",
]
