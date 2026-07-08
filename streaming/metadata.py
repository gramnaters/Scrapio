import httpx

TMDB_API_KEY = "439c478a771f35c05022f9feabcca01c"


async def resolve_tmdb_to_imdb(
    http_client: httpx.AsyncClient, media_type: str, tmdb_id: str
) -> str | None:
    """Convert a TMDB ID to an IMDb ID using the TMDB API."""
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
    try:
        response = await http_client.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            imdb_id = data.get("imdb_id")
            if imdb_id:
                return imdb_id
    except Exception:
        pass
    return None


async def resolve_imdb_id(
    http_client: httpx.AsyncClient, type_: str, id_: str
) -> dict:
    """Resolve any ID (IMDb tt... or TMDB tmdb:...) to metadata via Cinemeta.

    For TMDB IDs, first converts to IMDb ID via TMDB API, then queries Cinemeta.
    """
    # If it's a TMDB ID (tmdb:12345 or just digits), convert to IMDb first
    if id_.startswith("tmdb:") or id_.isdigit():
        tmdb_id = id_.replace("tmdb:", "")
        media_type = "tv" if type_ == "series" else "movie"
        imdb_id = await resolve_tmdb_to_imdb(http_client, media_type, tmdb_id)
        if imdb_id:
            id_ = imdb_id
        else:
            # Fallback: try using TMDB API directly for title
            return await resolve_tmdb_metadata(http_client, media_type, tmdb_id)

    # Use Cinemeta with IMDb ID
    url = f"https://v3-cinemeta.strem.io/meta/{type_}/{id_}.json"
    try:
        response = await http_client.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("meta", {})
    except Exception:
        pass
    return {}


async def resolve_tmdb_metadata(
    http_client: httpx.AsyncClient, media_type: str, tmdb_id: str
) -> dict:
    """Fallback: get metadata directly from TMDB API if Cinemeta fails."""
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
    try:
        response = await http_client.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            title = data.get("name") if media_type == "tv" else data.get("title")
            release_date = data.get("first_air_date") or data.get("release_date", "")
            return {
                "name": title,
                "releaseInfo": release_date[:4] if release_date else "",
                "year": release_date[:4] if release_date else "",
            }
    except Exception:
        pass
    return {}
