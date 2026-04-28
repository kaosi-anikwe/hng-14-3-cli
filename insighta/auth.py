import click
import secrets

import requests
from requests import Request
from .settings import settings
from pydantic import SecretStr
from .conflig import Credentials
from .utils import generate_pkce, capture_code_and_state, find_free_port


@click.command()
def login():
    """Authenticate with GitHub OAuth"""
    try:
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = generate_pkce()

        temp_server_host = "127.0.0.1"
        temp_server_port = find_free_port()
        temp_server = (temp_server_host, temp_server_port)

        url = "https://github.com/login/oauth/authorize"
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": f"http://{temp_server_host}:{temp_server_port}/auth/github/callback",
            "scope": "user:email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        req = Request("GET", url=url, params=params)
        prepared = req.prepare()
        auth_url = str(prepared.url)
        click.echo(auth_url)
        code, captured_state = capture_code_and_state(temp_server, auth_url)

        if state == captured_state:
            # Proceed with login
            click.echo("Loggin in...")
            login_url = f"{settings.BACKENC_URL}/auth/cli/callback"
            login_payload = {"code": code, "code_verifier": code_verifier}
            login_response = requests.post(url=login_url, json=login_payload)
            login_response.raise_for_status()
            response_data: dict[str, str] = login_response.json()

            access_token = response_data.get("access_token")
            refresh_token = response_data.get("refresh_token")
            username = response_data.get("username")

            creds = Credentials(
                username=str(username),
                access_token=SecretStr(str(access_token)),
                refresh_token=SecretStr(str(refresh_token)),
            )
            creds.save()
            click.echo(f"Logged in as {creds.username}")
        else:
            raise click.ClickException(f"Invalid CSRF, aborting...")
    except click.ClickException:
        raise
    except KeyboardInterrupt:
        click.echo("\nLogin cancelled.")
    except OSError as e:
        raise click.ClickException(f"Network error: {e}") from e
    except Exception as e:
        raise click.ClickException(f"Login failed: {e}") from e


@click.command()
def logout():
    """Logout and delete credentials"""
    pass


@click.command()
@click.pass_context
def whoami(ctx: click.Context):
    """Shows the current authenticated user"""
    creds: Credentials | None = ctx.obj["creds"]
    if creds is None:
        raise click.ClickException("Not logged in. Run `insighta login` first.")

    click.echo(f"Currently logged in as @{creds.username}")
