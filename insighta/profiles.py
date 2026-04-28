from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List

import rich_click as click
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console

from .settings import settings
from .client import authed_request, raise_for_status


@dataclass
class ProfileData:
    id: str
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: str

    @classmethod
    def from_dict(cls, data: dict) -> ProfileData:
        return cls(
            id=data["id"],
            name=data["name"],
            gender=data["gender"],
            gender_probability=float(data["gender_probability"]),
            age=int(data["age"]),
            age_group=data["age_group"],
            country_id=data["country_id"],
            country_name=data["country_name"],
            country_probability=float(data["country_probability"]),
            created_at=data["created_at"],
        )


@dataclass
class ProfileResponse:
    status: str
    profile: ProfileData

    @classmethod
    def from_dict(cls, data: dict) -> ProfileResponse:
        return cls(
            status=data["status"], profile=ProfileData.from_dict(data.get("data", {}))
        )


@dataclass
class ProfilesResponse:
    status: str
    page: int
    limit: int
    total: int
    total_pages: int
    links: dict[str, str | None]
    profiles: List[ProfileData]

    @classmethod
    def from_dict(cls, data: dict) -> ProfilesResponse:
        return cls(
            status=data["status"],
            page=int(data["page"]),
            limit=int(data["limit"]),
            total=int(data["total"]),
            total_pages=int(data["total_pages"]),
            links=data["links"],
            profiles=[ProfileData.from_dict(p) for p in data.get("data", [])],
        )


def profile_table(title: Optional[str] = None) -> Table:
    table = Table(title=title, show_lines=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Gender", justify="center")
    table.add_column("Gender Prob.", justify="right", style="cyan")
    table.add_column("Age", justify="right", style="yellow")
    table.add_column("Age Group", style="yellow")
    table.add_column("Country")
    table.add_column("Country Prob.", justify="right", style="cyan")
    table.add_column("Created At", no_wrap=True, style="dim")

    return table


def profile_row(profile: ProfileData) -> List[str]:
    gender_color = "blue" if profile.gender.lower() == "male" else "magenta"
    created_at = (
        datetime.fromisoformat(profile.created_at)
        .astimezone(timezone.utc)
        .strftime("%d %b %Y %H:%M")
    )
    return [
        profile.id,
        profile.name,
        f"[{gender_color}]{profile.gender.capitalize()}[/{gender_color}]",
        f"{profile.gender_probability:.1%}",
        str(profile.age),
        profile.age_group.capitalize(),
        f"{profile.country_name} ({profile.country_id})",
        f"{profile.country_probability:.1%}",
        created_at,
    ]


@click.command()
@click.option(
    "--gender",
    type=click.Choice(["male", "female"], case_sensitive=False),
    help="Filter by gender.",
)
@click.option(
    "--country",
    help="Filter by 2-character ISO country code (e.g. NG, US).",
    callback=lambda ctx, param, value: (
        (_ for _ in ()).throw(click.BadParameter("Must be a 2-character country code."))
        if value is not None and len(value) != 2
        else value
    ),
    is_eager=False,
)
@click.option(
    "--age-group",
    type=click.Choice(["child", "teenager", "adult", "senior"], case_sensitive=False),
    help="Filter by age group.",
)
@click.option("--min-age", type=click.IntRange(min=0), help="Minimum age to filter by.")
@click.option("--max-age", type=click.IntRange(min=0), help="Maximum age to filter by.")
@click.option(
    "--sort-by",
    type=click.Choice(
        ["age", "created_at", "gender_probability"], case_sensitive=False
    ),
    default="age",
    show_default=True,
    help="Field to sort results by.",
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    show_default=True,
    help="Sort direction.",
)
@click.option(
    "--page",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Page number.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=10, max=50),
    default=10,
    show_default=True,
    help="Results per page (10–50).",
)
def list(
    gender: Optional[str],
    country: Optional[str],
    age_group: Optional[str],
    min_age: Optional[int],
    max_age: Optional[int],
    sort_by: str,
    order: str,
    page: int,
    limit: int,
):
    """Query profiles with optional filters."""
    try:
        if min_age is not None and max_age is not None and min_age > max_age:
            raise click.UsageError("--min-age cannot be greater than --max-age.")

        params: dict = {
            "gender": gender,
            "country_id": country,
            "age_group": age_group,
            "min_age": min_age,
            "max_age": max_age,
            "sort_by": sort_by,
            "order": order,
            "page": page,
            "limit": limit,
        }
        # Strip None values so they aren't sent as query params
        params = {k: v for k, v in params.items() if v is not None}

        console = Console()
        next_url: Optional[str] = f"{settings.INSIGHTA_BACKEND_URL}/api/profiles"
        next_params: Optional[dict] = params

        while next_url:
            console.clear()
            with console.status("Fetching profiles..."):
                response = authed_request("GET", next_url, params=next_params)
                raise_for_status(response)
                result = ProfilesResponse.from_dict(response.json())

            console.print(
                f"Page [bold]{result.page}[/bold] of [bold]{result.total_pages}[/bold] "
                f"— [bold]{result.total}[/bold] total profiles"
            )

            # Show active filters if any were specified
            filter_keys = {"gender", "country_id", "age_group", "min_age", "max_age"}
            active_filters = {k: v for k, v in params.items() if k in filter_keys}
            if active_filters:
                filter_parts = [
                    f"[dim]{k.replace('_', ' ')}:[/dim] [cyan]{v}[/cyan]"
                    for k, v in active_filters.items()
                ]
                console.print("Filters: " + "  ·  ".join(filter_parts))

            table = profile_table()

            for profile in result.profiles:
                table.add_row(*profile_row(profile))

            console.print(table)

            # Build navigation prompt based on available links
            has_next = result.links.get("next") is not None
            has_prev = result.links.get("prev") is not None

            nav_parts = []
            if has_next:
                nav_parts.append("[bold]n[/bold] next")
            if has_prev:
                nav_parts.append("[bold]p[/bold] prev")
            nav_parts.append("[bold]q[/bold] quit")

            console.print(" · ".join(nav_parts))

            key = click.getchar().lower()
            console.print()  # newline after keypress

            if key == "n" and has_next:
                next_url = f"{settings.INSIGHTA_BACKEND_URL}{result.links['next']}"
                next_params = None  # params are already encoded in the link URL
            elif key == "p" and has_prev:
                next_url = f"{settings.INSIGHTA_BACKEND_URL}{result.links['prev']}"
                next_params = None
            else:
                break

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to list profiles: {e}") from e


@click.command()
@click.argument("id")
def get(id: str):
    """Get a specific profile by ID.

    \b
    Arguments:
      ID  The unique 32-character hex ID of the profile.
    """
    try:
        console = Console()
        with console.status("Getting profile..."):
            response = authed_request(
                "GET", f"{settings.INSIGHTA_BACKEND_URL}/api/profiles/{id}"
            )
            raise_for_status(response)
            result = ProfileResponse.from_dict(response.json())

        table = profile_table(f"Profile: {result.profile.name}")
        table.add_row(*profile_row(result.profile))

        console.print(table)

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to get profile: {e}") from e


@click.command()
@click.argument("query")
@click.option(
    "--sort-by",
    type=click.Choice(
        ["age", "created_at", "gender_probability"], case_sensitive=False
    ),
    default="age",
    show_default=True,
    help="Field to sort results by.",
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    show_default=True,
    help="Sort direction.",
)
@click.option(
    "--page",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Page number.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=10, max=50),
    default=10,
    show_default=True,
    help="Results per page (10–50).",
)
def search(query: str, sort_by: str, order: str, page: int, limit: int):
    """Search for profiles with natural language.

    \b
    Arguments:
      QUERY  Natural language query string.
    """
    try:
        params: dict = {
            "q": query,
            "sort_by": sort_by,
            "order": order,
            "page": page,
            "limit": limit,
        }

        console = Console()
        next_url: Optional[str] = f"{settings.INSIGHTA_BACKEND_URL}/api/profiles/search"
        next_params: Optional[dict] = params

        while next_url:
            console.clear()
            with console.status("Fetching profiles..."):
                response = authed_request("GET", next_url, params=next_params)
                raise_for_status(response)
                result = ProfilesResponse.from_dict(response.json())

            console.print(
                f"Page [bold]{result.page}[/bold] of [bold]{result.total_pages}[/bold] "
                f"— [bold]{result.total}[/bold] total profiles"
            )
            console.print(f"[bold]Query[/bold]: [dim italic]{query}[/dim italic]")

            table = profile_table()

            for profile in result.profiles:
                table.add_row(*profile_row(profile))

            console.print(table)

            # Build navigation prompt based on available links
            has_next = result.links.get("next") is not None
            has_prev = result.links.get("prev") is not None

            nav_parts = []
            if has_next:
                nav_parts.append("[bold]n[/bold] next")
            if has_prev:
                nav_parts.append("[bold]p[/bold] prev")
            nav_parts.append("[bold]q[/bold] quit")

            console.print(" · ".join(nav_parts))

            key = click.getchar().lower()
            console.print()  # newline after keypress

            if key == "n" and has_next:
                next_url = f"{settings.INSIGHTA_BACKEND_URL}{result.links['next']}"
                next_params = None  # params are already encoded in the link URL
            elif key == "p" and has_prev:
                next_url = f"{settings.INSIGHTA_BACKEND_URL}{result.links['prev']}"
                next_params = None
            else:
                break

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to search profiles: {e}") from e


@click.command()
@click.option("--name", required=True, help="Name to query and create a profile for.")
def create(name: str):
    """Create profile with specified name."""
    try:
        console = Console()
        with console.status("Creating profile..."):
            response = authed_request(
                "POST", f"{settings.INSIGHTA_BACKEND_URL}/api/profiles", json={"name": name}
            )
            raise_for_status(response)
            result = ProfileResponse.from_dict(response.json())

        table = profile_table()
        table.add_row(*profile_row(result.profile))

        console.print(
            f"[bold green]Successfully created profile[/bold green]: [italic cyan]{result.profile.name} ({result.profile.gender})[/italic cyan]"
        )
        console.print(table)

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to create profile: {e}") from e


@click.command()
@click.option("--format", required=True, help="File format for export.")
@click.option(
    "--gender",
    type=click.Choice(["male", "female"], case_sensitive=False),
    help="Filter by gender.",
)
@click.option(
    "--country",
    help="Filter by 2-character ISO country code (e.g. NG, US).",
    callback=lambda ctx, param, value: (
        (_ for _ in ()).throw(click.BadParameter("Must be a 2-character country code."))
        if value is not None and len(value) != 2
        else value
    ),
    is_eager=False,
)
@click.option(
    "--age-group",
    type=click.Choice(["child", "teenager", "adult", "senior"], case_sensitive=False),
    help="Filter by age group.",
)
@click.option("--min-age", type=click.IntRange(min=0), help="Minimum age to filter by.")
@click.option("--max-age", type=click.IntRange(min=0), help="Maximum age to filter by.")
@click.option(
    "--sort-by",
    type=click.Choice(
        ["age", "created_at", "gender_probability"], case_sensitive=False
    ),
    default="age",
    show_default=True,
    help="Field to sort results by.",
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    show_default=True,
    help="Sort direction.",
)
def export(
    gender: Optional[str],
    country: Optional[str],
    age_group: Optional[str],
    min_age: Optional[int],
    max_age: Optional[int],
    format: str,
    sort_by: str,
    order: str,
):
    """Export profiles to file in specified format and optional filters."""
    try:
        if min_age is not None and max_age is not None and min_age > max_age:
            raise click.UsageError("--min-age cannot be greater than --max-age.")

        params: dict = {
            "format": format,
            "gender": gender,
            "country_id": country,
            "age_group": age_group,
            "min_age": min_age,
            "max_age": max_age,
            "sort_by": sort_by,
            "order": order,
        }
        # Strip None values so they aren't sent as query params
        params = {k: v for k, v in params.items() if v is not None}

        console = Console()
        with console.status("Export profiles..."):
            response = authed_request(
                "GET",
                f"{settings.INSIGHTA_BACKEND_URL}/api/profiles/export",
                params=params,
            )
            raise_for_status(response)

            # Extract filename from Content-Disposition header, fall back to timestamp
            content_disposition = response.headers.get("Content-Disposition", "")
            filename = None
            for part in content_disposition.split(";"):
                part = part.strip()
                if part.startswith("filename="):
                    filename = part[len("filename=") :].strip().strip('"')
                    break
            if not filename:
                from datetime import datetime, timezone

                timestamp = datetime.now(timezone.utc).timestamp()
                filename = f"profiles_{timestamp}.csv"

            output_path = Path.cwd() / filename
            output_path.write_bytes(response.content)

        size_bytes = output_path.stat().st_size
        size_str = (
            f"{size_bytes / 1024:.1f} KB" if size_bytes >= 1024 else f"{size_bytes} B"
        )

        filter_keys = {"gender", "country_id", "age_group", "min_age", "max_age"}
        active_filters = {k: v for k, v in params.items() if k in filter_keys}
        filter_str = (
            "  ·  ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in active_filters.items()
            )
            if active_filters
            else "none"
        )

        summary = Text()
        summary.append("  File     ", style="dim")
        summary.append(f"{filename}\n", style="bold")
        summary.append("  Path     ", style="dim")
        summary.append(f"{output_path}\n", style="cyan")
        summary.append("  Size     ", style="dim")
        summary.append(f"{size_str}\n", style="green")
        summary.append("  Filters  ", style="dim")
        summary.append(filter_str, style="cyan")

        console.print(
            Panel(
                summary, title="[bold green]Export Complete[/bold green]", expand=False
            )
        )

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to export profiles: {e}") from e
