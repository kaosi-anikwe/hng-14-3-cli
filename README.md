# Insighta Labs+ CLI

[![CI](https://github.com/kaosi-anikwe/hng-14-3-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kaosi-anikwe/hng-14-3-cli/actions/workflows/ci.yml)

A command-line interface for the Insighta platform — query, search, create, and export user profiles, authenticated via GitHub OAuth.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [CI/CD](#cicd)
- [Configuration](#configuration)
- [System Architecture](#system-architecture)
- [Authentication Flow](#authentication-flow)
- [Token Handling](#token-handling)
- [CLI Usage](#cli-usage)
- [Development](#development)

---

## Requirements

- Python **3.14+**
- [pipx](https://pipx.pypa.io/) — install once, available globally

---

## Installation

Install directly from the `main` branch — no cloning required:

```bash
# 1. Ensure pipx is available
python -m pip install --user pipx
python -m pipx ensurepath
# Restart your shell after this step

# 2. Install insighta
pipx install "git+https://github.com/kaosi-anikwe/hng-14-3-cli.git@main#subdirectory=."
```

The `insighta` command is then available globally in any shell:

```bash
insighta --help
```

To upgrade to the latest commit on the branch:

```bash
pipx reinstall insighta
```

To uninstall:

```bash
pipx uninstall insighta
```

---

## Configuration

Settings are loaded from environment files in this priority order (last wins):

| Location              | Purpose                       |
| --------------------- | ----------------------------- |
| `.env` (project root) | Local/development overrides   |
| `~/.insighta/.env`    | Per-user persistent overrides |

Available variables:

| Variable                    | Default                           | Description                      |
| --------------------------- | --------------------------------- | -------------------------------- |
| `INSIGHTA_BACKEND_URL`      | `https://hng-14-three.vercel.app` | Base URL of the Insighta backend |
| `INSIGHTA_GITHUB_CLIENT_ID` | _(built-in)_                      | GitHub OAuth App client ID       |
| `INSIGHTA_DEVELOPMENT`      | `false`                           | Enable debug logging via Rich    |

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   insighta CLI                      │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐     │
│  │   auth   │  │ profiles │  │    settings    │     │
│  │ login    │  │ list     │  │ (pydantic-     │     │
│  │ logout   │  │ get      │  │  settings)     │     │
│  │ whoami   │  │ search   │  └────────────────┘     │
│  └────┬─────┘  │ create   │                         │
│       │        │ export   │  ┌────────────────┐     │
│       │        └────┬─────┘  │  config.py     │     │
│       │             │        │  Credentials   │     │
│       └─────────────┤        │  ~/.insighta/  │     │
│                     │        │  credentials   │     │
│              ┌──────▼──────┐ │  .json         │     │
│              │  client.py  │ └────────────────┘     │
│              │ authed_     │                        │
│              │ request()   │                        │
│              └──────┬──────┘                        │
└─────────────────────┼───────────────────────────────┘
                      │ HTTPS
                      ▼
          ┌───────────────────────┐
          │   Insighta Backend    │
          │  /auth/cli/callback   │
          │  /auth/refresh        │
          │  /auth/logout         │
          │  /api/users/me        │
          │  /api/profiles/**     │
          └───────────────────────┘
```

**Key modules:**

| Module        | Responsibility                                                    |
| ------------- | ----------------------------------------------------------------- |
| `__init__.py` | CLI entry point; registers all command groups                     |
| `auth.py`     | `login`, `logout`, `whoami` commands; token refresh logic         |
| `profiles.py` | `list`, `get`, `search`, `create`, `export` commands              |
| `client.py`   | `authed_request()` — authenticated HTTP with auto-refresh         |
| `config.py`   | `Credentials` model; read/write `~/.insighta/credentials.json`    |
| `settings.py` | `Settings` model; loads config from environment files             |
| `utils.py`    | PKCE generation, local OAuth callback HTTP server, port discovery |

---

## Authentication Flow

Insighta uses **GitHub OAuth 2.0 with PKCE** (Proof Key for Code Exchange) to avoid needing a client secret in the CLI.

```
User                  CLI                  GitHub             Backend
 │                     │                     │                   │
 │  insighta login     │                     │                   │
 │───────────────────▶│                     │                   │
 │                     │ 1. Generate state   │                   │
 │                     │    + PKCE pair      │                   │
 │                     │    (verifier /      │                   │
 │                     │     challenge)      │                   │
 │                     │                     │                   │
 │                     │ 2. Spin up local    │                   │
 │                     │    HTTP server on   │                   │
 │                     │    random port      │                   │
 │                     │                     │                   │
 │                     │ 3. Open browser ──▶ │                   │
 │  [browser opens]    │    /login/oauth/    │                   │
 │                     │    authorize        │                   │
 │                     │                     │                   │
 │  [user authorises]  │                     │                   │
 │                     │◀── 4. Redirect to ──│                   │
 │                     │    localhost/auth/  │                   │
 │                     │    github/callback  │                   │
 │                     │    ?code=…&state=…  │                   │
 │                     │                     │                   │
 │                     │ 5. Validate state   │                   │
 │                     │    (CSRF check)     │                   │
 │                     │                     │                   │
 │                     │ 6. POST /auth/cli/callback ──────────▶  │
 │                     │    { code, code_verifier }              │
 │                     │                     │                   │
 │                     │◀───────────────────── 7. { access_token,│
 │                     │                           refresh_token, │
 │                     │                            username }   │
 │                     │                     │                   │
 │                     │ 8. Save credentials │                   │
 │                     │    to disk          │                   │
 │  ✓ Logged in        │                     │                   │
 │◀────────────────────│                     │                   │
```

**PKCE** ensures that even if the authorization `code` is intercepted in the redirect, it cannot be exchanged for tokens without the original `code_verifier` that never leaves the CLI process.

---

## Token Handling

### Storage

Tokens are stored in `~/.insighta/credentials.json` after a successful login:

```json
{
  "username": "your-github-username",
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

On POSIX systems the file permissions are set to `0600` (owner read/write only) immediately after writing. On Windows the file is restricted by default NTFS ACLs for the user profile directory.

> **Never commit `~/.insighta/credentials.json` to version control.**

### Automatic Refresh

Every API call goes through `authed_request()` in `client.py`. If the backend returns **HTTP 401**, the client transparently:

1. Calls `POST /auth/refresh` with the stored refresh token.
2. Overwrites both tokens in `credentials.json`.
3. Retries the original request with the new access token.

If the refresh itself fails (expired or revoked refresh token), the command exits with:

```
Error: Session expired. Please log in again.
```

### Logout

`insighta logout` attempts to invalidate the session server-side (`POST /auth/logout`), then unconditionally deletes `~/.insighta/credentials.json` regardless of whether the server call succeeded.

---

## CLI Usage

### Top-level

```
insighta [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  login     Authenticate with GitHub OAuth.
  logout    Logout and delete credentials.
  whoami    Show the current authenticated user.
  profiles  Commands for managing profiles (auth required).
```

---

### `insighta login`

Opens a browser window to complete GitHub OAuth. On success, credentials are saved locally.

```bash
insighta login
```

---

### `insighta logout`

Invalidates the server session and deletes local credentials.

```bash
insighta logout
```

---

### `insighta whoami`

Prints details of the currently authenticated user.

```bash
insighta whoami
```

---

### `insighta profiles list`

Query all profiles with optional filters. Results are paginated and navigable interactively.

```bash
insighta profiles list [OPTIONS]

Options:
  --gender [male|female]                     Filter by gender.
  --country TEXT                             Filter by 2-character ISO country code (e.g. NG, US).
  --age-group [child|teenager|adult|senior]  Filter by age group.
  --min-age INTEGER                          Minimum age.
  --max-age INTEGER                          Maximum age.
  --sort-by [age|created_at|gender_probability]
                                             Field to sort by.  [default: age]
  --order [asc|desc]                         Sort direction.  [default: asc]
  --page INTEGER                             Page number.  [default: 1]
  --limit INTEGER RANGE                      Results per page (10–50).  [default: 10]
  --help                                     Show this message and exit.
```

**Interactive navigation:** press `n` for next page, `p` for previous, `q` (or any other key) to quit.

---

### `insighta profiles get ID`

Fetch a single profile by its 32-character hex ID.

```bash
insighta profiles get <ID>
```

---

### `insighta profiles search QUERY`

Full-text / natural language search across profiles.

```bash
insighta profiles search "young male from Nigeria" [OPTIONS]

Options:
  --sort-by [age|created_at|gender_probability]
  --order [asc|desc]       [default: asc]
  --page INTEGER           [default: 1]
  --limit INTEGER RANGE    [default: 10]
```

Results are paginated with the same interactive navigation as `list`.

---

### `insighta profiles create`

Create a new profile by name (gender, age, and country are inferred).

```bash
insighta profiles create --name "Ada Obi"
```

---

### `insighta profiles export`

Export profiles to a file. The filename is taken from the `Content-Disposition` response header.

```bash
insighta profiles export --format csv [OPTIONS]

Options:
  --format TEXT                              File format (required).
  --gender [male|female]
  --country TEXT
  --age-group [child|teenager|adult|senior]
  --min-age INTEGER
  --max-age INTEGER
  --sort-by [age|created_at|gender_probability]
  --order [asc|desc]
```

The exported file is saved to the current working directory.

---

## Development

Enable debug logging by setting `INSIGHTA_DEVELOPMENT=true` in your `.env`:

```env
INSIGHTA_DEVELOPMENT=true
```

Format code with Black:

```bash
poetry run black insighta/ tests/
```

Lint with Ruff:

```bash
poetry run ruff check insighta/ tests/
```

Run tests:

```bash
poetry run pytest tests/ -v
```

---

## CI/CD

GitHub Actions runs automatically on every pull request targeting `main`.

| Job       | Tool            | What it checks                        |
| --------- | --------------- | ------------------------------------- |
| **Lint**  | `black --check` | Code is correctly formatted           |
| **Lint**  | `ruff check`    | No style or import errors             |
| **Test**  | `pytest`        | All unit tests pass                   |
| **Build** | `poetry build`  | Package can be built as a wheel/sdist |

Workflow definition: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
