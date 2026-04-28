import click


@click.command()
def login():
    """Authenticate with GitHub OAuth"""
    pass


@click.command()
def logout():
    """Logout and delete credentials"""
    pass


@click.command()
def whoami():
    """Shows the current authenticated user"""
    pass
