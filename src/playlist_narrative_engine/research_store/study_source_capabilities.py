from __future__ import annotations

from typing import Final


MAESTRO_BETA_SOURCE_SYSTEM: Final = "Maestro Beta"
MAESTRO_BETA_MAX_PROMPT_CHARACTERS: Final = 255


def source_system_execution_capabilities() -> dict[str, dict[str, object]]:
    """Return the known, source-specific execution limits used by Study validation."""
    return {
        MAESTRO_BETA_SOURCE_SYSTEM: {
            "max_prompt_characters": MAESTRO_BETA_MAX_PROMPT_CHARACTERS,
            "character_counting": "UNICODE_CODE_POINTS",
        }
    }


def validate_planned_prompt_execution(
    source_system: str | None, prompt_text: str, *, run_key: str | None = None
) -> None:
    capability = source_system_execution_capabilities().get(source_system or "")
    if capability is None:
        return
    maximum = int(capability["max_prompt_characters"])
    actual = len(prompt_text)
    if actual > maximum:
        label = f"planned run {run_key!r} " if run_key else "planned run "
        raise ValueError(
            f"{label}prompt has {actual} characters; source system {source_system!r} "
            f"supports at most {maximum}"
        )
