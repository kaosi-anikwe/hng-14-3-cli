import requests
import rich_click as click

from .auth import refresh_access
from .conflig import Credentials


def raise_for_status(response: requests.Response) -> None:
    """Like response.raise_for_status() but surfaces the backend's error message."""
    try:
        response.raise_for_status()
    except requests.HTTPError:
        message = None
        try:
            message = response.json().get("message")
        except Exception:
            pass
        raise click.ClickException(message or f"HTTP {response.status_code}")


def authed_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make an authenticated HTTP request using cookie-based JWT auth.
    Automatically attempts a token refresh once on 401 before failing.
    """
    creds = Credentials.load()
    if creds is None:
        raise click.ClickException("Not logged in. Run `insighta login` first.")

    cookies = {"access_token_cookie": creds.access_token.get_secret_value()}
    headers = {"X-API-Version": "1"}
    response = requests.request(method, url, cookies=cookies, headers=headers, **kwargs)

    if response.status_code == 401:
        if refresh_access():
            creds = Credentials.load()
            if creds is None:
                raise click.ClickException("Session expired. Please log in again.")
            cookies = {"access_token_cookie": creds.access_token.get_secret_value()}
            response = requests.request(
                method, url, cookies=cookies, headers=headers, **kwargs
            )
        else:
            raise click.ClickException("Session expired. Please log in again.")

    return response
