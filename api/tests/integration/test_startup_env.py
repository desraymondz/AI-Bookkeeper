import os
import subprocess
import sys
from pathlib import Path

import pytest

from bookkeeper.config import ALL_ENV_VARS, REQUIRED_ENV_VARS
from tests.env import DUMMY_ENV

pytestmark = pytest.mark.integration

START_TIMEOUT_SECONDS = 60


def _clean_env(missing: str | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ALL_ENV_VARS}
    env.update(DUMMY_ENV)
    if missing is not None:
        env.pop(missing, None)
    return env


def _start_app(env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "bookkeeper.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
        ],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=START_TIMEOUT_SECONDS,
        check=False,
    )


def test_required_list_contains_boss_email() -> None:
    assert "BOSS_EMAIL" in REQUIRED_ENV_VARS
    assert set(REQUIRED_ENV_VARS) <= set(DUMMY_ENV)


@pytest.mark.parametrize(
    "missing",
    ["BOSS_EMAIL", *[v for v in REQUIRED_ENV_VARS if v != "BOSS_EMAIL"]],
)
def test_t232_app_exits_non_zero_naming_missing_var(missing: str, tmp_path: Path) -> None:
    result = _start_app(_clean_env(missing), tmp_path)

    assert result.returncode != 0
    assert missing in result.stderr


@pytest.mark.parametrize("missing", ["BOSS_EMAIL", "DATABASE_URL"])
def test_t232_empty_value_counts_as_missing(missing: str, tmp_path: Path) -> None:
    env = _clean_env()
    env[missing] = ""

    result = _start_app(env, tmp_path)

    assert result.returncode != 0
    assert missing in result.stderr


def test_t232_app_imports_when_all_required_vars_set(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import bookkeeper.main"],
        env=_clean_env(),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=START_TIMEOUT_SECONDS,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_t232_check_env_command_names_missing_var(tmp_path: Path) -> None:
    bk = Path(sys.executable).with_name("bk")
    missing = subprocess.run(
        [str(bk), "check-env"],
        env=_clean_env("BOSS_EMAIL"),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=START_TIMEOUT_SECONDS,
        check=False,
    )
    ok = subprocess.run(
        [str(bk), "check-env"],
        env=_clean_env(),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=START_TIMEOUT_SECONDS,
        check=False,
    )

    assert missing.returncode != 0
    assert "BOSS_EMAIL" in missing.stderr
    assert ok.returncode == 0, ok.stderr
