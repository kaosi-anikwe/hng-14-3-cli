import click
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

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

        response = authed_request(
            "GET",
            f"{settings.BACKEND_URL}/api/profiles",
            params=params,
        )
        raise_for_status(response)
        result = ProfilesResponse.from_dict(response.json())

        click.echo(
            f"Page {result.page}/{result.total_pages} — {result.total} total profiles"
        )

        # TODO: show tabulated result with pagination

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
        response = authed_request("GET", f"{settings.BACKEND_URL}/api/profiles/{id}")
        raise_for_status(response)
        result = ProfileResponse.from_dict(response.json())

        click.echo(f"Profile: {result.profile.name}")

        # TODO: show in proper way

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
        response = authed_request(
            "GET",
            f"{settings.BACKEND_URL}/api/profiles/search",
            params=params,
        )
        raise_for_status(response)
        result = ProfilesResponse.from_dict(response.json())

        click.echo(
            f"Page {result.page}/{result.total_pages} — {result.total} total profiles"
        )

        # TODO: show tabulated result with pagination

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to search profiles: {e}") from e


@click.command()
@click.option("--name", required=True, help="Name to query and create a profile for.")
def create(name: str):
    """Create profile with specified name."""
    try:
        response = authed_request(
            "POST", f"{settings.BACKEND_URL}/api/profiles", json={"name": name}
        )
        raise_for_status(response)
        result = ProfileResponse.from_dict(response.json())

        click.echo(
            f"Successfully created profile: {result.profile.name} ({result.profile.gender})"
        )

        # TODO: show in proper way

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

        response = authed_request(
            "GET",
            f"{settings.BACKEND_URL}/api/profiles/export",
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
        click.echo(f"Exported to {output_path}")

    except click.ClickException, click.UsageError:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to export profiles: {e}") from e
