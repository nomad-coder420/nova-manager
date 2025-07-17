import logging
from nova_manager.core.config import DEBUG

LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO


def configure_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


logger = logging.getLogger(__name__)
