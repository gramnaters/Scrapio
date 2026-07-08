import re
from urllib.parse import urlparse

FILE_EXT_PATTERN = re.compile(r".+\.(\w+)\?.+")


def _format_size(size: int) -> str:
    """Format byte size into human-readable string."""
    size_mb = size // 1024 // 1024
    if size_mb > 1024:
        return f"{size_mb / 1024:.2f} GB"
    return f"{size_mb} MB"


def _format_resolution(resolution: int) -> str:
    """Format resolution into display string."""
    if resolution >= 2160:
        return "4K"
    elif resolution >= 1080:
        return "1080p"
    elif resolution >= 720:
        return "720p"
    else:
        return f"{resolution}p"


def generate_stream_title(
    resolution: int, size: int, audio_langs: list[str] = None
) -> str:
    """Generate a clean stream title with resolution and optional audio language."""
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)

    title = f"{res_str} • {size_str}"

    if audio_langs:
        lang_str = ", ".join(audio_langs[:3])
        title += f" • {lang_str}"

    return title


def generate_stream_description(
    resolution: int,
    size: int,
    audio_langs: list[str] = None,
    subtitle_langs: list[str] = None,
) -> str:
    """Generate stream description with quality, size, audio, and subtitle info."""
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)

    lines = [f"🎬 {res_str} • 💾 {size_str}"]

    if audio_langs:
        lang_str = ", ".join(audio_langs)
        lines.append(f"🔊 {lang_str} Audio")

    if subtitle_langs:
        sub_str = ", ".join(subtitle_langs[:5])
        if len(subtitle_langs) > 5:
            sub_str += f" +{len(subtitle_langs) - 5}"
        lines.append(f"💬 {sub_str} Subs")

    return "\n".join(lines)


def get_stream_filename(url: str) -> str:
    """Extract or generate a filename with proper extension from a stream URL.
    This fixes the 'unrecognized file format' error in Stremio by providing
    a filename hint with a known video extension.
    """
    url_str = str(url)

    # Try to extract extension from URL (handles ?query params)
    ext_match = FILE_EXT_PATTERN.match(url_str)
    if ext_match:
        ext = ext_match.group(1).lower()
        if ext in ("mp4", "mkv", "avi", "webm", "m4v", "mov", "ts"):
            return f"stream.{ext}"

    # Try from URL path
    parsed = urlparse(url_str)
    path = parsed.path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ("mp4", "mkv", "avi", "webm", "m4v", "mov", "ts"):
            return f"stream.{ext}"

    # Default to mp4 — most Provider streams are mp4
    return "stream.mp4"
