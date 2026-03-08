import subprocess
import sys
from typing import Optional


class SkillIsolator:
    """
    Runs skills in a subprocess with a stripped environment.
    v1: subprocess.run — provides env isolation, NOT syscall isolation.
    v1.1 upgrade path: replace subprocess.run with Docker container run (same interface).

    CRITICAL: Always pass explicit env dict — never pass env=None (inherits parent secrets).
    """

    # Minimal allowed environment keys
    ALLOWED_ENV_KEYS = {"PATH", "HOME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE"}

    def run(
        self,
        skill_cmd: list[str],
        skill_package_path: str,
        timeout_s: float = 30.0,
        extra_env: Optional[dict] = None,
    ) -> str:
        """
        Execute a skill command in an isolated subprocess.
        Returns stdout as string.
        Raises RuntimeError on non-zero exit code.
        """
        minimal_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp",
            "PYTHONPATH": skill_package_path,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if extra_env:
            # Only allow keys from ALLOWED_ENV_KEYS to be overridden
            for k, v in extra_env.items():
                if k in self.ALLOWED_ENV_KEYS:
                    minimal_env[k] = v

        result = subprocess.run(
            [sys.executable] + skill_cmd,
            env=minimal_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if result.returncode != 0:
            # Surface stderr for debugging — do NOT expose to LLM context
            raise RuntimeError(
                f"Skill exited {result.returncode}: {result.stderr[:500]}"
            )
        return result.stdout
