"""Message templates. See planning/01-prd.md#g-5 and AGENTS.md (replies and acks are templates)."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=False,
)


def render(name: str, **context: Any) -> str:
    return _env.get_template(f"{name}.txt.j2").render(**context).strip()
