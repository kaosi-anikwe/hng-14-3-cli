import secrets
import rich_click as click

import requests
from requests import Request
from .settings import settings
from pydantic import SecretStr
from .conflig import Credentials
from .utils import generate_pkce, capture_code_and_state, find_free_port


def refresh_access() -> bool:
    from .client import raise_for_status

    creds = Credentials.load()
    if creds is None:
        return False
    try:
        refresh_token = creds.refresh_token.get_secret_value()
        refresh_url = f"{settings.BACKEND_URL}/auth/refresh"
        refresh_response = requests.post(
            url=refresh_url, json={"refresh_token": refresh_token}
        )
        raise_for_status(refresh_response)

        response_data = refresh_response.json()
        creds.access_token = SecretStr(str(response_data.get("access_token")))
        creds.refresh_token = SecretStr(str(response_data.get("refresh_token")))
        creds.save()
        return True
    except Exception as e:
        click.echo(f"Failed to refresh access: {e}")
        return False


@click.command()
def login():
    """Authenticate with GitHub OAuth"""
    try:
        from .client import raise_for_status

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
            login_url = f"{settings.BACKEND_URL}/auth/cli/callback"
            login_payload = {"code": code, "code_verifier": code_verifier}
            login_response = requests.post(url=login_url, json=login_payload)
            raise_for_status(login_response)
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
    from .client import raise_for_status

    """Logout and delete credentials."""
    from .conflig import CREDENTIALS_PATH

    creds = Credentials.load()
    if creds is None:
        raise click.ClickException("Not logged in.")

    # Attempt to invalidate tokens server-side; proceed with local cleanup regardless
    try:
        response = requests.post(
            url=f"{settings.BACKEND_URL}/auth/logout",
            cookies={"access_token_cookie": creds.access_token.get_secret_value()},
        )
        raise_for_status(response)
    except Exception as e:
        click.echo(
            f"Warning: server-side logout failed ({e}). Clearing local credentials anyway."
        )

    CREDENTIALS_PATH.unlink(missing_ok=True)
    click.echo("Logged out.")


@click.command()
def whoami():
    """Shows the current authenticated user."""
    creds = Credentials.load()
    if creds is None:
        raise click.ClickException("Not logged in. Run `insighta login` first.")

    click.echo(f"Currently logged in as @{creds.username}")
