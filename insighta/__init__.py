import logging

import rich_click as click

from . import auth
from . import profiles as profile_commands
from .settings import settings

if settings.INSIGHTA_DEVELOPMENT:
    from rich.logging import RichHandler

    logging.basicConfig(
        level="DEBUG",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
else:
    logging.disable(logging.CRITICAL)


@click.group()
@click.version_option()
def cli():
    """Insighta CLI."""
    pass


cli.add_command(auth.login)
cli.add_command(auth.logout)
cli.add_command(auth.whoami)


@cli.group()
def profiles():
    """Commands for managing profiles (auth required)"""
    pass


profiles.add_command(profile_commands.list)
profiles.add_command(profile_commands.get)
profiles.add_command(profile_commands.search)
profiles.add_command(profile_commands.create)
profiles.add_command(profile_commands.export)
