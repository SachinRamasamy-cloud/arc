"""Migration operations available before the feature APIs are published."""
import argparse
from importlib import import_module
from pathlib import Path

from alembic import command
from alembic.config import Config

import database as database_package


def migration_config():
    database_path = Path(database_package.__file__).resolve().parent
    config = Config()
    config.set_main_option("path_separator", "os")
    config.set_main_option("script_location", str(database_path))
    config.set_main_option("version_locations", str(database_path / "migrations/versions"))
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Arc backend foundation operations")
    parser.add_argument("command", choices=["migrate", "migration-status"])
    args = parser.parse_args(argv)
    config = migration_config()
    if args.command == "migrate":
        command.upgrade(config, "head")
    else:
        command.current(config)


def platform_main():
    """Preserve the full local CLI when later feature entrypoints are installed."""
    try:
        feature_cli = import_module("entrypoints.cli.main")
    except ModuleNotFoundError as error:
        if error.name not in {"entrypoints.cli", "entrypoints.cli.main"}:
            raise
        return main()
    return feature_cli.main()


if __name__ == "__main__":
    main()
