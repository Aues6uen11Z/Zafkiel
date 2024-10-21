from airtest.core.helper import G

from zafkiel.config import Config
from zafkiel.device.api import *
from zafkiel.device.template import Template
from zafkiel.device.win import WindowsPlatform
from zafkiel.timer import Timer
from zafkiel.report import simple_report
from zafkiel.logger import logger

__version__ = '0.2.0'


G.register_custom_device(WindowsPlatform)
