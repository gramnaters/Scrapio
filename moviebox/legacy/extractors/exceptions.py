from moviebox.legacy._bases import BaseProviderException


class DetailsExtractionError(BaseProviderException):
    """Raised when trying to extract data from html page without success"""
