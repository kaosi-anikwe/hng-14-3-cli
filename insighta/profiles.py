import click

from .conflig import Credentials


@click.command()
@click.pass_context
def list(ctx: click.Context):
    """Query profiles with optional filters"""
    creds: Credentials | None = ctx.obj["creds"]
    if not creds:
        raise click.ClickException("Not logged in. Run `insighta login` first.")


@click.command()
@click.argument("id")
def get():
    """Get a specific profile by ID"""
    pass


@click.command()
@click.argument("query")
def search():
    """Search for profiles with natrual language"""
    pass


@click.command()
@click.option("--name", help="Name to query and create profile")
def create():
    """Create profile with specified name"""
    pass


@click.command()
def export():
    """Export filtered profiles to file"""
    pass
