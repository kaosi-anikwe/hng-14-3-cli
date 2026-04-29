import base64
import hashlib
import secrets
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse

import rich_click as click


class OAuthCallbackServer(HTTPServer):
    code: str | None = None
    state: str | None = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    CALLBACK_PATH = "/auth/github/callback"

    def log_message(self, format, *args):
        pass  # Suppress default request logging

    def do_GET(self):
        parsed = parse.urlparse(self.path)

        # Ignore requests to other paths (e.g. favicon.ico)
        if parsed.path != self.CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        # 1. Send a friendly response to the browser
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        # TODO: add proper HTML file with styling after building web ui
        self.wfile.write(
            b"<h1>Success!</h1><p>You can close this tab and return to the terminal.</p>"
        )

        # 2. Parse the authorization code from the URL
        params = parse.parse_qs(parsed.query)

        if "code" in params and "state" in params:
            # Store the code on the server object for the main thread to access
            assert isinstance(self.server, OAuthCallbackServer)
            self.server.code = params["code"][0]
            self.server.state = params["state"][0]


def capture_code_and_state(
    server_address: tuple[str, int], auth_url: str
) -> tuple[str, str]:
    # Setup server
    httpd = OAuthCallbackServer(server_address, OAuthCallbackHandler)

    # Open the user's browser to the OAuth provider
    click.echo("Opening browser for authorization...")
    webbrowser.open(auth_url)

    # Wait for redirect
    httpd.timeout = 120  # seconds
    httpd.handle_request()

    if httpd.code is None:
        raise click.ClickException("Login timed out. Please try again.")

    if httpd.state is None:
        raise click.ClickException("Invalid request. `state` param missing.")

    # Return captured code and state
    return httpd.code, httpd.state


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def generate_pkce():
    verifier = secrets.token_urlsafe(64)
    sha256_hash = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")
    return verifier, challenge
