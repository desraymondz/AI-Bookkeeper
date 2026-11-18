"""T-230. See planning/01-prd.md#f-031-self-host-setup."""

from pathlib import Path

from pydantic_core import PydanticUndefined

from bookkeeper.config import Settings

README = Path(__file__).resolve().parents[3] / "README.md"


def test_t230_readme_covers_every_required_variable() -> None:
    text = README.read_text()
    required = [
        name.upper()
        for name, field in Settings.model_fields.items()
        if field.default is PydanticUndefined and field.default_factory is None
    ]
    assert "TELEGRAM_BOT_TOKEN" in required
    missing = [name for name in required if f"`{name}`" not in text]
    assert missing == []
    for step in ("@BotFather", "console.cloud.google.com", "aistudio.google.com", "ngrok"):
        assert step in text
