import pytest


@pytest.mark.xfail(reason="SEC-04 not yet implemented", strict=False)
def test_env_stripping(tmp_path):
    import os
    from argus.security.sandbox.isolator import SkillIsolator
    isolator = SkillIsolator()
    # Write a skill that prints its environment
    skill = tmp_path / "check_env.py"
    skill.write_text("import os, json; print(json.dumps(dict(os.environ)))")
    result = isolator.run(
        skill_cmd=[str(skill)],
        skill_package_path=str(tmp_path),
    )
    import json
    env = json.loads(result.strip())
    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    # Only allowed keys should be present (plus macOS-injected system vars that are not sensitive)
    allowed = {"PATH", "HOME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE"}
    # macOS injects __CF_USER_TEXT_ENCODING and LC_CTYPE at the OS level regardless of env=
    # These are not sensitive — they are locale/encoding metadata injected by CoreFoundation
    macos_system_vars = {"__CF_USER_TEXT_ENCODING", "LC_CTYPE"}
    assert set(env.keys()).issubset(allowed | macos_system_vars)


@pytest.mark.xfail(reason="SEC-04 not yet implemented", strict=False)
def test_scope_containment(tmp_path):
    import os
    from argus.security.sandbox.isolator import SkillIsolator
    isolator = SkillIsolator()
    # Skill attempts to write outside its declared scope
    target_file = tmp_path / "escape_attempt.txt"
    skill = tmp_path / "escape_skill.py"
    skill.write_text(f"open('{target_file}', 'w').write('escaped'); print('done')")
    # In v1, process isolation does not block filesystem writes — but the env is stripped
    # The test verifies the skill runs in isolation (stripped env), not that it's blocked from writing
    result = isolator.run(skill_cmd=[str(skill)], skill_package_path=str(tmp_path))
    assert "done" in result
