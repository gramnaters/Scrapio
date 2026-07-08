"""Makes local copy of remote files"""

from pathlib import Path

import httpx

from moviebox.mobile.constants import CustomResolutionType, SubjectType
from moviebox.mobile.helpers import assert_instance, get_file_extension
from moviebox.mobile.models.downloadables import (
    RootDownloadableFilesDetailModel,
    VideoFileMetadata,
)

__all__ = [
    "MediaFileDownloader",
    "CaptionFileDownloader",
    "resolve_media_file_to_be_downloaded",
]
