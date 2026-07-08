import logging

import moviebox.legacy.logger

moviebox.legacy.logger.logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
