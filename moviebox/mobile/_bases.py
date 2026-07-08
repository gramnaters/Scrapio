import asyncio
import os
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from moviebox.legacy._bases import BaseContentProviderAndHelper
from moviebox.mobile.constants import (
    CURRENT_WORKING_DIR,
    DOWNLOAD_REQUEST_HEADERS,
)
