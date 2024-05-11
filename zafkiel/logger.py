import logging
import sys

from loguru import logger

airtest_logger = logging.getLogger("airtest")
airtest_logger.setLevel(logging.ERROR)

logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                              "<level>{level: <7}</level> | "
                              "<level>{message}</level>",
           )


