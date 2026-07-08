"""Contains functionalities for fetching and modelling downloadable files metadata
and later performing the actual download as well
"""

from pathlib import Path

import httpx

from moviebox.legacy._bases import BaseContentProviderAndHelper
from moviebox.legacy.constants import SubjectType
from moviebox.legacy.extractors.json_models import (
    ItemJsonDetailsModel,
    PostListItemSubjectModel,
)
from moviebox.legacy.helpers import assert_instance, get_absolute_url
from moviebox.legacy.models import DownloadableFilesMetadata, SearchResultsItem
from moviebox.legacy.requests import Session

__all__ = [
    "MediaFileDownloader",
    "CaptionFileDownloader",
    "DownloadableMovieFilesDetail",
    "DownloadableTVSeriesFilesDetail",
    "resolve_media_file_to_be_downloaded",
]


class BaseDownloadableFilesDetail(BaseContentProviderAndHelper):
    """Base class for fetching and modelling downloadable files detail"""

    _url = get_absolute_url("/wefeed-h5-bff/web/subject/download")

    def __init__(
        self, session: Session, item: SearchResultsItem | ItemJsonDetailsModel
    ):
        """Constructor for `BaseDownloadableFilesDetail`

        Args:
            session (Session): ProviderAPI request session.
            item (SearchResultsItem | ItemJsonDetailsModel): Movie/TVSeries item
                to handle.
        """
        assert_instance(session, Session, "session")
        assert_instance(item, (SearchResultsItem, ItemJsonDetailsModel), "item")
        self.session = session
        self._item: SearchResultsItem | PostListItemSubjectModel = (
            item.resData.postList.items[0].subject
            if isinstance(item, ItemJsonDetailsModel)
            else item
        )

    def _create_request_params(self, season: int, episode: int) -> dict:
        """Creates request parameters

        Args:
            season (int): Season number of the series.
            episde (int): Episode number of the series.
        Returns:
            t.Dict: Request params
        """
        return {"subjectId": self._item.subjectId, "se": season, "ep": episode}

    async def get_content(self, season: int, episode: int) -> dict:
        """Performs the actual fetching of files detail.

        Args:
            season (int): Season number of the series.
            episde (int): Episode number of the series.

        Returns:
            t.Dict: File details
        """
        request_header = {
            "Referer": get_absolute_url(f"/movies/{self._item.detailPath}")
        }
        content = await self.session.get_with_cookies_from_api(
            url=self._url,
            params=self._create_request_params(season, episode),
            headers=request_header,
        )
        return content

    async def get_content_model(
        self, season: int, episode: int
    ) -> DownloadableFilesMetadata:
        """Get modelled version of the downloadable files detail.

        Args:
            season (int): Season number of the series.
            episde (int): Episode number of the series.

        Returns:
            DownloadableFilesMetadata: Modelled file details
        """
        contents = await self.get_content(season, episode)
        return DownloadableFilesMetadata(**contents)


class DownloadableMovieFilesDetail(BaseDownloadableFilesDetail):
    """Fetches and model movie files detail"""

    async def get_content(self) -> dict:
        """Actual fetch of files detail"""
        return await super().get_content(season=0, episode=0)

    async def get_content_model(self) -> DownloadableFilesMetadata:
        """Modelled version of the files detail"""
        contents = await self.get_content()
        return DownloadableFilesMetadata(**contents)


class DownloadableTVSeriesFilesDetail(BaseDownloadableFilesDetail):
    """Fetches and model series files detail"""
