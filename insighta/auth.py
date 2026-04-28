import secrets
import rich_click as click

import requests
from rich.text import Text
from requests import Request
from rich.panel import Panel
from pydantic import SecretStr
from rich.console import Console

from .settings import settings
from .conflig import Credentials
from .utils import generate_pkce, capture_code_and_state, find_free_port


def refresh_access() -> bool:
    from .client import raise_for_status

    creds = Credentials.load()
    if creds is None:
        return False
    try:
        refresh_token = creds.refresh_token.get_secret_value()
        refresh_url = f"{settings.INSIGHTA_BACKEND_URL}/auth/refresh"
        refresh_response = requests.post(
            url=refresh_url, json={"refresh_token": refresh_token}
        )
        raise_for_status(refresh_response)

        response_data = refresh_response.json()
        creds.access_token = SecretStr(str(response_data.get("access_token")))
        creds.refresh_token = SecretStr(str(response_data.get("refresh_token")))
        creds.save()
        return True
    except:
        return False


@click.command()
def login():
    """Authenticate with GitHub OAuth."""
    try:
        from .client import raise_for_status

        console = Console()
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = generate_pkce()

        temp_server_host = "127.0.0.1"
        temp_server_port = find_free_port()
        temp_server = (temp_server_host, temp_server_port)

        url = "https://github.com/login/oauth/authorize"
        params = {
            "client_id": settings.INSIGHTA_GITHUB_CLIENT_ID,
            "redirect_uri": f"http://{temp_server_host}:{temp_server_port}/auth/github/callback",
            "scope": "user:email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        req = Request("GET", url=url, params=params)
        prepared = req.prepare()
        auth_url = str(prepared.url)
        code, captured_state = capture_code_and_state(temp_server, auth_url)

        if state == captured_state:
            with console.status("Logging in..."):
                login_url = f"{settings.INSIGHTA_BACKEND_URL}/auth/cli/callback"
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

            console.print(
                f"[bold green]✓[/bold green] Logged in as [bold cyan]@{creds.username}[/bold cyan]"
            )
        else:
            raise click.ClickException("Invalid CSRF, aborting...")
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
    """Logout and delete credentials."""
    from .client import raise_for_status
    from .conflig import CREDENTIALS_PATH

    console = Console()
    creds = Credentials.load()
    if creds is None:
        raise click.ClickException("Not logged in.")

    # Attempt to invalidate tokens server-side; proceed with local cleanup regardless
    try:
        with console.status("Logging out..."):
            response = requests.post(
                url=f"{settings.INSIGHTA_BACKEND_URL}/auth/logout",
                cookies={"access_token_cookie": creds.access_token.get_secret_value()},
            )
            raise_for_status(response)
    except Exception as e:
        console.print(
            f"[yellow]Warning:[/yellow] server-side logout failed ({e}). Clearing local credentials anyway."
        )

    CREDENTIALS_PATH.unlink(missing_ok=True)
    console.print("[bold green]✓[/bold green] Logged out.")


@click.command()
def whoami():
    """Shows the current authenticated user."""
    console = Console()
    creds = Credentials.load()
    if creds is None:
        raise click.ClickException("Not logged in. Run `insighta login` first.")

    summary = Text()
    summary.append("  Username  ", style="dim")
    summary.append(f"@{creds.username}", style="bold cyan")

    console.print(Panel(summary, title="[bold]Current User[/bold]", expand=False))
