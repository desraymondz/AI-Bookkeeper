"""See planning/03-tech-stack.md#101-api-run-in-api."""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from bookkeeper.config import ConfigError, load_settings


def _check_env(_: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Environment OK (APP_ENV={settings.app_env}).")
    return 0


async def _seed_async() -> int:
    from eval.seed.runner import SeedRefusedError, seed_demo_cafe

    from bookkeeper.config import load_database_settings
    from bookkeeper.db.session import create_engine, create_sessionmaker

    engine = create_engine(load_database_settings().database_url)
    try:
        async with create_sessionmaker(engine)() as session:
            try:
                summary = await seed_demo_cafe(session)
            except SeedRefusedError as exc:
                await session.rollback()
                print(exc, file=sys.stderr)
                return 1
            await session.commit()
    finally:
        await engine.dispose()
    print(
        f"Seeded demo cafe: {summary.suppliers} suppliers, {summary.invoices} invoices, "
        f"{summary.sales_days} sales days, {summary.payments} payments, "
        f"{summary.entries} journal entries."
    )
    return 0


def _seed(_: argparse.Namespace) -> int:
    api_dir = str(Path(__file__).resolve().parents[2])
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    try:
        return asyncio.run(_seed_async())
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1


def _not_implemented(name: str) -> Callable[[argparse.Namespace], int]:
    def run(_: argparse.Namespace) -> int:
        print(f"bk {name}: not implemented yet.", file=sys.stderr)
        return 2

    return run


COMMANDS: dict[str, tuple[str, Callable[[argparse.Namespace], int]]] = {
    "seed": ("Seed the demo cafe", _seed),
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
