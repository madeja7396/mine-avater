from __future__ import annotations

import re
from pathlib import Path


SKILLS_ROOT = Path("skills")
AGENTS_FILE = Path("AGENTS.md")
REQUIRED_SKILLS = [
    "avatar-development-orchestrator",
    "avatar-ci-guardian",
    "avatar-spec-steward",
]
REQUIRED_AGENTS_TOKENS = [
    "### Available skills",
    "### Routing rules (mandatory)",
    "### Operational guardrails",
    "make check",
    "make test_fast",
    "make test_unit",
    "make test_full",
    "harness/task_lock.py",
]


def parse_frontmatter(skill_md: Path) -> dict[str, str] | None:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return None
    body = match.group(1)
    data: dict[str, str] = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_openai_yaml(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    data: dict[str, str] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        raw = line.strip()
        key, value = raw.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def validate_skill(skill_name: str) -> list[str]:
    errors: list[str] = []
    skill_dir = SKILLS_ROOT / skill_name
    skill_md = skill_dir / "SKILL.md"
    openai_yaml = skill_dir / "agents/openai.yaml"

    if not skill_md.is_file():
        return [f"ERROR: missing {skill_md}"]
    if not openai_yaml.is_file():
        return [f"ERROR: missing {openai_yaml}"]

    frontmatter = parse_frontmatter(skill_md)
    if not frontmatter:
        errors.append(f"ERROR: invalid frontmatter {skill_md}")
        return errors

    if frontmatter.get("name") != skill_name:
        errors.append(
            f"ERROR: skill_name_mismatch file={skill_md} "
            f"expected={skill_name} got={frontmatter.get('name')}"
        )
    description = frontmatter.get("description", "")
    if not description or "[TODO" in description:
        errors.append(f"ERROR: incomplete_description file={skill_md}")

    interface = parse_openai_yaml(openai_yaml)
    display_name = interface.get("display_name", "")
    short_description = interface.get("short_description", "")
    default_prompt = interface.get("default_prompt", "")
    if not display_name:
        errors.append(f"ERROR: missing_display_name file={openai_yaml}")
    if not (25 <= len(short_description) <= 64):
        errors.append(
            f"ERROR: invalid_short_description_length file={openai_yaml} "
            f"length={len(short_description)}"
        )
    if not default_prompt:
        errors.append(f"ERROR: missing_default_prompt file={openai_yaml}")

    for script in (skill_dir / "scripts").glob("*"):
        if script.is_file() and not script.stat().st_mode & 0o111:
            errors.append(f"ERROR: non_executable_script file={script}")

    return errors


def main() -> int:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir():
        print("ERROR: missing skills directory")
        return 1
    if not AGENTS_FILE.is_file():
        print(f"ERROR: missing {AGENTS_FILE}")
        return 1

    agents_text = AGENTS_FILE.read_text(encoding="utf-8")

    for skill_name in REQUIRED_SKILLS:
        errors.extend(validate_skill(skill_name))
        expected_path = f"skills/{skill_name}/SKILL.md"
        if skill_name not in agents_text:
            errors.append(f"ERROR: agents_missing_skill_name skill={skill_name}")
        if expected_path not in agents_text:
            errors.append(f"ERROR: agents_missing_skill_path path={expected_path}")

    for token in REQUIRED_AGENTS_TOKENS:
        if token not in agents_text:
            errors.append(f"ERROR: agents_missing_token token={token}")

    if errors:
        print(f"ERROR: project_skills_invalid failures={len(errors)}")
        for error in errors:
            print(error)
        return 1

    print(f"METRIC: project_skills_valid count={len(REQUIRED_SKILLS)} failures=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
