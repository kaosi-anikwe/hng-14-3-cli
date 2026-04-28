import click


@click.command()
def list():
    """Query profiles with optional filters"""
    pass


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
