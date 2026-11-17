"""See planning/decisions.md#D-016."""

import pytest

from bookkeeper.agents.gemini import ModelNotConfiguredError, UnknownTaskError, model_for_task
from bookkeeper.config import load_settings


def test_model_comes_from_env_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL_EXTRACT", "env-chosen-model")
    assert model_for_task(load_settings(_env_file=None), "extract") == "env-chosen-model"


def test_unknown_task_and_disabled_escalation() -> None:
    settings = load_settings(_env_file=None)
    with pytest.raises(UnknownTaskError):
        model_for_task(settings, "nope")
    with pytest.raises(ModelNotConfiguredError):
        model_for_task(settings, "extract_escalate")
