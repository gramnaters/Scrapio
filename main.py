"""
Scrapio — Combined Stremio Addon
Sources: MovieBox + HDGharTV + KMMovies
Features: Source selection, audio language filter, quality filter
"""
import os, sys, json, re, base64, asyncio, time
from typing import Optional, List, Dict, Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

# ============================================================
# Config
# ============================================================
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "439c478a771f35c05022f9feabcca01c")
TMDB_BASE = "https://api.themoviedb.org/3"
REQUEST_TIMEOUT = 30.0
HDGHAR_BASE = "https://hdghartv.cc/api"
KM_BASE = "https://kmmovies.shop"
KM_WP_API = f"{KM_BASE}/wp-json/wp/v2"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

_client: Optional[httpx.AsyncClient] = None
async def get_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers={"User-Agent": UA})
    return _client

# ============================================================
# Config parsing
# ============================================================
def parse_config(config_str: str) -> dict:
    if not config_str:
        return {"sources": ["moviebox", "hdghar", "kmmovies"], "language": ["all"], "quality": ["all"]}
    try:
        padding = 4 - (len(config_str) % 4)
        if padding != 4:
            config_str += "=" * padding
        decoded = base64.urlsafe_b64decode(config_str).decode("utf-8")
        config = json.loads(decoded)
        # Normalize language and quality to lists
        if isinstance(config.get("language"), str):
            config["language"] = [config["language"]]
        if isinstance(config.get("quality"), str):
            config["quality"] = [config["quality"]]
        if not config.get("language"):
            config["language"] = ["all"]
        if not config.get("quality"):
            config["quality"] = ["all"]
        return config
    except Exception:
        return {"sources": ["moviebox", "hdghar", "kmmovies"], "language": ["all"], "quality": ["all"]}

def encode_config(sources, language, quality):
    raw = json.dumps({"sources": sources, "language": language, "quality": quality})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

# ============================================================
# TMDB / Cinemeta metadata
# ============================================================
async def resolve_title(http_client, media_type, id_):
    # Handle tmdb: prefix
    if id_.startswith("tmdb:"):
        tmdb_id = id_[5:]
        typ = "tv" if media_type == "series" else "movie"
        # Try TMDB external_ids for IMDb conversion
        url = f"{TMDB_BASE}/{typ}/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
        try:
            r = await http_client.get(url, timeout=10)
            if r.status_code == 200:
                imdb_id = r.json().get("imdb_id")
                if imdb_id:
                    id_ = imdb_id
                else:
                    # Fallback: get title from TMDB directly
                    url2 = f"{TMDB_BASE}/{typ}/{tmdb_id}?api_key={TMDB_API_KEY}"
                    r2 = await http_client.get(url2, timeout=10)
                    if r2.status_code == 200:
                        d = r2.json()
                        title = d.get("name") if media_type == "series" else d.get("title")
                        year = (d.get("first_air_date") or d.get("release_date", ""))[:4]
                        return title, year
        except Exception:
            pass

    # Use Cinemeta
    url = f"https://v3-cinemeta.strem.io/meta/{media_type}/{id_}.json"
    try:
        r = await http_client.get(url, timeout=10)
        if r.status_code == 200:
            meta = r.json().get("meta", {})
            title = meta.get("name")
            year = ""
            ri = str(meta.get("releaseInfo", ""))
            m = re.search(r"\d{4}", ri)
            if m:
                year = m.group(0)
            return title, year
    except Exception:
        pass
    return None, None

# ============================================================
# Source 1: MovieBox
# ============================================================
async def moviebox_streams(http_client, media_type, id_, season, episode, lang_filter, qual_filter):
    try:
        from streaming.metadata import resolve_imdb_id
        from streaming.provider import find_all_matches, extract_streams
        from streaming.helpers import generate_stream_description, generate_stream_title, get_stream_filename

        meta = await resolve_imdb_id(http_client, media_type, id_)
        title = meta.get("name")
        if not title:
            return []

        year_match = re.search(r"\d{4}", str(meta.get("releaseInfo", "")))
        year = year_match.group(0) if year_match else ""

        matches = await find_all_matches(title, year, is_movie=(media_type == "movie"))
        if not matches:
            return []

        stream_results = await extract_streams(matches, media_type == "movie", season, episode)

        pref_lang = lang_filter
        min_res = qual_filter
        streams = []
        seen_urls = set()

        for stream_data in stream_results:
            dl = stream_data["download"]
            audio_lang = stream_data.get("audio_lang")
            subtitle_langs = stream_data.get("subtitle_langs", [])

            url_str = str(dl.url)
            base_dl_url = url_str.split("?")[0] if "?" in url_str else url_str
            if base_dl_url in seen_urls:
                continue
            seen_urls.add(base_dl_url)

            resolution = getattr(dl, "resolution", 0)
            size = getattr(dl, "size", 0)

            # Quality filter
            if min_res == "4k" and resolution < 2160: continue
            elif min_res == "1080p" and resolution < 1080: continue
            elif min_res == "720p" and resolution < 720: continue

            # Language filter (strict)
            if pref_lang != "all":
                if pref_lang == "orig" and audio_lang: continue
                elif pref_lang != "orig":
                    if not audio_lang or pref_lang.lower() not in audio_lang.lower(): continue

            is_dash = "playstream.mpd" in url_str
            fmt_label = "DASH" if is_dash else "MP4"
            res_label = f"{resolution}p" if resolution else "Auto"
            size_label = f"{size/1024/1024:.0f} MB" if size else "adaptive"

            stream_title = f"🎬 {res_label} • {size_label}\n"
            if audio_lang:
                stream_title += f"🔊 {audio_lang}\n"
            if subtitle_langs:
                stream_title += f"💬 {', '.join(subtitle_langs[:5])}\n"
            stream_title += f"📍 MovieBox • {fmt_label}"

            streams.append({
                "name": "Scrapio",
                "title": stream_title,
                "url": url_str,
                "behaviorHints": {
                    "notWebReady": True,
                    "filename": get_stream_filename(url_str),
                    "proxyHeaders": {"request": {
                        "Referer": "https://fmoviesunblocked.net/",
                        "User-Agent": UA,
                    }},
                },
            })
        return streams
    except Exception as e:
        print(f"[Scrapio] MovieBox error: {e}", file=sys.stderr)
        return []

# ============================================================
# Source 2: HDGharTV
# ============================================================
async def hdghar_streams(http_client, media_type, id_, season, episode, lang_filter, qual_filter):
    try:
        title, year = await resolve_title(http_client, media_type, id_)
        if not title:
            return []

        # Search HDGharTV
        search_url = f"{HDGHAR_BASE}/search?q={quote(title)}"
        r = await http_client.get(search_url, headers={"Accept": "application/json"})
        if r.status_code != 200:
            return []
        data = r.json()
        key = "movies" if media_type == "movie" else "series"
        items = data.get(key, [])
        if not items:
            return []

        # Find exact match
        match = None
        for m in items:
            if m.get("title", "").lower().startswith(title.lower()):
                match = m
                break
        if not match:
            match = items[0]

        mongo_id = match.get("_id", "")
        if not mongo_id:
            return []

        # Get details via /movies/public/{id} or /series/public/{id}
        detail_url = f"{HDGHAR_BASE}/{key}/public/{mongo_id}"
        r2 = await http_client.get(detail_url, headers={"Accept": "application/json"})
        if r2.status_code != 200:
            return []
        detail = r2.json()

        streams = []
        if media_type == "movie":
            for link in detail.get("streamingLinks", []):
                if not link.get("isActive", True): continue
                url = link.get("url", "")
                if not url: continue
                quality = link.get("quality", "Unknown")
                q_lower = quality.lower()
                # Language filter for HDGharTV — check quality/title text
                if lang_filter != "all" and lang_filter != "orig":
                    if lang_filter not in q_lower and lang_filter not in title.lower():
                        continue
                if qual_filter == "4k" and "4k" not in q_lower and "2160" not in q_lower: continue
                elif qual_filter == "1080p" and "1080" not in q_lower: continue
                elif qual_filter == "720p" and "720" not in q_lower: continue

                streams.append({
                    "name": "Scrapio",
                    "title": f"🎬 {quality} • {title}\n📍 HDGharTV",
                    "url": url,
                    "behaviorHints": {
                        "notWebReady": True,
                        "proxyHeaders": {"request": {"User-Agent": UA, "Referer": "https://hdghartv.cc/"}},
                    },
                })
        else:
            for s in detail.get("seasons", []):
                if s.get("seasonNumber", s.get("number", 0)) != season: continue
                for ep in s.get("episodes", []):
                    if ep.get("episodeNumber", ep.get("number", 0)) != episode: continue
                    for link in ep.get("streamingLinks", []):
                        if not link.get("isActive", True): continue
                        url = link.get("url", "")
                        if not url: continue
                        quality = link.get("quality", "Unknown")
                        q_lower = quality.lower()
                        if lang_filter != "all" and lang_filter != "orig":
                            if lang_filter not in q_lower and lang_filter not in title.lower():
                                continue
                        streams.append({
                            "name": "Scrapio",
                            "title": f"🎬 {quality} • S{season}E{episode}\n📍 HDGharTV",
                            "url": url,
                            "behaviorHints": {
                                "notWebReady": True,
                                "proxyHeaders": {"request": {"User-Agent": UA, "Referer": "https://hdghartv.cc/"}},
                            },
                        })
        return streams
    except Exception as e:
        print(f"[Scrapio] HDGharTV error: {e}", file=sys.stderr)
        return []

# ============================================================
# Source 3: KMMovies
# ============================================================
async def kmmovies_streams(http_client, media_type, id_, season, episode, lang_filter, qual_filter):
    try:
        title, year = await resolve_title(http_client, media_type, id_)
        if not title:
            return []

        # Search KMMovies
        search_url = f"{KM_WP_API}/posts?search={quote(title)}&per_page=5"
        r = await http_client.get(search_url)
        if r.status_code != 200:
            return []
        posts = r.json()
        if not posts:
            return []

        # Find exact match
        post = None
        lower = title.lower()
        for p in posts:
            t = re.sub(r'<[^>]+>', '', p.get("title", {}).get("rendered", "")).strip()
            if t.lower().startswith(lower) or lower in t.lower():
                post = p
                break
        if not post:
            post = posts[0]

        post_url = post.get("link", "")
        post_title = re.sub(r'<[^>]+>', '', post.get("title", {}).get("rendered", "")).strip()
        # Detect all Indian regional languages from title
        title_lower = post_title.lower()
        detected_langs = []
        for lang in ["hindi", "english", "telugu", "tamil", "kannada", "malayalam", "punjabi", "bengali", "marathi", "gujarati"]:
            if lang in title_lower:
                detected_langs.append(lang)
        if not detected_langs:
            detected_langs = ["english"]  # default
        if "dual audio" in title_lower or ("hindi" in title_lower and "english" in title_lower):
            audio = "Dual Audio"
        elif detected_langs:
            audio = detected_langs[0].capitalize()

        # Language filter
        if lang_filter != "all":
            if lang_filter == "orig":
                pass  # original = no dubbed language, skip
            elif lang_filter not in [l.lower() for l in detected_langs] and lang_filter not in title_lower:
                return []

        # Parse download links
        r2 = await http_client.get(post_url)
        if r2.status_code != 200:
            return []
        html = r2.text

        idx = html.find('downloads-section')
        if idx < 0:
            return []
        section = html[idx:idx+50000]

        streams = []
        has_seasons = 'season-block' in section

        if has_seasons and media_type == "series":
            # Parse season blocks
            season_pattern = re.compile(
                r'<div class="season-block[^"]*"[^>]*>.*?<span class="season-block-title">\s*(Season\s+(\d+)).*?</div>\s*<div class="season-block-body">(.*?)(?=<div class="season-block|</div>\s*</div>\s*</div>)',
                re.DOTALL
            )
            for m in season_pattern.finditer(section):
                season_num = int(m.group(2))
                if season_num != season: continue
                body = m.group(3)
                buttons = re.findall(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*dl-btn[^"]*"[^>]*>(.*?)</a>', body, re.DOTALL)
                for href, content in buttons:
                    res_m = re.search(r'<span class="dl-res">([^<]+)</span>', content)
                    quality = res_m.group(1).strip() if res_m else "Unknown"
                    # Skip non-seekable GDrive links and zip files
                    if "gdtot" in href.lower() or "hubcloud" in href.lower(): continue
                    if ".zip" in quality.lower() or "zip" in quality.lower(): continue
                    # Quality filter
                    q_lower = quality.lower()
                    if qual_filter == "4k" and "2160" not in q_lower and "4k" not in q_lower: continue
                    elif qual_filter == "1080p" and "1080" not in q_lower: continue
                    elif qual_filter == "720p" and "720" not in q_lower: continue

                    # Resolve the link
                    direct_url = await _resolve_km_link(http_client, href, media_type, season, episode)
                    if direct_url:
                        streams.append({
                            "name": "Scrapio",
                            "title": f"🎬 {quality} • S{season}E{episode} • {audio}\n📍 KMMovies",
                            "url": direct_url,
                            "behaviorHints": {
                                "notWebReady": True,
                                "proxyHeaders": {"request": {"User-Agent": UA, "Referer": "https://kmmovies.shop/"}},
                            },
                        })
        else:
            # Movie
            buttons = re.findall(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*dl-btn[^"]*"[^>]*>(.*?)</a>', section, re.DOTALL)
            for href, content in buttons:
                res_m = re.search(r'<span class="dl-res">([^<]+)</span>', content)
                size_m = re.search(r'<span class="dl-size">([^<]+)</span>', content)
                quality = res_m.group(1).strip() if res_m else "Unknown"
                size = size_m.group(1).strip() if size_m else ""
                # Skip non-seekable GDrive links and zip files
                if "gdtot" in href.lower() or "hubcloud" in href.lower(): continue
                if ".zip" in quality.lower() or "zip" in (size + quality).lower(): continue
                # Quality filter
                q_lower = quality.lower()
                if qual_filter == "4k" and "2160" not in q_lower and "4k" not in q_lower: continue
                elif qual_filter == "1080p" and "1080" not in q_lower: continue
                elif qual_filter == "720p" and "720" not in q_lower: continue

                # Resolve the link
                direct_url = await _resolve_km_link(http_client, href, media_type, 0, 0)
                if direct_url:
                    # Skip .zip URLs
                    if ".zip" in direct_url.lower(): continue
                    streams.append({
                        "name": "Scrapio",
                        "title": f"🎬 {quality} • {audio}" + (f" • {size}" if size else "") + f"\n📍 KMMovies",
                        "url": direct_url,
                        "behaviorHints": {
                            "notWebReady": True,
                            "proxyHeaders": {"request": {"User-Agent": UA, "Referer": "https://kmmovies.shop/"}},
                        },
                    })
        return streams
    except Exception as e:
        print(f"[Scrapio] KMMovies error: {e}", file=sys.stderr)
        return []

async def _resolve_km_link(http_client, magiclinks_url, media_type, season, episode):
    """Resolve KMMovies magiclinks URL to a direct seekable video URL."""
    try:
        # For series: episodes.magiclinks.lol → skydrop.sbs → api.php → download_url
        if "episodes.magiclinks" in magiclinks_url:
            r = await http_client.get(magiclinks_url, headers={"Referer": f"{KM_BASE}/"})
            if r.status_code != 200: return None
            html = r.text
            skydrop_urls = re.findall(r'https://w[0-9]+\.skydrop\.sbs/download\.php\?id=[A-Za-z0-9_\-]+', html)
            if not skydrop_urls: return None
            unique = list(dict.fromkeys(skydrop_urls))
            # For episode-wise, we need the right episode index
            # The magiclinks URL already points to a specific quality+season
            # Each skydrop URL is one episode
            file_id = unique[0].split('id=')[1]
            api_url = f"https://w1.skydrop.sbs/api.php?id={file_id}"
            r2 = await http_client.get(api_url, headers={"Referer": "https://w1.skydrop.sbs/", "X-Requested-With": "XMLHttpRequest"})
            if r2.status_code != 200: return None
            data = r2.json()
            if data.get("success") and data.get("download_url"):
                return data["download_url"]
            return None

        # For movies: magiclinks.lol → mirrors (skydrop/flexplayer/gdtot/kmphotos)
        elif "magiclinks.lol" in magiclinks_url:
            r = await http_client.get(magiclinks_url, headers={"Referer": f"{KM_BASE}/"})
            if r.status_code != 200: return None
            html = r.text
            anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for href, text in anchors:
                text_clean = re.sub(r'<[^>]+>', '', text).strip().upper()
                if any(s in href.lower() for s in ['facebook', 'twitter', 'whatsapp', 'telegram', 'share', '#']): continue
                # Try skydrop/flexplayer first (most seekable)
                if 'SKYDROP' in text_clean or 'FLEXPLAYER' in href:
                    m = re.search(r'\?file=([A-Za-z0-9_\-]+)', href)
                    if m:
                        file_id = m.group(1)
                        base = re.match(r'(https://w[0-9]+\.flexplayer\.buzz)', href)
                        if base:
                            api_url = f"{base.group(1)}/pkmmain/api.php?id={file_id}"
                            try:
                                r2 = await http_client.get(api_url, headers={"Referer": href, "X-Requested-With": "XMLHttpRequest"}, timeout=10.0)
                                if r2.status_code == 200:
                                    try:
                                        data = r2.json()
                                        if data.get("success") and data.get("download_url"):
                                            return data["download_url"]
                                    except: pass
                            except: pass
                # Try kmphotos direct (seekable) — both download99.php and online.php
                elif 'ZIP-ZAP' in text_clean or 'KMPHOTOS' in href.upper():
                    if 'skytech.works' not in href:
                        return href
            # Fallback: try to find any kmphotos URL in the page
            km_urls = re.findall(r'https://z\d+\.kmphotos\.cv/(?:download99|online)\.php\?file=[^"\'<>\s]+', html)
            if km_urls:
                return km_urls[0]
            return None

        return None
    except Exception:
        return None

# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(title="Scrapio")

@app.on_event("startup")
async def startup():
    print("[Scrapio] Started", file=sys.stderr)

def build_manifest(config=None):
    return {
        "id": "com.scrapio.addon",
        "version": "1.0.0",
        "name": "Scrapio",
        "description": "Movies & series from MovieBox, HDGharTV, KMMovies.",
        "logo": "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode(),
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt", "tmdb"],
        "catalogs": [],
        "behaviorHints": {"configurable": True},
    }

@app.get("/manifest.json")
async def manifest():
    return build_manifest()

@app.get("/{config}/manifest.json")
async def manifest_configured(config: str):
    return build_manifest(parse_config(config))

@app.get("/stream/movie/{id}.json")
async def stream_movie(id: str):
    return {"streams": await handle_stream("movie", id, 1, 1, "")}

@app.get("/{config}/stream/movie/{id}.json")
async def stream_movie_configured(config: str, id: str):
    return {"streams": await handle_stream("movie", id, 1, 1, config)}

@app.get("/stream/series/{id}.json")
@app.get("/stream/series/{id}:{season}.json")
@app.get("/stream/series/{id}:{season}:{episode}.json")
async def stream_series(id: str, season: Optional[str] = None, episode: Optional[str] = None):
    if not season or not episode: return {"streams": []}
    return {"streams": await handle_stream("series", id, int(season), int(episode), "")}

@app.get("/{config}/stream/series/{id}.json")
@app.get("/{config}/stream/series/{id}:{season}.json")
@app.get("/{config}/stream/series/{id}:{season}:{episode}.json")
async def stream_series_configured(config: str, id: str, season: Optional[str] = None, episode: Optional[str] = None):
    if not season or not episode: return {"streams": []}
    return {"streams": await handle_stream("series", id, int(season), int(episode), config)}

async def handle_stream(media_type, id_, season, episode, config_str):
    config = parse_config(config_str)
    sources = config.get("sources", ["moviebox", "hdghar", "kmmovies"])
    langs = config.get("language", ["all"])
    quals = config.get("quality", ["all"])
    if isinstance(langs, str): langs = [langs]
    if isinstance(quals, str): quals = [quals]

    # If "all" is in the list, treat as all
    has_all_lang = "all" in langs
    has_all_qual = "all" in quals

    # Parse ID (handle tmdb: prefix for series)
    parts = id_.split(":")
    content_id = id_
    if parts[0] == "tmdb":
        content_id = "tmdb:" + parts[1]
        if media_type == "series" and len(parts) >= 4:
            season = int(parts[2])
            episode = int(parts[3])
    elif media_type == "series" and len(parts) >= 3:
        content_id = parts[0]
        season = int(parts[1])
        episode = int(parts[2])

    client = await get_client()
    all_streams = []

    # Run all enabled sources in parallel
    # For multi-select: if "all" is selected, pass "all"; otherwise pass the first selected value
    lang_filter = "all" if has_all_lang else langs[0] if langs else "all"
    qual_filter = "all" if has_all_qual else quals[0] if quals else "all"

    tasks = []
    if "moviebox" in sources:
        tasks.append(("MovieBox", moviebox_streams(client, media_type, content_id, season, episode, lang_filter, qual_filter)))
    if "hdghar" in sources:
        tasks.append(("HDGharTV", hdghar_streams(client, media_type, content_id, season, episode, lang_filter, qual_filter)))
    if "kmmovies" in sources:
        tasks.append(("KMMovies", kmmovies_streams(client, media_type, content_id, season, episode, lang_filter, qual_filter)))

    results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[Scrapio] {tasks[i][0]} error: {result}", file=sys.stderr)
        elif result:
            all_streams.extend(result)

    return all_streams

@app.get("/health")
async def health():
    return {"status": "ok", "sources": ["moviebox", "hdghar", "kmmovies"]}

@app.get("/")
async def root():
    return RedirectResponse(url="/configure")

@app.get("/configure")
async def configure_page():
    return HTMLResponse(CONFIGURE_HTML)

# ============================================================
# Logo (minimalist SVG)
# ============================================================
LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#000"/>
  <text x="32" y="46" font-family="Arial Black,sans-serif" font-size="42" font-weight="900" fill="#fff" text-anchor="middle">S</text>
</svg>'''

# ============================================================
# Config page
# ============================================================
CONFIGURE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scrapio — Stremio Addon</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#000;color:#e5e5e5;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
.wrap{max-width:440px;width:100%}
.header{text-align:center;margin-bottom:2.5rem}
.header h1{font-family:'Orbitron',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:2px;color:#fff;text-shadow:0 0 30px rgba(255,255,255,.1)}
.section{margin-bottom:1.5rem}
.section h3{font-size:.75rem;font-weight:600;color:rgba(255,255,255,.85);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:.75rem}
.sources{display:flex;flex-direction:column;gap:.5rem}
.source{display:flex;align-items:center;gap:.75rem;padding:.85rem 1rem;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:12px;cursor:pointer;transition:all .2s;-webkit-tap-highlight-color:transparent}
.source:hover{background:rgba(255,255,255,.04);border-color:rgba(255,255,255,.1)}
.source.active{background:rgba(255,255,255,.03);border-color:rgba(255,255,255,.12)}
.source .check{width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;transition:all .15s;flex-shrink:0}
.source.active .check{background:#2563eb;border-color:#2563eb}
.source.active .check::after{content:'';width:5px;height:9px;border:solid #fff;border-width:0 2px 2px 0;transform:rotate(45deg)}
.source .label{font-size:.95rem;font-weight:500}
.tags{display:flex;flex-wrap:wrap;gap:.5rem}
.tag{padding:.5rem 1.2rem;border-radius:50px;font-size:.85rem;font-weight:500;cursor:pointer;transition:background .2s ease,color .2s ease,border-color .2s ease;user-select:none;-webkit-tap-highlight-color:transparent;-webkit-user-select:none;outline:none;color:rgba(255,255,255,.85);background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.08)}
.tag:hover{color:rgba(255,255,255,.7);border-color:rgba(255,255,255,.15)}
.tag.active{color:#000;background:#fff;border:1px solid #fff;backdrop-filter:blur(18px) saturate(180%);-webkit-backdrop-filter:blur(18px) saturate(180%);box-shadow:0 6px 18px rgba(255,255,255,.15), inset 0 1px 0 rgba(255,255,255,.9)}
.url-box{width:100%;padding:1rem;background:rgba(255,255,255,.03);border:1px solid rgba(37,99,235,.5);border-radius:12px;font-family:monospace;font-size:.78rem;color:#e5e5e5;word-break:break-all;text-align:center;min-height:50px;display:flex;align-items:center;justify-content:center;margin-bottom:.75rem}
.btn{display:block;width:100%;background:#2563eb;color:#fff;border:none;padding:1rem;font-size:1rem;font-weight:700;border-radius:12px;cursor:pointer;transition:all .2s;-webkit-tap-highlight-color:transparent}
.btn:hover{background:#1d4ed8}
.note{margin-top:1rem;font-size:.72rem;color:rgba(255,255,255,.2);text-align:center}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
<h1>SCRAPiO</h1>
</div>

<div class="section">
<h3>Sources</h3>
<div class="sources">
<div class="source active" data-source="moviebox"><span class="check"></span><span class="label">MovieBox</span></div>
<div class="source active" data-source="hdghar"><span class="check"></span><span class="label">HDGharTV</span></div>
<div class="source active" data-source="kmmovies"><span class="check"></span><span class="label">KMMovies</span></div>
</div>
</div>

<div class="section">
<h3>Audio</h3>
<div class="tags" id="audio-tags">
<div class="tag active" data-value="all">All</div>
<div class="tag" data-value="hindi">Hindi</div>
<div class="tag" data-value="english">English</div>
<div class="tag" data-value="telugu">Telugu</div>
<div class="tag" data-value="tamil">Tamil</div>
<div class="tag" data-value="kannada">Kannada</div>
<div class="tag" data-value="malayalam">Malayalam</div>
<div class="tag" data-value="punjabi">Punjabi</div>
<div class="tag" data-value="bengali">Bengali</div>
<div class="tag" data-value="marathi">Marathi</div>
<div class="tag" data-value="orig">Original</div>
</div>
</div>

<div class="section">
<h3>Quality</h3>
<div class="tags" id="quality-tags">
<div class="tag active" data-value="all">All</div>
<div class="tag" data-value="4k">4K</div>
<div class="tag" data-value="1080p">1080p+</div>
<div class="tag" data-value="720p">720p+</div>
</div>
</div>

<div class="url-box" id="url">Loading...</div>
<button class="btn" id="copy" onclick="copyUrl()">Copy Manifest URL</button>

</div>

<script>
document.querySelectorAll('.source').forEach(function(s){
  s.addEventListener('click', function(e){
    e.preventDefault();
    this.classList.toggle('active');
    updateUrl();
  });
});

document.querySelectorAll('.tags').forEach(function(container){
  container.querySelectorAll('.tag').forEach(function(tag){
    tag.addEventListener('click', function(){
      if(this.dataset.value === 'all'){
        container.querySelectorAll('.tag').forEach(function(t){ t.classList.remove('active'); });
        this.classList.add('active');
      } else {
        container.querySelector('.tag[data-value="all"]').classList.remove('active');
        this.classList.toggle('active');
        if(container.querySelectorAll('.tag.active').length === 0){
          container.querySelector('.tag[data-value="all"]').classList.add('active');
        }
      }
      updateUrl();
    });
  });
});

function getActiveValues(containerId){
  var vals = [];
  document.querySelectorAll('#' + containerId + ' .tag.active').forEach(function(t){
    vals.push(t.dataset.value);
  });
  return vals;
}

function updateUrl(){
  var sources = [];
  document.querySelectorAll('.source.active').forEach(function(d){ sources.push(d.dataset.source); });
  var langs = getActiveValues('audio-tags');
  var quals = getActiveValues('quality-tags');
  var config = {sources: sources, language: langs, quality: quals};
  var encoded = btoa(JSON.stringify(config)).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
  var url = window.location.href.replace(/configure\\/?$/,'').replace(/\\/$/,'') + '/' + encoded + '/manifest.json';
  document.getElementById('url').textContent = url;
}

function copyUrl(){
  navigator.clipboard.writeText(document.getElementById('url').textContent);
  var b = document.getElementById('copy');
  b.textContent = 'Copied!';
  setTimeout(function(){ b.textContent = 'Copy Manifest URL'; }, 2000);
}

updateUrl();
</script>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
