import logging
import sys

from loguru import logger

_logger = logging.getLogger("airtest")
_logger.setLevel(logging.ERROR)

logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                              "<level>{level: <8}</level> | "
                              "<level>{message}</level>",
           )


