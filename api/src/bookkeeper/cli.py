"""See planning/03-tech-stack.md#101-api-run-in-api."""

import argparse
import sys
from collections.abc import Callable, Sequence

from bookkeeper.config import ConfigError, load_settings


def _check_env(_: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Environment OK (APP_ENV={settings.app_env}).")
    return 0


def _not_implemented(name: str) -> Callable[[argparse.Namespace], int]:
    def run(_: argparse.Namespace) -> int:
        print(f"bk {name}: not implemented yet.", file=sys.stderr)
        return 2

    return run


COMMANDS: dict[str, tuple[str, Callable[[argparse.Namespace], int]]] = {
    "seed": ("Seed the demo cafe", _not_implemented("seed")),
    "eval": ("Run the eval harness", _not_implemented("eval")),
    "set-webhook": ("Register the Telegram webhook", _not_implemented("set-webhook")),
    "webhook-info": ("Show Telegram webhook status", _not_implemented("webhook-info")),
    "check-env": ("Check required environment variables", _check_env),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bk", description="AI Bookkeeper command line")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (help_text, handler) in COMMANDS.items():
        cmd = sub.add_parser(name, help=help_text)
        cmd.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
