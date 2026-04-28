import click

from . import auth
from .conflig import Credentials
from . import profiles as profile_commands


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx: click.Context):
    """Insighta CLI."""
    ctx.ensure_object(dict)
    ctx.obj["creds"] = Credentials.load()


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
