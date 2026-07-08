"""Extracts data from specific movie/tv-series page"""

from moviebox.legacy.extractors.core import (
    JsonDetailsExtractor,
    JsonDetailsExtractorModel,
    TagDetailsExtractor,
    TagDetailsExtractorModel,
)
from moviebox.legacy.extractors.exceptions import DetailsExtractionError

__all__ = [
    "TagDetailsExtractor",
    "JsonDetailsExtractor",
    "TagDetailsExtractorModel",
    "JsonDetailsExtractorModel",
    "DetailsExtractionError",
]
