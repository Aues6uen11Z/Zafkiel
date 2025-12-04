from airtest.core.helper import G
from zafkiel.device.win import WindowsPlatform
from zafkiel.report import ZafkielLogger

G.register_custom_device(WindowsPlatform)
G.LOGGER = ZafkielLogger(None)

from zafkiel.config import Config
from zafkiel.device.api import *
from zafkiel.device.template import ImageTemplate as Template
from zafkiel.timer import Timer
from zafkiel.report import simple_report
from zafkiel.logger import logger

try:
    from zafkiel._version import version as __version__
except ImportError:
    __version__ = "unknown"
