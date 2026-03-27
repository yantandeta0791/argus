import os
import tempfile

import casbin

from argus.security.exceptions import PermissionDeniedError
from argus.security.permission.policy import PolicyConfig

# Casbin RBAC model definition (in-memory string, no model file needed)
RBAC_MODEL = """
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
"""


class PermissionEnforcer:
    """Casbin RBAC enforcer for tool-level permission checks.

    Accepts a PolicyConfig or a dict (which is coerced to PolicyConfig).
    If config is None or empty, operates in permissive mode (all calls allowed).

    Note: Uses synchronous casbin.Enforcer for Plan 03. Phase 2 will migrate
    to casbin.AsyncEnforcer when the full async state machine is built.
    """

    def __init__(self, policy_config) -> None:
        # Accept both dict and PolicyConfig for convenience
        if isinstance(policy_config, dict):
            policy_config = PolicyConfig(**policy_config)

        if policy_config is None or policy_config.is_empty():
            self._permissive = True
            self._enforcer = None
            self._wildcard_roles: set[str] = set()
            self._deny_rules: set[tuple[str, str]] = set()
            return

        self._permissive = False

        # Build wildcard allow set (tool="*") and deny set — both handled pre-Casbin
        self._wildcard_roles = {
            rule.role
            for rule in policy_config.rules
            if rule.tool == "*" and rule.effect == "allow"
        }
        self._deny_rules = {
            (rule.role, rule.tool)
            for rule in policy_config.rules
            if rule.effect == "deny"
        }

        # Only pass allow rules with specific tools (not wildcards) to Casbin
        casbin_rules = [
            rule
            for rule in policy_config.rules
            if rule.effect == "allow" and rule.tool != "*"
        ]

        if casbin_rules:
            csv_lines = [f"p, {rule.role}, {rule.tool}, call" for rule in casbin_rules]
            csv_text = "\n".join(csv_lines)

            # Write policy to a temp file — StringAdapter is not in pycasbin 1.43.0 public API
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".csv", delete=False
                ) as tmp_file:
                    tmp_file.write(csv_text)
                    tmp_path = tmp_file.name

                model = casbin.Model()
                model.load_model_from_text(RBAC_MODEL)
                adapter = casbin.FileAdapter(tmp_path)
                self._enforcer = casbin.Enforcer(model, adapter)
            finally:
                if tmp_path is not None and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            # No Casbin rules — deny/wildcard checks in enforce() handle everything
            self._enforcer = None

    def enforce(self, role: str, tool_name: str) -> None:
        """Check if role may call tool_name.

        Returns None if allowed. Raises PermissionDeniedError if denied.

        Evaluation order:
          1. Permissive mode — allow all.
          2. Deny rules — explicit deny overrides everything (checked first).
          3. Wildcard allow — role has tool="*" allow rule.
          4. Casbin — check specific allow rules.
          5. No Casbin enforcer + no wildcard — deny.
        """
        if self._permissive:
            return

        # 1. Explicit deny always wins (checked before wildcard allow)
        if (role, tool_name) in self._deny_rules:
            raise PermissionDeniedError(
                gate="permission",
                blocked=tool_name,
                rule=f"role={role} tool={tool_name} effect=deny",
            )

        # 2. Wildcard allow — this role can call any tool
        if role in self._wildcard_roles:
            return

        # 3. Casbin enforcer for specific tool rules
        if self._enforcer is not None:
            allowed = self._enforcer.enforce(role, tool_name, "call")
            if not allowed:
                raise PermissionDeniedError(
                    gate="permission",
                    blocked=tool_name,
                    rule=f"role={role} tool={tool_name}",
                )
        else:
            # No Casbin enforcer and no wildcard — deny
            raise PermissionDeniedError(
                gate="permission",
                blocked=tool_name,
                rule=f"role={role} tool={tool_name}",
            )
