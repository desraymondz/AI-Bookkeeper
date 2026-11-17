import pytest

from bookkeeper.cli import COMMANDS, main
from bookkeeper.config import REQUIRED_ENV_VARS, ConfigError, Settings, load_settings
from tests.env import DUMMY_ENV


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key, value in DUMMY_ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


@pytest.mark.parametrize("missing", REQUIRED_ENV_VARS)
def test_missing_required_var_is_named(env: pytest.MonkeyPatch, missing: str) -> None:
    env.delenv(missing)

    with pytest.raises(ConfigError) as err:
        load_settings(_env_file=None)

    assert missing in str(err.value)


def test_all_missing_vars_listed_together(env: pytest.MonkeyPatch) -> None:
    env.delenv("BOSS_EMAIL")
    env.delenv("SESSION_SECRET")

    with pytest.raises(ConfigError) as err:
        load_settings(_env_file=None)

    assert "BOSS_EMAIL" in str(err.value)
    assert "SESSION_SECRET" in str(err.value)


def test_loads_with_required_vars(env: pytest.MonkeyPatch) -> None:
    settings = load_settings(_env_file=None)

    assert isinstance(settings, Settings)
    assert settings.boss_email == "boss@example.com"
    assert settings.gemini_model_extract_escalate == ""


def test_model_ids_come_from_env(env: pytest.MonkeyPatch) -> None:
    env.setenv("GEMINI_MODEL_EXTRACT", "some-other-model")

    assert load_settings(_env_file=None).gemini_model_extract == "some-other-model"


@pytest.mark.parametrize("app_env", ["dev", "production"])
def test_test_login_refused_outside_test_env(env: pytest.MonkeyPatch, app_env: str) -> None:
    env.setenv("APP_ENV", app_env)
    env.setenv("E2E_TEST_LOGIN", "1")

    with pytest.raises(ConfigError) as err:
        load_settings(_env_file=None)

    assert "E2E_TEST_LOGIN" in str(err.value)


def test_cli_has_every_subcommand() -> None:
    assert set(COMMANDS) == {"seed", "eval", "set-webhook", "webhook-info", "check-env"}


def test_cli_check_env(env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    env.chdir("/")
    assert main(["check-env"]) == 0

    env.delenv("BOSS_EMAIL")
    assert main(["check-env"]) == 1
    assert "BOSS_EMAIL" in capsys.readouterr().err
