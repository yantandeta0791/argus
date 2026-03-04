from pydantic import BaseModel
from typing import Literal


class PolicyRule(BaseModel):
    role: str
    tool: str
    effect: Literal["allow", "deny"] = "allow"


class PolicyConfig(BaseModel):
    rules: list[PolicyRule] = []

    def is_empty(self) -> bool:
        return len(self.rules) == 0

    def to_casbin_csv(self) -> str:
        """Convert to Casbin policy CSV format: p, role, tool, call"""
        lines = []
        for rule in self.rules:
            if rule.effect == "allow":
                lines.append(f"p, {rule.role}, {rule.tool}, call")
        return "\n".join(lines)
