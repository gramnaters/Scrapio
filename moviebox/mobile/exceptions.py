from moviebox.legacy.exceptions import (
    ExhaustedSearchResultsError,
    ProviderApiException,
    ZeroCaptionFileError,
    ZeroMediaFileError,
    ZeroSearchResultsError,
)


class ResultsNavigationError(ProviderApiException): ...


class MissingDubError(ProviderApiException): ...
