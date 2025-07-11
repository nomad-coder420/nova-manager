import logging

LOG_LEVEL = logging.INFO


def configure_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


logger = logging.getLogger(__name__)
