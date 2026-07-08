"""Exceptions module"""

from httpx import Response

from moviebox.legacy._bases import BaseProviderException


class ProviderApiException(BaseProviderException):
    """A unique base `Exception` for the package"""


class UnsuccessfulResponseError(BaseProviderException):
    """Raised when provider API serves request with a fail report."""

    def __init__(self, response: Response, *args, **kwargs):
        self.response = response
        """Unsuccessful response data"""
        super().__init__(*args, **kwargs)


class EmptyResponseError(BaseProviderException):
    """Raised when an empty body response is received with status code 200-OK"""

    def __init__(self, response: Response, *args, **kwargs):
        self.response = response
        """Httpx response object"""
        super().__init__(*args, **kwargs)


class ExhaustedSearchResultsError(BaseProviderException):
    """Raised when trying to navigate to next page of a complete search results"""

    def __init__(self, last_pager, *args, **kwargs):
        self.last_pager = last_pager
        """Current page info"""
        super().__init__(*args, **kwargs)


class ZeroSearchResultsError(BaseProviderException):
    """Raised when empty search results is encountered."""


class ZeroCaptionFileError(BaseProviderException):
    """Raised when caption file is required but the item lacks any"""


class ZeroMediaFileError(BaseProviderException):
    """Raised when trying to access a downloadable media file but the list
    is empty"""


class MissingAuthError(BaseProviderException):
    """Raised when target response lacks x-user key in headers"""
