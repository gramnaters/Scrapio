"""v2 Exceptions"""

from moviebox.legacy.exceptions import (
    ExhaustedSearchResultsError,
    ProviderApiException,
)


class InvalidDetailPathError(ProviderApiException): ...
